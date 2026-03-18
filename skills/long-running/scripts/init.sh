#!/bin/bash
# ============================================================
#  长期运行项目初始化脚本
#  用法: ./init.sh <项目目录> <项目名称> [总任务数]
#
#  示例:
#    ./init.sh . "my-web-app"
#    ./init.sh ~/projects/my-app "电商系统" 50
# ============================================================

set -uo pipefail

# ---- 跨平台 MD5 计算函数 ----
md5_file() {
    local file="$1"
    if command -v md5sum &>/dev/null; then
        md5sum "$file" 2>/dev/null | awk '{print $1}'
    elif command -v md5 &>/dev/null; then
        md5 -q "$file" 2>/dev/null
    else
        echo "错误: 需要 md5sum 或 md5 命令" >&2
        exit 1
    fi
}

if [ $# -lt 2 ]; then
    echo "用法: ./init.sh <项目目录> <项目名称> [总任务数]"
    echo ""
    echo "参数:"
    echo "  <项目目录>    项目根目录路径"
    echo "  <项目名称>    项目名称（用于 checkpoint 记录）"
    echo "  [总任务数]    预估任务总数，可选"
    echo ""
    echo "示例:"
    echo "  ./init.sh . \"my-web-app\""
    echo "  ./init.sh ~/projects/my-app \"电商系统\" 50"
    exit 1
fi

PROJECT_DIR="$1"
PROJECT_NAME="$2"
TOTAL_TASKS="${3:-0}"

# 解析绝对路径
PROJECT_DIR=$(cd "$PROJECT_DIR" 2>/dev/null && pwd)
if [ $? -ne 0 ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

STATE_DIR="$PROJECT_DIR/.state"

# 检查是否已初始化
if [ -d "$STATE_DIR" ]; then
    echo "错误: 项目已初始化，状态目录已存在: $STATE_DIR"
    echo "如需重新初始化，请先删除该目录"
    exit 1
fi

# 创建目录结构
mkdir -p "$STATE_DIR/logs"

echo "==========================================="
echo "  初始化长期运行项目"
echo "==========================================="
echo "  项目目录: $PROJECT_DIR"
echo "  项目名称: $PROJECT_NAME"
echo "  预估任务数: $TOTAL_TASKS"
echo "==========================================="
echo ""

# 生成 ISO 格式时间戳（仅生成一次，确保所有文件使用相同时间戳）
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOCAL_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 创建 task-queue.json（必须在 checkpoint 之前，因为需要计算其校验和）
cat > "$STATE_DIR/task-queue.json" << EOF
{
  "version": 1,
  "updated_at": "$TIMESTAMP",
  "tasks": []
}
EOF

# 基于实际文件内容计算 task-queue.json 的校验和
TASK_QUEUE_CHECKSUM=$(md5_file "$STATE_DIR/task-queue.json")

cp "$STATE_DIR/task-queue.json" "$STATE_DIR/task-queue.json.bak"

echo "✓ 创建 task-queue.json"

# 创建 session-log.md（必须在 checkpoint 之前，因为需要计算其校验和）
cat > "$STATE_DIR/session-log.md" << EOF
# 会话日志

## 项目信息
- **项目名称**: $PROJECT_NAME
- **初始化时间**: $LOCAL_TIMESTAMP
- **预估任务数**: $TOTAL_TASKS

---

## 会话 #0 — $LOCAL_TIMESTAMP
**类型**: 初始化
**完成**: 项目初始化，创建状态文件
**下一步**: 编辑 task-queue.json 定义任务

---

EOF

# 基于实际文件内容计算 session-log.md 的校验和
SESSION_LOG_CHECKSUM=$(md5_file "$STATE_DIR/session-log.md")

echo "✓ 创建 session-log.md"

# 创建 checkpoint.json (version 2)
# 现在使用正确的校验和，因为文件已经存在
cat > "$STATE_DIR/checkpoint.json" << EOF
{
  "version": 2,
  "project_name": "$PROJECT_NAME",
  "created_at": "$TIMESTAMP",
  "updated_at": "$TIMESTAMP",
  "status": "active",
  "progress_percent": 0.0,
  "session_count": 0,
  "total_tasks": $TOTAL_TASKS,
  "completed_tasks": 0,
  "in_progress_tasks": 0,
  "pending_tasks": $TOTAL_TASKS,
  "blocked_tasks": 0,
  "failed_tasks": 0,
  "recent_errors": [],
  "dependency_health": "valid",
  "teams_used": {
    "total_teams_created": 0,
    "last_team_config": null
  },
  "recent_sessions": [],
  "checksum": {
    "task_queue": "$TASK_QUEUE_CHECKSUM",
    "session_log": "$SESSION_LOG_CHECKSUM"
  },
  "last_session": null,
  "summary": "项目初始化完成，等待任务定义"
}
EOF

# 创建 checkpoint.json.bak（首次备份）
cp "$STATE_DIR/checkpoint.json" "$STATE_DIR/checkpoint.json.bak"

echo "✓ 创建 checkpoint.json (version 2)"

# 创建 .gitignore（如果不存在）
GITIGNORE="$PROJECT_DIR/.gitignore"
if [ ! -f "$GITIGNORE" ]; then
    touch "$GITIGNORE"
fi

# 添加 .state 相关条目（如果不重复）
for pattern in ".state/logs/" ".state/*.tmp" ".state/*.bak" ".state/lock"; do
    if ! grep -q "^$pattern$" "$GITIGNORE" 2>/dev/null; then
        echo "$pattern" >> "$GITIGNORE"
    fi
done

echo "✓ 更新 .gitignore"

# 检查是否为 git 仓库
if [ -d "$PROJECT_DIR/.git" ]; then
    echo ""
    echo "检测到Git 仓库，建议执行以下命令提交状态文件："
    echo "  git add .state/checkpoint.json .state/task-queue.json .state/session-log.md .gitignore"
    echo "  git commit -m \"chore: 初始化长期运行状态管理\""
fi

echo ""
echo "==========================================="
echo "  初始化完成"
echo "==========================================="
echo "  状态目录: $STATE_DIR"
echo ""
echo "下一步:"
echo "  1. 编辑 task-queue.json 定义任务"
echo "  2. 使用 run.sh 开始自动化执行"
echo ""
echo "任务定义示例:"
echo '  参考基础设施文档 ~/.claude/skills/long-running/references/infrastructure.md'
echo ""
echo "checkpoint.json 格式 (version 2):"
echo "  - 新增项目状态字段 (status)"
echo "  - 新增进度百分比 (progress_percent)"
echo "  - 新增各状态任务统计"
echo "  - 新增错误记录 (recent_errors)"
echo "  - 新增依赖健康检查 (dependency_health)"
echo "  - 新增 Agent Teams 使用记录 (teams_used)"
echo "  - 新增最近会话摘要 (recent_sessions)"
echo "  - 新增数据校验和 (checksum)"
echo "==========================================="
