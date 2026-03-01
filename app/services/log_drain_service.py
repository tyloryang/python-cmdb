"""
log_drain_service.py
~~~~~~~~~~~~~~~~~~~~
封装 drain3 TemplateMiner，提供：
  - 构建 miner（按 watcher 配置参数）
  - 本地文件 tail（按字节偏移）
  - 远程 SSH tail
  - 批量解析日志行，返回 (cluster_id, template_str, change_type, raw_line) 列表
"""
from __future__ import annotations

import glob
import io
import os
import re
from pathlib import Path
from typing import Optional

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.file_persistence import FilePersistenceHandler

# drain3 状态文件存放目录
_STATE_DIR = Path(".drain3_state")
_STATE_DIR.mkdir(exist_ok=True)

# 每个模板最多保留的样本日志条数
SAMPLE_LIMIT = 10


def _build_miner(watcher) -> TemplateMiner:
    """根据 LogWatcher 配置构建 drain3 TemplateMiner（带文件持久化）"""
    config = TemplateMinerConfig()
    config.load_defaults()
    config.drain_depth = watcher.drain_depth
    config.drain_sim_th = watcher.drain_sim_th
    config.drain_max_children = watcher.drain_max_children

    # 注入用户自定义掩码规则
    if watcher.masking_patterns:
        for mp in watcher.masking_patterns:
            pattern = mp if isinstance(mp, dict) else mp.model_dump()
            config.masking_instructions.append(
                {"regex_pattern": pattern["regex_pattern"], "mask_with": pattern.get("mask_with", "<*>")}
            )

    state_file = str(_STATE_DIR / f"watcher_{watcher.id}.bin")
    persistence = FilePersistenceHandler(state_file)
    return TemplateMiner(persistence_handler=persistence, config=config)


def _extract_message(raw_line: str, log_format_regex: Optional[str]) -> str:
    """若配置了格式正则，从原始行中提取 message 字段；否则直接返回原行"""
    if not log_format_regex:
        return raw_line
    m = re.search(log_format_regex, raw_line)
    if m and "message" in m.groupdict():
        return m.group("message")
    return raw_line


# ─────────────────────────────────────────────
# 本地 tail
# ─────────────────────────────────────────────

def tail_local(log_path: str, last_pos: int) -> tuple[list[str], int]:
    """
    从 last_pos 字节处读取本地日志新行（支持 glob 路径）。
    返回 (新行列表, 新字节偏移)。
    文件被 rotate 时（文件变小）自动从头重读。
    """
    paths = sorted(glob.glob(log_path)) or [log_path]
    filepath = paths[-1]  # 取最新一个文件

    try:
        file_size = os.path.getsize(filepath)
    except FileNotFoundError:
        return [], last_pos

    # 文件被截断（logrotate）
    if file_size < last_pos:
        last_pos = 0

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        f.seek(last_pos)
        lines = [line.rstrip("\n") for line in f if line.strip()]
        new_pos = f.tell()

    return lines, new_pos


# ─────────────────────────────────────────────
# 远程 SSH tail
# ─────────────────────────────────────────────

def tail_remote(server, log_path: str, last_pos: int) -> tuple[list[str], int]:
    """
    通过 SSH 从远程服务器读取日志新行。
    用 `wc -c` 获取文件大小，再用 `tail -c +N` 读增量。
    返回 (新行列表, 新字节偏移)。
    """
    import paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    kwargs: dict = {
        "hostname": server.hostname,
        "port": server.ssh_port,
        "username": server.ssh_user,
        "timeout": 10,
    }
    if server.ssh_auth_type == "password":
        kwargs["password"] = server.ssh_credential
    else:
        kwargs["pkey"] = paramiko.RSAKey.from_private_key(io.StringIO(server.ssh_credential))

    try:
        ssh.connect(**kwargs)

        # 获取文件大小
        _, out, _ = ssh.exec_command(f"wc -c < {log_path} 2>/dev/null || echo 0")
        file_size = int(out.read().decode().strip() or 0)

        if file_size < last_pos:
            last_pos = 0  # 文件被截断

        if file_size <= last_pos:
            return [], last_pos

        # 读取增量内容
        start = last_pos + 1  # tail -c +N 是从第 N 字节开始（1-indexed）
        _, out, _ = ssh.exec_command(f"tail -c +{start} {log_path}")
        content = out.read().decode("utf-8", errors="replace")

        lines = [line for line in content.splitlines() if line.strip()]
        return lines, file_size

    finally:
        ssh.close()


# ─────────────────────────────────────────────
# 核心解析函数
# ─────────────────────────────────────────────

ParseResult = list[dict]  # [{cluster_id, template_str, change_type, raw_line}]


def parse_lines(watcher, lines: list[str]) -> ParseResult:
    """
    将一批日志行送入 drain3，返回解析结果列表。
    每个元素：{cluster_id, template_str, change_type, raw_line}
    """
    if not lines:
        return []

    miner = _build_miner(watcher)
    results: ParseResult = []

    for raw in lines:
        message = _extract_message(raw, watcher.log_format_regex)
        result = miner.add_log_message(message)
        if result is None:
            continue
        results.append({
            "cluster_id": result["cluster_id"],
            "template_str": result["template_mined"],
            "change_type": result["change_type"],   # none / update / cluster_template_changed / cluster_created
            "raw_line": raw,
        })

    return results
