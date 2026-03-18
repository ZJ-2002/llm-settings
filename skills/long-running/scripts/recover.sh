#!/bin/bash
# ============================================================
#  长期运行项目恢复脚本
#  用法: ./recover.sh <项目目录> [选项]
#
#  示例:
#    ./recover.sh .                         # 交互式恢复
#    ./recover.sh . --force          # 强制恢复
#    ./recover.sh . --dry-run        # 只显示操作
# ============================================================

set -uo pipefail

# 检查 python3 是否可用
if ! command -v python3 &>/dev/null; then
    echo "错误: 需要 python3，请先安装"
    exit 1
fi

# ---- 参数解析 ----

FORCE=false
DRY_RUN=false
PROJECT_DIR="."

while [ $# -gt 0 ]; do
    case "$1" in
        --force|-f)
            FORCE=true
            shift
            ;;
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "用法: ./recover.sh <项目目录> [选项]"
            echo ""
            echo "选项:"
            echo "  --force, -f      强制恢复，不提示确认"
            echo "  --dry-run, -n    只显示将要执行的操作"
            echo "  --help, -h       显示帮助"
            exit 0
            ;;
        -*)
            echo "错误: 未知选项 $1"
            exit 1
            ;;
        *)
            PROJECT_DIR="$1"
            shift
            ;;
    esac
done

# 获取绝对路径
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
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    NC=''
fi

# ---- 辅助函数 ----

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_action() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}[DRY-RUN]${NC} $1"
    else
        echo -e "${CYAN}[ACTION]${NC} $1"
    fi
}

# 验证 JSON 文件
validate_json() {
    local file="$1"
    python3 -c "import json; json.load(open('$file'))" 2>/dev/null
    return $?
}

# 从备份恢复
restore_from_backup() {
    local main_file="$1"
    local bak_file="${main_file}.bak"

    if [ -f "$bak_file" ]; then
        if validate_json "$bak_file"; then
            log_action "从备份恢复: $main_file"
            if [ "$DRY_RUN" = false ]; then
                cp "$bak_file" "$main_file"
            fi
            return 0
        else
            log_error "备份文件也损坏: $bak_file"
            return 1
        fi
    else
        log_error "备份文件不存在: $bak_file"
        return 1
    fi
}

# 从 Git 恢复
restore_from_git() {
    local file="$1"

    if [ -d "$PROJECT_DIR/.git" ]; then
        log_action "从 Git 恢复: $file"
        if [ "$DRY_RUN" = false ]; then
            cd "$PROJECT_DIR" && git checkout HEAD -- "$file" 2>/dev/null
            return $?
        fi
        return 0
    else
        log_error "不是 Git 仓库，无法从 Git 恢复"
        return 1
    fi
}

# ---- 主恢复流程 ----

echo ""
echo -e "${CYAN}===========================================${NC}"
echo -e "${CYAN}  长期运行项目恢复${NC}"
echo -e "${CYAN}===========================================${NC}"
echo -e "${BLUE}项目目录:${NC} $PROJECT_DIR"
echo -e "${BLUE}模式:${NC} $([ "$DRY_RUN" = true ] && echo "Dry-run (仅显示操作)" || echo "执行恢复")"
echo ""

# 检查状态目录是否存在
if [ ! -d "$STATE_DIR" ]; then
    log_error "状态目录不存在: $STATE_DIR"
    echo ""
    echo "项目可能未初始化，请先运行 init.sh"
    exit 1
fi

ACTIONS_TAKEN=()

# ---- 阶段 1: 清理中断的写入 ----

echo ""
echo -e "${CYAN}=== 阶段 1: 清理中断的写入 ===${NC}"

