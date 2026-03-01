"""
比较两个 Git 分支的差异，按根目录分组，输出：哪些人修改了哪些根目录下的哪些文件
用法：
    python branch_diff_report.py <目标分支> <基准分支>
    python branch_diff_report.py prac master
    python branch_diff_report.py origin/prac origin/master

参数说明：
    目标分支（第一个）：要检查的分支，如 prac
    基准分支（第二个）：作为对比基准，如 master
    输出：目标分支相对基准分支新增/修改/删除了哪些内容
"""

import subprocess
import sys
import os
from collections import defaultdict

# Windows 终端 UTF-8 输出
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip()


def get_diff_commits(base, compare):
    """获取 compare 相对 base 独有的提交 hash 列表"""
    out = run(["git", "log", f"{base}..{compare}", "--pretty=format:%H"])
    return [h for h in out.splitlines() if h]


def get_commit_author(commit_hash):
    """获取提交的作者名"""
    return run(["git", "show", "-s", "--format=%an", commit_hash])


def get_commit_files(commit_hash):
    """获取提交涉及的文件列表（带变更类型）"""
    out = run(["git", "diff-tree", "--no-commit-id", "-r", "--name-status", commit_hash])
    files = []
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            status, filepath = parts
            files.append((status.strip(), filepath.strip()))
    return files


def get_root_dir(filepath):
    """提取文件的根目录（第一级目录或根目录文件）"""
    parts = filepath.replace("\\", "/").split("/")
    if len(parts) == 1:
        return "(根目录文件)"
    return parts[0] + "/"


STATUS_MAP = {
    "A": "新增",
    "M": "修改",
    "D": "删除",
    "R": "重命名",
    "C": "拷贝",
}


def main():
    if len(sys.argv) < 3:
        print("用法: python branch_diff_report.py <目标分支> <基准分支>")
        print("示例: python branch_diff_report.py prac master")
        print("示例: python branch_diff_report.py origin/prac origin/master")
        sys.exit(1)

    # 目标分支在前，基准分支在后
    # 输出：目标分支相对基准分支的差��（目标有、基准没有的提交）
    target = sys.argv[1]   # prac —— 要查的分支
    base   = sys.argv[2]   # master —— 基准分支

    print(f"\n{'='*60}")
    print(f"  分支对比: {target}  vs  {base}")
    print(f"  （显示 {target} 相对 {base} 的差异）")
    print(f"{'='*60}\n")

    # git log base..target：target 有但 base 没有的提交
    commits = get_diff_commits(base, target)
    if not commits:
        print(f"没有发现差异（{target} 与 {base} 相同，或 {target} 是 {base} 的子集）")
        sys.exit(0)

    print(f"共发现 {len(commits)} 个差异提交\n")

    # 数据结构: root_dir -> file -> set(作者)
    # 同时记录文件的变更类型
    root_files = defaultdict(lambda: defaultdict(set))       # root -> file -> {authors}
    root_files_status = defaultdict(dict)                    # root -> file -> status

    for commit_hash in commits:
        author = get_commit_author(commit_hash)
        files = get_commit_files(commit_hash)
        for status, filepath in files:
            root = get_root_dir(filepath)
            root_files[root][filepath].add(author)
            # 优先级：D > M > A（保留最"重"的变更类型）
            existing = root_files_status[root].get(filepath, "A")
            priority = {"D": 3, "M": 2, "R": 2, "C": 2, "A": 1}
            if priority.get(status[0], 0) >= priority.get(existing[0], 0):
                root_files_status[root][filepath] = status[0]

    # 按根目录输出
    for root in sorted(root_files.keys()):
        files = root_files[root]
        print(f"┌─ 根目录: {root}  ({len(files)} 个文件)")
        for filepath in sorted(files.keys()):
            authors = sorted(files[filepath])
            status_code = root_files_status[root].get(filepath, "?")
            status_label = STATUS_MAP.get(status_code, status_code)
            print(f"│  ├─ [{status_label}] {filepath}")
            print(f"│  │     修改人: {', '.join(authors)}")
        print("│")

    # 汇总：每人修改的根目录和文件数
    print(f"\n{'='*60}")
    print("  人员汇总")
    print(f"{'='*60}")

    author_summary = defaultdict(lambda: defaultdict(set))  # author -> root -> {files}
    for root, files in root_files.items():
        for filepath, authors in files.items():
            for author in authors:
                author_summary[author][root].add(filepath)

    for author in sorted(author_summary.keys()):
        roots = author_summary[author]
        total_files = sum(len(f) for f in roots.values())
        print(f"\n  {author}  （共涉及 {len(roots)} 个目录，{total_files} 个文件）")
        for root in sorted(roots.keys()):
            files = roots[root]
            print(f"    └─ {root}")
            for f in sorted(files):
                print(f"         · {f}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
