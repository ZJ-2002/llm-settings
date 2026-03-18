# Agent Teams 协作与孤儿进程清理协议

> 本文档定义了 Agent Teams 模式下团队生命周期管理、心跳机制和孤儿进程清理协议，确保主代理（Leader）崩溃时不会遗留僵尸子进程。

---

## 目录

- [核心问题](#核心问题)
- [协议核心：团队注册表机制](#协议核心团队注册表机制)
- [协议三阶段](#协议三阶段)
  - [阶段 1：登记与绑定](#阶段-1登记与绑定)
  - [阶段 2：存活心跳](#阶段-2存活心跳)
  - [阶段 3：收割（Reaping）](#阶段-3收割reaping)
- [MCP 工具详解](#mcp-工具详解)
- [心跳脚本实现](#心跳脚本实现)
- [集成到 recover()](#集成到-recover)
- [故障排除](#故障排除)

---

## 核心问题

当主代理（Leader）由于以下原因崩溃时，它启动的子代理（Sub-agents）进程可能仍在后台消耗 Token 和系统资源：

- API 超时或限流
- 进程被强制中断（Ctrl+C）
- 系统崩溃或断电
- 网络断开

**后果**：
- Token 费用持续累积
- 文件系统竞争（Race Condition）
- 系统资源耗尽

---

## 协议核心：团队注册表机制

引入 `.state/active_teams.json` 作为"团队注册表"，记录所有活跃团队的信息。

### 注册表数据结构

```json
{
  "version": 1,
  "updated_at": "2025-06-15T16:30:00Z",
  "active_teams": [
    {
      "team_id": "team-882",
      "leader_pid": 12345,
      "member_pids": [12346, 12347],
      "created_at": "2025-06-15T16:00:00Z",
      "heartbeat": "2025-06-15T16:30:00Z",
      "task_id": "task-005"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `team_id` | string | 团队唯一标识 |
| `leader_pid` | number | 发起团队创建的父进程 PID |
| `member_pids` | number[] | 子代理进程 PID 列表 |
| `created_at` | string | 创建时间（ISO 8601） |
| `heartbeat` | string | 最后心跳时间（ISO 8601） |
| `task_id` | string/null | 关联的任务 ID |

**Git 策略**：`.state/active_teams.json` **不应**提交到 Git（包含瞬时 PID 状态）。

---

## 协议三阶段

### 阶段 1：登记与绑定

**触发时机**：`TeamCreate` 工具调用时

**流程**：
```python
async def team_create_tool(team_id, task_id, sub_agent_count=2):
    # 1. 启动子代理进程
    member_pids = []
    for i in range(sub_agent_count):
        process = subprocess.Popen([...])
        member_pids.append(process.pid)
    
    # 2. 原子写入注册表
    register_team(
        team_id=team_id,
        leader_pid=os.getpid(),
        member_pids=member_pids,
        task_id=task_id
    )
    
    # 3. 启动子代理心跳
    for pid in member_pids:
        start_heartbeat_daemon(pid, leader_pid=os.getpid())
```

**原则**：没有写入注册表的子进程不允许启动。

---

### 阶段 2：存活心跳

**子代理行为**：
- 每隔 30-60 秒更新 `heartbeat` 时间戳
- 持续检查 `leader_pid` 是否存活
- 如果发现 Leader 已退出，执行**自杀协议**

**心跳脚本伪代码**：
```python
def heartbeat_loop(team_id, leader_pid):
    while True:
        # 1. 自杀协议：检查父进程
        if not psutil.pid_exists(leader_pid):
            print(f"父进程 {leader_pid} 已丢失，执行自杀...")
            cleanup_and_exit()
        
        # 2. 更新心跳
        update_team_heartbeat(team_id)
        
        # 3. 等待下一个周期
        time.sleep(30)
```

---

### 阶段 3：收割（Reaping）

**触发时机**：
- `recover()` 执行时
- 手动调用 `reap_orphaned_teams()` 时

**收割协议流程**：

| 检查步骤 | 检测逻辑 | 动作 |
|---------|---------|------|
| 1. 亲子关系验证 | `leader_pid` 是否在 OS 进程表中？ | 若不存在：标记该 Team 为"孤儿" |
| 2. 僵尸扫描 | `member_pids` 是否还在运行？ | 若在运行：发送 SIGTERM/SIGKILL |
| 3. 状态回滚 | 关联的 `task_id` 状态 | 将任务从 `in_progress` 重置为 `pending` |
| 4. 注册表清理 | 移除已终止的团队条目 | 原子写入更新后的 `active_teams.json` |

**收割实现**：
```python
def reap_orphaned_teams(state_dir):
    teams_file = Path(state_dir) / "active_teams.json"
    if not teams_file.exists():
        return
    
    teams_data = load_json(teams_file)
    remaining_teams = []
    
    for team in teams_data.get("active_teams", []):
        leader_pid = team["leader_pid"]
        
        # 检查父进程（Leader）是否还活着
        if not psutil.pid_exists(leader_pid):
            print(f"检测到孤儿团队: {team['team_id']}，正在清理...")
            
            # 终止子进程
            for m_pid in team.get("member_pids", []):
                if psutil.pid_exists(m_pid):
                    p = psutil.Process(m_pid)
                    p.terminate()  # 先礼后兵
                    try:
                        p.wait(timeout=5)
                    except:
                        p.kill()  # 超时后强制 kill
            
            # 回滚关联任务状态
            if team.get("task_id"):
                reset_task_to_pending(team["task_id"])
        else:
            remaining_teams.append(team)
    
    # 原子写回更新后的注册表
    write_json_atomic(teams_file, {"active_teams": remaining_teams})
```

---

## MCP 工具详解

### register_team

```python
register_team(
    project_dir: str = ".",
    team_id: str = "team-001",
    member_pids: List[int] = [12346, 12347],
    task_id: str = "task-005"
) -> dict
```

**功能**：将团队信息持久化到注册表

**返回值**：
```json
{
  "success": true,
  "team_id": "team-001",
  "leader_pid": 12345,
  "member_pids": [12346, 12347],
  "registered_at": "2025-06-15T16:00:00Z"
}
```

### update_team_heartbeat

```python
update_team_heartbeat(
    project_dir: str = ".",
    team_id: str = "team-001"
) -> dict
```

**功能**：更新团队心跳时间戳（由子代理调用）

### reap_orphaned_teams

```python
reap_orphaned_teams(
    project_dir: str = ".",
    dry_run: bool = false
) -> dict
```

**功能**：检测并清理孤儿团队

**返回值**：
```json
{
  "success": true,
  "orphan_teams_found": 1,
  "processes_terminated": [12346, 12347],
  "tasks_reset": ["task-005"],
  "dry_run": false
}
```

### deregister_team

```python
deregister_team(
    project_dir: str = ".",
    team_id: str = "team-001"
) -> dict
```

**功能**：正常解散团队，从注册表移除

---

## 心跳脚本实现

完整的子代理心跳脚本 `heartbeat_daemon.py`：

```python
#!/usr/bin/env python3
"""
子代理心跳守护进程
由 Leader 在启动子代理时一并启动
"""

import os
import sys
import json
import time
import signal
import psutil
import shutil
from pathlib import Path
from datetime import datetime

# 配置
HEARTBEAT_INTERVAL = 30  # 秒
STATE_DIR = Path(".state")
TEAMS_FILE = STATE_DIR / "active_teams.json"


def load_json(path):
    """安全加载 JSON"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return None


def is_valid_json(path):
    """验证 JSON 有效性"""
    try:
        with open(path, 'r') as f:
            json.load(f)
        return True
    except:
        return False


def atomic_update_heartbeat(team_id):
    """原子更新心跳时间戳"""
    if not TEAMS_FILE.exists():
        return False
    
    tmp_path = TEAMS_FILE.with_suffix(".tmp")
    bak_path = TEAMS_FILE.with_suffix(".bak")
    
    # 读取当前数据
    data = load_json(TEAMS_FILE)
    if not data:
        return False
    
    # 修改匹配团队的时间戳
    updated = False
    for team in data.get("active_teams", []):
        if team["team_id"] == team_id:
            team["heartbeat"] = datetime.now().isoformat()
            updated = True
            break
    
    if not updated:
        return False  # 团队已被删除
    
    # 原子写入
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    if is_valid_json(tmp_path):
        shutil.copy(TEAMS_FILE, bak_path)
        tmp_path.replace(TEAMS_FILE)
        return True
    return False


def check_leader_alive(leader_pid):
    """检查父进程是否存活"""
    return psutil.pid_exists(leader_pid)


def suicide_cleanup():
    """自杀前的清理"""
    print(f"[{datetime.now()}] 检测到 Leader 丢失，执行自杀...")
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("用法: heartbeat_daemon.py <team_id> <leader_pid>")
        sys.exit(1)
    
    team_id = sys.argv[1]
    leader_pid = int(sys.argv[2])
    
    print(f"[{datetime.now()}] 心跳守护启动: team={team_id}, leader_pid={leader_pid}")
    
    # 设置信号处理
    def signal_handler(signum, frame):
        print(f"[{datetime.now()}] 收到信号 {signum}，退出心跳守护")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # 主循环
    while True:
        try:
            # 1. 自杀协议
            if not check_leader_alive(leader_pid):
                suicide_cleanup()
            
            # 2. 更新心跳
            atomic_update_heartbeat(team_id)
            
            # 3. 等待
            time.sleep(HEARTBEAT_INTERVAL)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[{datetime.now()}] 心跳错误: {e}")
            time.sleep(HEARTBEAT_INTERVAL)
    
    print(f"[{datetime.now()}] 心跳守护正常退出")


if __name__ == "__main__":
    main()
```

**启动方式**：
```bash
# Leader 启动子代理时
python3 heartbeat_daemon.py <team_id> <leader_pid> &
```

---

## 集成到 recover()

`recover()` 工具会自动执行孤儿团队收割：

```python
async def recover_impl(project_dir: str, force: bool = False, dry_run: bool = False):
    actions = []
    
    # ... 其他恢复步骤 ...
    
    # 阶段 X：收割孤儿 Agent Teams
    teams_file = state_dir / "active_teams.json"
    if teams_file.exists():
        teams_data = load_json(teams_file)
        active_teams = teams_data.get("active_teams", [])
        remaining_teams = []
        
        for team in active_teams:
            leader_pid = team.get("leader_pid")
            team_id = team.get("team_id")
            
            # 如果 Leader 进程已不存在，则该团队为孤儿
            if not psutil.pid_exists(leader_pid):
                actions.append(f"发现孤儿团队 {team_id} (Leader PID {leader_pid} 已终止)")
                
                # 终止子进程
                for m_pid in team.get("member_pids", []):
                    if psutil.pid_exists(m_pid):
                        if not dry_run:
                            p = psutil.Process(m_pid)
                            p.terminate()
                        actions.append(f"  └─ 终止子进程 PID: {m_pid}")
                
                # 回滚关联任务
                if team.get("task_id") and not dry_run:
                    reset_task_to_pending(team["task_id"])
                    actions.append(f"  └─ 重置任务: {team['task_id']}")
            else:
                remaining_teams.append(team)
        
        if not dry_run:
            write_json_atomic(teams_file, {"active_teams": remaining_teams})
    
    return {"success": True, "actions": actions}
```

---

## 故障排除

### 现象：子代理仍在运行但 Leader 已崩溃

**检测**：
```bash
ps aux | grep claude
```

**解决**：
```python
# 新会话自动处理
recover(project_dir=".")
```

### 现象：active_teams.json 损坏

**症状**：JSON 解析错误

**解决**：
```python
# recover() 会自动从 .bak 恢复
recover(project_dir=".", force=True)
```

### 现象：心跳更新冲突（Race Condition）

**症状**：多个子代理同时更新导致数据丢失

**解决**：心跳脚本已实现原子写入（`.tmp` → `.bak` → `mv`），如仍冲突可考虑：
1. 使用文件锁（`fcntl` 或 `portalocker`）
2. 错峰更新（随机延迟）

---

## 局限性与扩展

### 当前局限

| 局限 | 说明 |
|------|------|
| 单机限制 | PID 检查仅在单机有效 |
| 权限要求 | 需要足够的权限检查/终止进程 |
| 心跳延迟 | 30 秒窗口期内可能产生资源浪费 |

### 分布式扩展

如果未来涉及跨机器运行（Docker 容器或不同服务器）：

| 方案 | 替换项 |
|------|--------|
| UUID 替代 PID | `leader_pid` → `leader_uuid` |
| Redis TTL | 心跳写入 Redis，设置过期时间 |
| 服务发现 | Consul/etcd 注册服务实例 |

---

**相关文档**：
- `recovery-protocol.md` - 完整恢复流程
- `sop.md` - 标准操作规程
- `infrastructure.md` - 状态文件格式