for tmp_file in "$STATE_DIR"/*.tmp; do
    if [ -f "$tmp_file" ]; then
        filename=$(basename "$tmp_file")
        log_action "删除中断残留: $filename"
        if [ "$DRY_RUN" = false ]; then
            rm -f "$tmp_file"
        fi
        ACTIONS_TAKEN+=("删除: $filename")
    fi
done

# ---- 阶段 2: 验证并恢复 checkpoint.json ----

echo ""
echo -e "${CYAN}=== 阶段 2: 验证 checkpoint.json ===${NC}"

CHECKPOINT_FILE="$STATE_DIR/checkpoint.json"

if [ ! -f "$CHECKPOINT_FILE" ]; then
    log_warn "checkpoint.json 不存在"
    if restore_from_backup "$CHECKPOINT_FILE"; then
        ACTIONS_TAKEN+=("从备份恢复: checkpoint.json")
    elif restore_from_git "$CHECKPOINT_FILE"; then
        ACTIONS_TAKEN+=("从 Git 恢复: checkpoint.json")
    else
        log_error "无法恢复 checkpoint.json"
    fi
elif ! validate_json "$CHECKPOINT_FILE"; then
    log_warn "checkpoint.json 格式无效"
    if restore_from_backup "$CHECKPOINT_FILE"; then
        ACTIONS_TAKEN+=("从备份恢复: checkpoint.json")
    elif restore_from_git "$CHECKPOINT_FILE"; then
        ACTIONS_TAKEN+=("从 Git 恢复: checkpoint.json")
    else
        log_error "无法恢复 checkpoint.json"
    fi
else
    log_info "checkpoint.json 验证通过"
fi

# ---- 阶段 3: 验证并恢复 task-queue.json ----

echo ""
echo -e "${CYAN}=== 阶段 3: 验证 task-queue.json ===${NC}"

TASK_QUEUE_FILE="$STATE_DIR/task-queue.json"

if [ ! -f "$TASK_QUEUE_FILE" ]; then
    log_warn "task-queue.json 不存在"
    if restore_from_backup "$TASK_QUEUE_FILE"; then
        ACTIONS_TAKEN+=("从备份恢复: task-queue.json")
    elif restore_from_git "$TASK_QUEUE_FILE"; then
        ACTIONS_TAKEN+=("从 Git 恢复: task-queue.json")
    else
        log_error "无法恢复 task-queue.json"
    fi
elif ! validate_json "$TASK_QUEUE_FILE"; then
    log_warn "task-queue.json 格式无效"
    if restore_from_backup "$TASK_QUEUE_FILE"; then
        ACTIONS_TAKEN+=("从备份恢复: task-queue.json")
    elif restore_from_git "$TASK_QUEUE_FILE"; then
        ACTIONS_TAKEN+=("从 Git 恢复: task-queue.json")
    else
        log_error "无法恢复 task-queue.json"
    fi
else
    log_info "task-queue.json 验证通过"
fi

# ---- 阶段 4: 处理 in_progress 任务 ----

echo ""
echo -e "${CYAN}=== 阶段 4: 处理 in_progress 任务 ===${NC}"

# 4.1 处理 JSON 文件中的孤儿任务
if [ -f "$TASK_QUEUE_FILE" ] && validate_json "$TASK_QUEUE_FILE"; then
    IN_PROGRESS_TASKS=$(python3 -c "
import json
with open('$TASK_QUEUE_FILE') as f:
    data = json.load(f)
tasks = [t for t in data.get('tasks', []) if t.get('status') == 'in_progress']
for t in tasks:
    print(t.get('id', 'unknown'))
" 2>/dev/null)

    if [ -n "$IN_PROGRESS_TASKS" ]; then
        log_warn "JSON 文件中发现 in_progress 任务，将重置为 pending"

        for task_id in $IN_PROGRESS_TASKS; do
            log_action "重置 JSON 任务: $task_id (in_progress → pending)"
            ACTIONS_TAKEN+=("重置 JSON 任务: $task_id")
        done

        if [ "$DRY_RUN" = false ]; then
            python3 -c "
import json
with open('$TASK_QUEUE_FILE', 'r') as f:
    data = json.load(f)

for task in data.get('tasks', []):
    if task.get('status') == 'in_progress':
        task['status'] = 'pending'

with open('$TASK_QUEUE_FILE', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" 2>/dev/null
            log_info "JSON 任务状态已更新"
        fi
    fi
fi

# ---- 阶段 5: 清理过期锁文件 ----

echo ""
echo -e "${CYAN}=== 阶段 5: 清理过期锁文件 ===${NC}"

LOCK_FILE="$STATE_DIR/lock"

if [ -f "$LOCK_FILE" ]; then
    log_action "清理过期锁文件"
    if [ "$DRY_RUN" = false ]; then
        rm -f "$LOCK_FILE"
    fi
    ACTIONS_TAKEN+=("清理过期锁文件")
else
    log_info "无锁文件残留"
fi

# ---- 恢复总结 ----

echo ""
echo -e "${CYAN}===========================================${NC}"
echo -e "${CYAN}  恢复完成${NC}"
echo -e "${CYAN}===========================================${NC}"

if [ ${#ACTIONS_TAKEN[@]} -eq 0 ]; then
    log_info "无需恢复操作，项目状态正常"
else
    echo ""
    echo "执行的操作:"
    for action in "${ACTIONS_TAKEN[@]}"; do
        echo "  • $action"
    done
fi

echo ""
echo "下一步:"
echo "  1. 检查状态: ~/.claude/skills/long-running/scripts/status.sh $PROJECT_DIR"
echo "  2. 继续执行: ./run.sh 10 $PROJECT_DIR"
echo ""
