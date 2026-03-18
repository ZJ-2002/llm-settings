#!/bin/bash
# ============================================================
#  长期运行项目状态检查脚本
#  用法: ./status.sh [项目目录] [选项]
#
#  示例:
#    ./status.sh                        # 检查当前目录
#    ./status.sh ~/projects/my-app      # 检查指定目录
#    ./status.sh . --detailed            # 显示详细信息
#    ./status.sh . --tasks               # 显示任务列表
# ============================================================

set -uo pipefail

# 检查 python3 是否可用
if ! command -v python3 &>/dev/null; then
    echo "错误: 需要 python3，请先安装"
    exit 1
fi

# ---- 参数解析 ----

SHOW_DETAILED=false
SHOW_TASKS=false
SHOW_LOG=false
SHOW_ERRORS=false
PROJECT_DIR="."

while [ $# -gt 0 ]; do
    case "$1" in
        --detailed|-d)
            SHOW_DETAILED=true
            shift
            ;;
        --tasks|-t)
            SHOW_TASKS=true
            shift
            ;;
        --log|-l)
            SHOW_LOG=true
            shift
            ;;
        --errors|-e)
            SHOW_ERRORS=true
            shift
            ;;
        --all|-a)
            SHOW_DETAILED=true
            SHOW_TASKS=true
            SHOW_LOG=true
            SHOW_ERRORS=true
            shift
            ;;
        -*)
            echo "未知选项: $1"
            exit 1
            ;;
        *)
            PROJECT_DIR="$1"
            shift
            ;;
    esac
done

# 解析绝对路径
PROJECT_DIR=$(cd "$PROJECT_DIR" 2>/dev/null && pwd)
if [ $? -ne 0 ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

STATE_DIR="$PROJECT_DIR/.state"

# ---- 颜色输出 ----

if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    MAGENTA='\033[0;35m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    MAGENTA=''
    NC=''
fi

# ---- 检查项目是否已初始化 ----

if [ ! -d "$STATE_DIR" ]; then
    echo "错误: 项目未初始化，状态目录不存在: $STATE_DIR"
    echo ""
    echo "请先运行 init.sh 初始化项目"
    exit 1
fi

# ---- 辅助函数 ----

# 跨平台获取文件修改时间（Unix 时间戳）
get_file_mtime() {
    local file="$1"
    if stat --version &>/dev/null 2>&1; then
        # Linux (GNU stat)
        stat -c %Y "$file" 2>/dev/null || echo 0
    else
        # macOS (BSD stat)
        stat -f %m "$file" 2>/dev/null || echo 0
    fi
}

# 跨平台计算 MD5
md5_file() {
    local file="$1"
    if command -v md5sum &>/dev/null; then
        md5sum "$file" 2>/dev/null | awk '{print $1}'
    elif command -v md5 &>/dev/null; then
        md5 -q "$file" 2>/dev/null
    else
        echo "错误: 需要 md5sum 或 md5 命令"
        exit 1
    fi
}

print_section() {
    echo ""
    echo -e "${CYAN}=== $1 ===${NC}"
}

print_label() {
    printf "${BLUE}%s${NC} %s\n" "$1" "$2"
}

print_success() {
    printf "${GREEN}✓${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}✗${NC} %s\n" "$1"
}

print_status() {
    local status="$1"
    case "$status" in
        "active")
            printf "${GREEN}● 运行中${NC}"
            ;;
        "completed")
            printf "${GREEN}● 已完成${NC}"
            ;;
        "failed")
            printf "${RED}● 已失败${NC}"
            ;;
        "paused")
            printf "${YELLOW}● 已暂停${NC}"
            ;;
        *)
            printf "? 未知${NC}"
            ;;
    esac
}

# ---- 主输出 ----

echo -e "${CYAN}=============================================${NC}"
echo -e "${CYAN}  长期运行项目状态${NC}"
echo -e "${CYAN}=============================================${NC}"
echo -e "${BLUE}项目目录:${NC} $PROJECT_DIR"
echo -e "${BLUE}检查时间:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "${CYAN}=============================================${NC}"

echo ""
echo "状态目录已初始化: $STATE_DIR"
echo ""
echo -e "${BLUE}提示:${NC}"
echo "  使用 --detailed/-d 显示详细信息"
echo "  使用 --tasks/-t 显示任务列表"
echo "  使用 --log/-l 显示最近日志"
echo "  使用 --errors/-e 显示最近错误"
echo "  使用 --all/-a 显示所有详情"
echo -e "${CYAN}=============================================${NC}"
