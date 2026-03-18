#!/bin/bash
# ============================================================
#  长期运行项目 - 后台守护进程管理脚本
#  用法: ./run-daemon.sh <命令> [参数]
#
#  命令:
#    start [轮次] [项目目录]  启动后台循环，默认 1000 轮
#    stop [项目目录]          停止后台循环
#    status [项目目录]        查看后台循环状态
#    log [项目目录]           实时查看日志 (tail -f)
#    pid [项目目录]           显示进程 PID
# ============================================================

set -euo pipefail

# 默认项目目录
DEFAULT_PROJECT_DIR="."

# 获取绝对路径函数
get_abs_path() {
    local path="$1"
    cd "$path" 2>/dev/null && pwd
}

# 启动后台循环
start_daemon() {
    local iterations="${1:-1000}"
    local project_dir="${2:-$DEFAULT_PROJECT_DIR}"

    project_dir=$(get_abs_path "$project_dir")
    if [ $? -ne 0 ]; then
        echo "错误: 项目目录不存在: $project_dir"
        exit 1
    fi

    if [ ! -d "$project_dir/.state" ]; then
        echo "错误: 项目未初始化，请先运行 init.sh"
        exit 1
    fi

    local pid_file="$project_dir/.state/run.pid"
    local log_file="$project_dir/run.log"
    local run_script="$project_dir/run.sh"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null || echo "")
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            echo "警告: 后台循环已在运行 (PID: $pid)"
            exit 1
        fi
    fi

    echo "启动后台循环 ($iterations 轮)..."
    cd "$project_dir"
    nohup "$run_script" "$iterations" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"

    echo "后台循环已启动 (PID: $pid)"
}

# 停止后台循环
stop_daemon() {
    local project_dir="${1:-$DEFAULT_PROJECT_DIR}"
    project_dir=$(get_abs_path "$project_dir")
    local pid_file="$project_dir/.state/run.pid"

    if [ ! -f "$pid_file" ]; then
        echo "信息: 未找到 PID 文件"
        exit 0
    fi

    local pid=$(cat "$pid_file" 2>/dev/null || echo "")
    if [ -z "$pid" ]; then
        echo "错误: 无法读取 PID"
        exit 1
    fi

    if ! ps -p "$pid" > /dev/null 2>&1; then
        echo "信息: 进程不存在，清理 PID 文件"
        rm -f "$pid_file"
        exit 0
    fi

    kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
    rm -f "$pid_file"
    echo "后台循环已停止"
}

# 主命令分发
COMMAND="${1:-help}"
shift

case "$COMMAND" in
    start)
        start_daemon "$@"
        ;;
    stop)
        stop_daemon "$@"
        ;;
    help|--help|-h)
        echo "用法: $0 <命令> [参数]"
        echo ""
        echo "命令:"
        echo "  start [轮次] [项目目录]  启动后台循环"
        echo "  stop [项目目录]          停止后台循环"
        ;;
    *)
        echo "错误: 未知命令 '$COMMAND'"
        exit 1
        ;;
esac
