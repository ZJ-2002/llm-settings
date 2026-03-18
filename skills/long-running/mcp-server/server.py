#!/usr/bin/env python3
"""
Long-Running MCP Server
提供项目状态持久化和管理的工具化接口
"""

import asyncio
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

PROJECT_ROOT = Path(os.getenv("LONG_RUNNING_ROOT", "."))


def validate_project_dir(project_dir: str) -> tuple[bool, str]:
    """验证项目目录是否已初始化"""
    state_dir = Path(project_dir) / ".state"
    if not state_dir.exists():
        return False, "项目未初始化，状态目录不存在"
    if not (state_dir / "checkpoint.json").exists():
        return False, "checkpoint.json 不存在"
    return True, ""


def read_json(filepath: Path) -> dict | None:
    """安全读取 JSON 文件"""
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    except (json.JSONDecodeError, IOError):
        return None


def write_json_atomic(filepath: Path, data: dict) -> bool:
    """原子写入 JSON 文件"""
    try:
        tmp_path = filepath.with_suffix(".tmp")
        bak_path = filepath.with_suffix(".bak")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            with open(tmp_path, "r") as f:
                json.load(f)
        except json.JSONDecodeError:
            tmp_path.unlink(missing_ok=True)
            return False
        if filepath.exists():
            shutil.copy(filepath, bak_path)
        shutil.move(str(tmp_path), str(filepath))
        return True
    except Exception:
        return False


def format_result(result: dict) -> str:
    """格式化结果为可读字符串"""
    if result.get("success"):
        output = []
        for key, value in result.items():
            if key != "success":
                if isinstance(value, dict):
                    output.append(f"{key}:\n{json.dumps(value, ensure_ascii=False, indent=2)}")
                elif isinstance(value, list):
                    output.append(f"{key}:")
                    for item in value:
                        output.append(f"  - {item}")
                else:
                    output.append(f"{key}: {value}")
        return "\n".join(output)
    else:
        return f"错误: {result.get('error', '未知错误')}"


async def initialize_project_impl(project_dir: str, project_name: str, total_tasks: int) -> dict:
    """初始化项目实现"""
    project_path = Path(project_dir).resolve()
    state_dir = project_path / ".state"
    if state_dir.exists():
        return {"success": False, "error": "项目已初始化"}
    try:
        state_dir.mkdir(parents=True)
        (state_dir / "logs").mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        checkpoint = {
            "version": 2, "project_name": project_name, "created_at": timestamp,
            "updated_at": timestamp, "status": "active", "progress_percent": 0.0,
            "session_count": 0, "total_tasks": total_tasks, "completed_tasks": 0,
            "in_progress_tasks": 0, "pending_tasks": total_tasks, "blocked_tasks": 0,
            "failed_tasks": 0, "recent_errors": [], "dependency_health": "valid",
            "teams_used": {"total_teams_created": 0, "active_teams": 0, "last_team_config": None},
            "recent_sessions": [], "checksum": {}, "last_session": None,
            "summary": "项目初始化完成"
        }
        write_json_atomic(state_dir / "checkpoint.json", checkpoint)
        write_json_atomic(state_dir / "task-queue.json", {"version": 1, "tasks": []})
        return {"success": True, "message": "项目初始化成功", "state_dir": str(state_dir)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_status_impl(project_dir: str, show_tasks: bool, show_errors: bool, show_log: bool) -> dict:
    """获取状态实现"""
    is_valid, error = validate_project_dir(project_dir)
    if not is_valid:
        return {"success": False, "error": error}
    checkpoint = read_json(Path(project_dir) / ".state" / "checkpoint.json")
    if not checkpoint:
        return {"success": False, "error": "无法读取 checkpoint"}
    result = {
        "success": True, "status": checkpoint.get("status", "unknown"),
        "project_name": checkpoint.get("project_name", "未知"),
        "progress_percent": checkpoint.get("progress_percent", 0),
        "tasks": {
            "total": checkpoint.get("total_tasks", 0),
            "completed": checkpoint.get("completed_tasks", 0),
            "in_progress": checkpoint.get("in_progress_tasks", 0),
            "pending": checkpoint.get("pending_tasks", 0),
            "blocked": checkpoint.get("blocked_tasks", 0),
            "failed": checkpoint.get("failed_tasks", 0)
        },
        "session_count": checkpoint.get("session_count", 0),
        "dependency_health": checkpoint.get("dependency_health", "unknown"),
        "updated_at": checkpoint.get("updated_at", "")
    }
    return result


if MCP_AVAILABLE:
    mcp = FastMCP("long-running-server")

    @mcp.tool()
    async def initialize_project(project_dir: str = ".", project_name: str = "未命名项目", total_tasks: int = 0) -> str:
        """初始化长期运行项目"""
        result = await initialize_project_impl(project_dir, project_name, total_tasks)
        return format_result(result)

    @mcp.tool()
    async def get_status(project_dir: str = ".", show_tasks: bool = False, show_errors: bool = False, show_log: bool = False) -> str:
        """获取项目当前状态"""
        result = await get_status_impl(project_dir, show_tasks, show_errors, show_log)
        return format_result(result)

if __name__ == "__main__":
    if MCP_AVAILABLE:
        mcp.run(transport="stdio")
    else:
        print("MCP 不可用", file=sys.stderr)
        sys.exit(1)
