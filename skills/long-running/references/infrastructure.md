# Long-Running Infrastructure — 状态管理基础设施

> **⭐ 重要更新**: 本 skill 已升级为 SQLite 数据库架构，提供更强大的并发控制、ACID 事务和原子操作支持。JSON 文件格式仍保留用于向后兼容。

## 目录

- [架构概览](#架构概览)
- [存储层对比](#存储层对比-json-vs-sqlite)
- [数据库 Schema 详解](#数据库-schema-详解)
- [文件格式详解（向后兼容）](#文件格式详解向后兼容)
- [原子操作协议](#原子操作协议)
- [事务一致性保障](#事务一致性保障)
- [任务依赖与 DAG 检测](#任务依赖与-dag-检测)
- [多代理并发控制](#多代理并发控制)
- [Git 版本绑定](#git-版本绑定)
- [MCP 工具说明](#mcp-工具说明)

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Server Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  initialize │  │   recover   │  │  atomic_start_task  │  │
│  │  get_status │  │ start_daemon│  │   complete_task     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    SkillStorage Wrapper                     │
│         (Python class - references/skill_storage.py)        │
│  - 乐观锁 (CAS)              - Git hash 校验                 │
│  - 连接池管理                - 自动初始化/迁移               │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              SQLite Database (.state/project_storage.db)    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ projects │ │  tasks   │ │task_deps │ │  teams   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ team_mem │ │knowledge │ │ session  │ │ artifacts│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
          │
          ▼ (向后兼容)
┌─────────────────────────────────────────────────────────────┐
│              Legacy JSON Files (.state/*.json)              │
│         checkpoint.json, task-queue.json, etc.              │
└─────────────────────────────────────────────────────────────┘
```

---

## 存储层对比: JSON vs SQLite

| 特性 | JSON 文件 (旧) | SQLite 数据库 (新) |
|------|---------------|-------------------|
| **并发控制** | 文件锁，易冲突 | 行级锁 + 乐观锁 (version 字段) |
| **原子性** | 手动 `.tmp` → `.bak` → `mv` | ACID 事务内置 |
| **查询复杂度** | O(N) 全量加载 | O(1) 索引查询 |
| **并发写入** | 易覆盖（丢失更新） | CAS 乐观锁防冲突 |
| **多机扩展** | 困难 | 支持 NFS 共享存储 |
| **数据完整性** | 依赖应用层校验 | 外键约束 + CHECK 约束 |
| **备份恢复** | 手动 `.bak` 文件 | 事务日志 + 自动恢复 |
| **Git 绑定** | 需额外记录 | `git_hash` 字段内置 |

**推荐**: 新项目直接使用 SQLite，旧项目可通过 `recover()` 自动迁移。

---

## 数据库 Schema 详解

### 核心表结构

```sql
-- 项目核心状态表
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT CHECK(status IN ('active', 'paused', 'completed', 'failed')),
    git_hash TEXT,                              -- ⭐ 代码版本绑定
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 任务队列表（替代 task-queue.json）
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    project_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'completed', 'failed', 'blocked')),
    priority TEXT DEFAULT 'medium',
    retry_count INTEGER DEFAULT 0,
    version INTEGER DEFAULT 0,                  -- ⭐ 乐观锁版本号
    owner TEXT,                                 -- 当前执行者
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

-- 任务依赖表（DAG 支持）
CREATE TABLE task_dependencies (
    task_id TEXT,
    depends_on_id TEXT,
    PRIMARY KEY (task_id, depends_on_id),
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY(depends_on_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

-- 知识库与决策记录
CREATE TABLE knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    topic TEXT,
    decision TEXT NOT NULL,
    rationale TEXT,
    context_tags TEXT,                          -- JSON 数组，支持语义检索
    task_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

-- Agent Teams 注册表
CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'failed')),
    agent_type TEXT DEFAULT 'team-lead',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

-- 团队成员表（含心跳信息）
CREATE TABLE team_members (
    member_id TEXT PRIMARY KEY,
    team_id TEXT,
    name TEXT NOT NULL,
    role TEXT,
    pid INTEGER,
    last_heartbeat TIMESTAMP,
    status TEXT DEFAULT 'active',
    FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
);

-- 成果文件表（工作缓冲区）
CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    team_id TEXT,
    creator TEXT,
    creator_role TEXT,
    artifact_type TEXT CHECK(artifact_type IN ('research_note', 'review_report', 'analysis_result', 'design_doc', 'code_snippet', 'log_file', 'temp_data', 'other')),
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    visibility TEXT DEFAULT 'team' CHECK(visibility IN ('public', 'team', 'leader_only', 'private')),
    tags TEXT,                                  -- JSON 数组
    file_path TEXT,                             -- 大内容可存外部文件
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
);

-- 会话日志表
CREATE TABLE session_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    session_id TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

-- 性能索引
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_owner ON tasks(owner);
CREATE INDEX idx_deps_task ON task_dependencies(task_id);
CREATE INDEX idx_knowledge_project ON knowledge_base(project_id);
CREATE INDEX idx_artifacts_team ON artifacts(team_id);
```

### 乐观锁 (CAS) 机制

```python
# 原子化申领任务示例
def atomic_start_task(conn, task_id, owner):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks 
        SET status = 'in_progress', 
            started_at = ?,
            owner = ?,
            version = version + 1          -- 版本号递增
        WHERE task_id = ? 
          AND status = 'pending'           -- 条件检查
    """, (datetime.now().isoformat(), owner, task_id))
    
    if cursor.rowcount == 0:
        # 更新失败：可能已被其他 agent 抢占
        return False
    return True
```

**工作原理**:
1. 读取任务时记录 `version`
2. 更新时检查 `status = 'pending'`
3. 同时递增 `version` 字段
4. 如果 `rowcount == 0`，说明条件不满足（被抢占或状态改变）

---

## 文件格式详解（向后兼容）

> JSON 文件格式保留用于：
> 1. 向后兼容旧项目
> 2. 人类可读的状态导出
> 3. Git diff 友好的变更追踪

### checkpoint.json — 项目检查点（版本 2）

```json
{
  "version": 2,
  "project_name": "my-web-app",
  "created_at": "2025-06-15T10:00:00Z",
  "updated_at": "2025-06-15T16:30:00Z",
  "status": "active",
  "progress_percent": 58.33,
  "session_count": 5,
  "total_tasks": 12,
  "completed_tasks": 7,
  "in_progress_tasks": 1,
  "pending_tasks": 3,
  "blocked_tasks": 1,
  "failed_tasks": 0,
  "git_hash": "a1b2c3d4e5f6",           // ⭐ 代码版本绑定
  "recent_errors": [...],
  "dependency_health": "valid",
  "teams_used": {...},
  "recent_sessions": [...],
  "summary": "已完成认证模块（7/12）..."
}
```

### task-queue.json — 任务队列

```json
{
  "version": 1,
  "updated_at": "2025-06-15T16:30:00Z",
  "tasks": [
    {
      "id": "task-001",
      "title": "搭建项目基础结构",
      "description": "...",
      "status": "completed",
      "priority": "high",
      "depends_on": [],
      "version": 3,                          // ⭐ 乐观锁版本号
      "owner": "agent-001",
      "created_at": "2025-06-15T10:00:00Z",
      "started_at": "2025-06-15T10:00:00Z",
      "completed_at": "2025-06-15T10:45:00Z"
    }
  ]
}
```

---

## 原子操作协议

### 数据库事务原子性

```python
from contextlib import contextmanager

@contextmanager
def atomic_transaction(storage):
    """原子事务上下文管理器"""
    conn = storage._get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")  # 立即获取写锁
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# 使用示例
with atomic_transaction(storage) as conn:
    # 1. 更新任务状态
    conn.execute("UPDATE tasks SET ...")
    # 2. 记录知识库
    conn.execute("INSERT INTO knowledge_base ...")
    # 3. 更新团队心跳
    conn.execute("UPDATE team_members ...")
    # 全部成功或全部回滚
```

### 对比：JSON 原子写入（旧方案）

```python
# 仅用于向后兼容或导出
def write_json_atomic(filepath: Path, data: dict) -> bool:
    tmp_path = filepath.with_suffix(".tmp")
    bak_path = filepath.with_suffix(".bak")
    
    # 1. 写入临时文件
    with open(tmp_path, "w") as f:
        json.dump(data, f)
    
    # 2. 验证 JSON
    with open(tmp_path, "r") as f:
        json.load(f)  # 验证
    
    # 3. 备份现有文件
    if filepath.exists():
        shutil.copy(filepath, bak_path)
    
    # 4. 原子替换
    shutil.move(str(tmp_path), str(filepath))
```

---

## 事务一致性保障

### 数据库层面的一致性

```python
def sync_checkpoint_from_db(storage, project_id):
    """从数据库生成 checkpoint 快照"""
    stats = storage.get_stats(project_id)
    
    checkpoint = {
        "version": 2,
        "total_tasks": sum(stats['tasks'].values()),
        "completed_tasks": stats['tasks'].get('completed', 0),
        "in_progress_tasks": stats['tasks'].get('in_progress', 0),
        "pending_tasks": stats['tasks'].get('pending', 0),
        "failed_tasks": stats['tasks'].get('failed', 0),
        "blocked_tasks": stats['tasks'].get('blocked', 0),
        "git_hash": storage.get_project(project_id)['git_hash'],
        "progress_percent": round(
            stats['tasks'].get('completed', 0) / sum(stats['tasks'].values()) * 100, 2
        ) if stats['tasks'] else 0.0
    }
    return checkpoint
```

### 导出为 JSON（Git 友好）

```python
def export_to_json(storage, project_id, state_dir):
    """导出数据库状态到 JSON（用于 Git 提交）"""
    checkpoint = sync_checkpoint_from_db(storage, project_id)
    tasks = storage.get_tasks_by_status(None, project_id)  # 所有任务
    knowledge = storage.get_knowledge(project_id, limit=1000)
    
    # 写入 JSON 文件
    write_json_atomic(
        state_dir / "checkpoint.json", 
        checkpoint
    )
    write_json_atomic(
        state_dir / "task-queue.json",
        {"version": 1, "tasks": tasks}
    )
```

---

## 任务依赖与 DAG 检测

### 查询可执行任务（依赖已满足）

```sql
-- 获取所有 pending 且依赖已全部完成的任务
SELECT t.* FROM tasks t
WHERE t.status = 'pending'
AND NOT EXISTS (
    SELECT 1 FROM task_dependencies td
    JOIN tasks dep ON td.depends_on_id = dep.task_id
    WHERE td.task_id = t.task_id
    AND dep.status != 'completed'
)
ORDER BY 
    CASE t.priority 
        WHEN 'high' THEN 1 
        WHEN 'medium' THEN 2 
        ELSE 3 
    END;
```

### Python 实现

```python
def get_ready_tasks(self, project_id=None):
    """
    获取可执行的任务列表（依赖已满足）。
    返回按优先级排序的任务列表。
    """
    with self._get_connection() as conn:
        query = """
            SELECT t.* FROM tasks t
            WHERE t.status = 'pending'
            AND NOT EXISTS (
                SELECT 1 FROM task_dependencies td
                JOIN tasks dep ON td.depends_on_id = dep.task_id
                WHERE td.task_id = t.task_id
                AND dep.status != 'completed'
            )
        """
        params = []
        if project_id:
            query += " AND t.project_id = ?"
            params.append(project_id)
        
        query += """ ORDER BY 
            CASE t.priority 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                ELSE 3 
            END"""
        
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
```

### 循环依赖检测

```python
def detect_circular_dependencies(self):
    """检测任务依赖图中的环路"""
    with self._get_connection() as conn:
        rows = conn.execute(
            "SELECT task_id, depends_on_id FROM task_dependencies"
        ).fetchall()
        
        # 构建图
        graph = {}
        for row in rows:
            if row['task_id'] not in graph:
                graph[row['task_id']] = []
            graph[row['task_id']].append(row['depends_on_id'])
        
        # DFS 检测环路
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        result = dfs(neighbor)
                        if result:
                            return result
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor)
                        cycles.append(path[cycle_start:] + [neighbor])
            
            path.pop()
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node)
        
        return cycles
```

---

## 多代理并发控制

### 并发场景处理

| 场景 | 处理机制 | 结果 |
|------|---------|------|
| Agent A 和 B 同时申领同一任务 | `atomic_start_task()` 的 CAS 机制 | 只有一人成功，另一人收到失败提示 |
| Agent A 更新任务时 B 读取 | SQLite 的读锁不阻塞读 | B 读取到旧版本，下次查询获取最新 |
| Agent A 更新任务时 B 写入 | SQLite 的写锁串行化 | B 等待 A 事务完成后执行 |
| Leader 崩溃后子 Agent 写入 | `recover()` 重置孤儿任务 | 任务状态回滚，子 Agent 写入被拒绝 |

### 最佳实践

```python
# ✅ 正确：使用原子操作
success, msg = storage.atomic_start_task("task-001", owner="agent-a")
if not success:
    # 选择其他任务
    ready_tasks = storage.get_ready_tasks()
    ...

# ❌ 错误：直接查询修改
# 可能导致丢失更新
task = storage.get_task("task-001")
if task['status'] == 'pending':  # 此时可能被其他 agent 修改
    storage.update_task_status("task-001", "in_progress")  # 覆盖他人修改
```

---

## Git 版本绑定

### 代码版本一致性校验

```python
class SkillStorage:
    @staticmethod
    def get_current_git_hash():
        """获取当前 Git commit hash"""
        try:
            return subprocess.check_output(
                ['git', 'rev-parse', 'HEAD']
            ).decode().strip()
        except:
            return None
    
    def recover_orphaned_tasks(self, current_git_hash=None):
        """
        崩溃恢复，包含 Git hash 校验
        """
        with self._get_connection() as conn:
            if current_git_hash:
                project = conn.execute(
                    "SELECT git_hash FROM projects LIMIT 1"
                ).fetchone()
                
                if project and project['git_hash']:
                    if project['git_hash'] != current_git_hash:
                        return False, (
                            f"⚠️ 版本冲突：快照记录为 {project['git_hash'][:7]}，"
                            f"当前为 {current_git_hash[:7]}"
                        )
            
            # 重置孤儿任务
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'pending', owner = NULL, version = version + 1
                WHERE status = 'in_progress'
            """)
            conn.commit()
            
            return True, f"成功恢复 {cursor.rowcount} 个孤儿任务"
```

### 恢复流程中的版本检查

```
recover() 启动
    │
    ▼
获取 current_git_hash = git rev-parse HEAD
    │
    ▼
查询数据库中的记录 git_hash
    │
    ├─ 一致 → 继续恢复
    │
    └─ 不一致 → 警告用户
              "代码版本与快照不匹配"
              选项 1: git checkout 到记录版本
              选项 2: 以当前代码为准，重置所有状态
```

---

## MCP 工具说明

### 数据库核心工具

| 工具 | 功能 | 使用场景 |
|------|------|---------|
| `SkillStorage()` | 初始化数据库连接 | 每个会话开始 |
| `atomic_start_task()` | 原子化申领任务 | 开始执行任务前 |
| `complete_task()` | 标记任务完成 | 任务成功后 |
| `get_ready_tasks()` | 获取可执行任务 | 选择下一个任务 |
| `recover_orphaned_tasks()` | 崩溃恢复 | `recover()` 内部调用 |
| `add_knowledge()` | 记录决策 | 关键选择时 |

### 工具使用示例

```python
# 完整会话流程
from skill_storage import SkillStorage

# 1. 初始化
storage = SkillStorage(".state/project_storage.db")

# 2. 恢复（含 Git hash 校验）
import subprocess
current_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
success, msg = storage.recover_orphaned_tasks(current_hash)
print(msg)

# 3. 获取可执行任务
ready_tasks = storage.get_ready_tasks()

# 4. 原子化申领
for task in ready_tasks:
    success, msg = storage.atomic_start_task(task['task_id'], owner="main-agent")
    if success:
        # 执行任务...
        execute_task(task)
        
        # 5. 标记完成
        storage.complete_task(task['task_id'])
        
        # 6. 记录关键决策
        storage.add_knowledge(
            project_id=task['project_id'],
            decision="使用 bcrypt 替代 argon2",
            rationale="兼容性更好",
            context_tags=["auth", "security"]
        )
        break
```

---

## 相关文档

- `recovery-protocol.md` - 崩溃恢复协议（含 Git 版本校验）
- `agent-teams.md` - Agent Teams 协作与孤儿清理
- `sop.md` - 标准操作规程完整版
- `skill_storage.py` - SkillStorage Python 实现
