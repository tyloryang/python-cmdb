#!/usr/bin/env bash
# 比较两个 Git 分支差异，按根目录分组，输出修改人
# 用法: bash branch_diff_report.sh <目标分支> <基准分支>
# 示例: bash branch_diff_report.sh prac master
#       bash branch_diff_report.sh origin/prac origin/master

set -euo pipefail

# ── 参数检查 ──────────────────────────────────────────────
if [ $# -lt 2 ]; then
    echo "用法: bash branch_diff_report.sh <目标分支> <基准分支>"
    echo "示例: bash branch_diff_report.sh prac master"
    echo "示例: bash branch_diff_report.sh origin/prac origin/master"
    exit 1
fi

TARGET="$1"   # 目标分支（要查的，如 prac）
BASE="$2"     # 基准分支（如 master）

SEP="============================================================"

echo ""
echo "$SEP"
echo "  分支对比: $TARGET  vs  $BASE"
echo "  （显示 $TARGET 相对 $BASE 的差异）"
echo "$SEP"
echo ""

# ── 获取差异提交列表（target 有、base 没有）────────────────
COMMITS=$(git log "${BASE}..${TARGET}" --pretty=format:"%H" 2>/dev/null)

if [ -z "$COMMITS" ]; then
    echo "没有发现差异（$TARGET 与 $BASE 相同，或 $TARGET 是 $BASE 的子集）"
    exit 0
fi

COMMIT_COUNT=$(echo "$COMMITS" | wc -l | tr -d ' ')
echo "共发现 $COMMIT_COUNT 个差异提交"
echo ""

# ── 收集数据：文件 -> 作者集合 & 变更类型 ─────────────────
# 临时文件存放 "文件路径|作者|变更类型"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

while IFS= read -r HASH; do
    [ -z "$HASH" ] && continue
    AUTHOR=$(git show -s --format="%an" "$HASH")
    # diff-tree 输出格式: <状态>\t<文件路径>（--root 兼容首次提交）
    git diff-tree --no-commit-id -r --root --name-status "$HASH" \
    | while IFS=$'\t' read -r STATUS FILEPATH; do
        [ -z "$FILEPATH" ] && continue
        # 只取状态首字母（R100 -> R）
        STATUS="${STATUS:0:1}"
        echo "${FILEPATH}|${AUTHOR}|${STATUS}"
    done
done <<< "$COMMITS" >> "$TMP"

if [ ! -s "$TMP" ]; then
    echo "未发现文件变更"
    exit 0
fi

# ── 提取所有根目录（去重排序）────────────────────────────
get_root() {
    local fp="$1"
    local root
    root=$(echo "$fp" | cut -d'/' -f1)
    if [ "$root" = "$fp" ]; then
        echo "(根目录文件)"
    else
        echo "${root}/"
    fi
}

status_label() {
    case "$1" in
        A) echo "新增" ;;
        M) echo "修改" ;;
        D) echo "删除" ;;
        R) echo "重命名" ;;
        C) echo "拷贝" ;;
        *) echo "$1" ;;
    esac
}

# 所有根目录（去重）
ALL_ROOTS=$(awk -F'|' '{
    fp=$1
    n=split(fp,parts,"/")
    if(n==1) root="(根目录文件)"
    else root=parts[1]"/"
    print root
}' "$TMP" | sort -u)

# ── 按根目录输出 ──────────────────────────────────────────
while IFS= read -r ROOT; do
    [ -z "$ROOT" ] && continue

    # 筛选属于该根目录的行
    if [ "$ROOT" = "(根目录文件)" ]; then
        LINES=$(grep -v '/' "$TMP" || true)
    else
        PREFIX="${ROOT%/}"   # 去掉末尾 /
        LINES=$(grep "^${PREFIX}/" "$TMP" || true)
    fi

    [ -z "$LINES" ] && continue

    # 该根目录下的文件列表（去重）
    FILES=$(echo "$LINES" | awk -F'|' '{print $1}' | sort -u)
    FILE_COUNT=$(echo "$FILES" | wc -l | tr -d ' ')

    echo "┌─ 根目录: $ROOT  ($FILE_COUNT 个文件)"

    while IFS= read -r FPATH; do
        [ -z "$FPATH" ] && continue

        # 该文件的所有作者（去重排序）
        AUTHORS=$(grep "^${FPATH}|" "$TMP" | awk -F'|' '{print $2}' | sort -u | paste -sd ', ')

        # 该文件的变更类型（取优先级最高的）
        STATUS=$(grep "^${FPATH}|" "$TMP" | awk -F'|' '{
            s=$3
            p=0
            if(s=="D") p=3
            else if(s=="M"||s=="R"||s=="C") p=2
            else p=1
            if(p>maxp){ maxp=p; best=s }
        } END{print best}')

        LABEL=$(status_label "$STATUS")
        echo "│  ├─ [$LABEL] $FPATH"
        echo "│  │     修改人: $AUTHORS"
    done <<< "$FILES"

    echo "│"
done <<< "$ALL_ROOTS"

# ── 人员汇总 ──────────────────────────────────────────────
echo ""
echo "$SEP"
echo "  人员汇总"
echo "$SEP"

# 所有作者（去重排序）
ALL_AUTHORS=$(awk -F'|' '{print $2}' "$TMP" | sort -u)

while IFS= read -r AUTHOR; do
    [ -z "$AUTHOR" ] && continue

    # 该作者涉及的所有行
    AUTHOR_LINES=$(grep "|${AUTHOR}|" "$TMP" || true)
    [ -z "$AUTHOR_LINES" ] && continue

    # 涉及的根目录（去重）
    AUTHOR_ROOTS=$(echo "$AUTHOR_LINES" | awk -F'|' '{
        fp=$1
        n=split(fp,parts,"/")
        if(n==1) root="(根目录文件)"
        else root=parts[1]"/"
        print root
    }' | sort -u)

    ROOT_COUNT=$(echo "$AUTHOR_ROOTS" | wc -l | tr -d ' ')
    FILE_COUNT=$(echo "$AUTHOR_LINES" | awk -F'|' '{print $1}' | sort -u | wc -l | tr -d ' ')

    echo ""
    echo "  $AUTHOR  （共涉及 $ROOT_COUNT 个目录，$FILE_COUNT 个文件）"

    while IFS= read -r ROOT; do
        [ -z "$ROOT" ] && continue
        echo "    └─ $ROOT"

        if [ "$ROOT" = "(根目录文件)" ]; then
            RFILES=$(echo "$AUTHOR_LINES" | awk -F'|' '!($1 ~ "/"){print $1}' | sort -u)
        else
            PREFIX="${ROOT%/}"
            RFILES=$(echo "$AUTHOR_LINES" | awk -F'|' -v p="$PREFIX/" '$1 ~ "^"p{print $1}' | sort -u)
        fi

        while IFS= read -r F; do
            [ -z "$F" ] && continue
            echo "         · $F"
        done <<< "$RFILES"
    done <<< "$AUTHOR_ROOTS"

done <<< "$ALL_AUTHORS"

echo ""
echo "$SEP"
echo ""
