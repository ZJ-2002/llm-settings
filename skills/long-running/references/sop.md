# Long-Running SOP — 标准操作规程

> **⭐ 重要更新**: 本 SOP 已适配 SQLite 数据库架构，所有状态操作通过 `SkillStorage` 原子化 API 执行。

---

## 目录

- [会话启动检查清单](#一会话启动检查清单startup)
- [任务执行检查清单](#二任务执行检查清单execution)
- [会话收尾检查清单](#三会话收尾检查清单wrap-up)
- [故障排除速查](#四故障排除速查troubleshooting)
- [数据库操作指南](#五数据库操作指南)
- [最佳实践总结](#六最佳实践总结)

---

## 一、会话启动检查清单 (Startup)

**目标**：确保分析环境一致，清理历史遗留任务，校验代码版本。

### 1. 执行环境恢复

```python
from skill_storage import SkillStorage
import subprocess

# 初始化数据库连接
storage = SkillStorage(".state/project_storage.db")

# 获取当前 Git hash
current_hash = subprocess.check_output(
    ['git', 'rev-parse', 'HEAD']
).decode().strip()

# 执行恢复（含 Git hash 校验）
success, msg = storage.recover_orphaned_tasks(current_hash)
print(msg)

# 如果版本冲突，需要选择同步策略
if not success:
    print("⚠️ Git 版本冲突！")
    print("选项 1: git checkout 回退到记录版本")
    print("选项 2: 以当前代码为准，强制恢复")
```

### 2. 获取全局进度

```python
# 查询项目统计
stats = storage.get_stats()
print(f"任务统计: {stats['tasks']}")
print(f"活跃团队: {stats['teams']}")

# 查询可执行的任务
ready_tasks = storage.get_ready_tasks()
print(f"可执行任务: {len(ready_tasks)} 个")
for task in ready_tasks[:5]:
    print(f"  - {task['task_id']}: {task['title']}")
```

### 3. 检查计算资源

```python
# 对于高负载任务（如 Seurat 分析），先预留资源许可
result = reserve_permit(
    team_name="main",
    member_name="agent-001",
    task_type="heavy_analysis",  # 或 "development", "testing"
    duration_minutes=60
)

if result["success"]:
    print(f"资源许可已预留: {result['permit_id']}")
else:
    print(f"资源不足: {result['reason']}")
```

### 启动检查清单 ✓

- [ ] 已初始化 SkillStorage 数据库连接
- [ ] 已执行 `recover_orphaned_tasks()` 并校验 Git hash
- [ ] 已查询可执行任务列表
- [ ] （高负载任务）已预留资源许可

---

## 二、任务执行检查清单 (Execution)

**目标**：利用原子操作防止多 Agent 抢占，确保分析记录准确。

### 1. 原子化申领任务

```python
# ✅ 正确：使用原子操作申领任务
for task in ready_tasks:
    success, msg = storage.atomic_start_task(
        task_id=task['task_id'],
        owner="agent-001"  # 当前 agent 标识
    )
    
    if success:
        print(f"✓ 成功申领任务: {task['title']}")
        current_task = task
        break
    else:
        print(f"✗ 申领失败: {msg}")  # 任务已被抢占
        continue

if not current_task:
    print("无可用任务，等待中...")
    return
```

**⚠️ 严禁手动修改数据库状态！**

```python
# ❌ 错误：直接查询修改可能导致丢失更新
task = storage.get_task("task-001")
if task['status'] == 'pending':  # 此时可能被其他 agent 修改
    storage.update_task_status("task-001", "in_progress")  # 覆盖他人修改！
```

### 2. 核心计算执行

```python
try:
    # 执行任务...
    execute_task(current_task)
    
    # 标记完成
    storage.complete_task(current_task['task_id'])
    print(f"✓ 任务完成: {current_task['task_id']}")
    
except Exception as e:
    # 记录失败
    storage.fail_task(current_task['task_id'])
    
    # 记录错误日志
    record_error(
        team_name="main",
        error_content=str(e),
        context=f"任务 {current_task['task_id']} 执行失败"
    )
    print(f"✗ 任务失败: {e}")
```

### 3. 记录关键决策

```python
# 在分析过程中调整参数或做出决策时，必须记录
if parameter_changed:
    storage.add_knowledge(
        project_id="demo",
        decision=f"调整 nFeature_RNA 阈值从 200 到 500",
        rationale="过滤掉低质量细胞，提高聚类效果",
        context_tags=["single-cell", "qc", "seurat"],
        task_id=current_task['task_id']
    )
```

### 任务执行检查清单 ✓

- [ ] 使用 `atomic_start_task()` 申领任务
- [ ] 申领成功后才开始执行
- [ ] 执行完成后调用 `complete_task()`
- [ ] 失败时调用 `fail_task()` 并记录错误
- [ ] 关键决策使用 `add_knowledge()` 记录

---

## 三、会话收尾检查清单 (Wrap-up)

**目标**：固化实验状态，记录 session 日志，释放资源。

### 1. 释放资源

```python
# 释放资源许可（如果之前预留了）
# 自动在任务完成时释放
```

### 2. 导出状态到 JSON（用于 Git）

```python
# 导出数据库状态到 JSON，便于 Git 追踪
stats = storage.get_stats()

# checkpoint.json
checkpoint = {
    "version": 2,
    "git_hash": current_hash,
    **stats
}

with open(".state/checkpoint.json", "w") as f:
    json.dump(checkpoint, f, indent=2)

# task-queue.json
tasks = storage.get_tasks_by_status(None)
with open(".state/task-queue.json", "w") as f:
    json.dump({"version": 1, "tasks": tasks}, f, indent=2)
```

### 3. Git 提交

```bash
# 提交状态文件和代码变更
git add .state/project_storage.db  # SQLite 数据库
git add .state/checkpoint.json     # 导出的快照
git add .state/task-queue.json     # 导出的任务队列
git add src/ tests/                # 代码变更

git commit -m "feat: 完成 [任务ID] - [分析描述]

- 完成 task-XXX: 具体描述
- 关键决策: 记录到知识库
- Git hash: ${current_hash:0:7}"
```

### 会话收尾检查清单 ✓

- [ ] 所有任务状态已正确更新
- [ ] 资源许可已释放
- [ ] 数据库已导出到 JSON（可选但推荐）
- [ ] Git commit 包含代码和状态变更
- [ ] session-log.md 已更新（追加写入）

---

## 四、故障排除速查 (Troubleshooting)

### 常见症状与解决方案

| 症状 | 可能原因 | 解决方案 |
|------|---------|---------|
| `atomic_start_task` 持续返回 False | 任务已被抢占或版本冲突 | 选择其他 `ready` 任务，或执行 `recover()` |
| 恢复时提示 "版本冲突" | Git hash 不匹配 | `git checkout <recorded_hash>` 或 `recover(force=True)` |
| 数据库读写超时 (Locked) | 并发写入过多或事务未提交 | 增加连接 timeout，检查是否有挂起的事务 |
| 检测到循环依赖 | 任务依赖形成环路 | 手动修复 `task_dependencies` 表中的依赖关系 |
| 任务状态不一致 | 并发修改或崩溃残留 | 执行 `recover()` 强制重置版本和状态 |
| 孤儿 Teams 残留 | Leader 崩溃未清理 | `recover()` 自动收割，或使用 Pipe 监控 |
| `get_ready_tasks` 返回空 | 所有任务被阻塞或已完成 | 检查依赖状态，或使用 `detect_circular_dependencies()` |

### 数据库调试命令

```python
# 查看所有任务状态
with storage._get_connection() as conn:
    rows = conn.execute("""
        SELECT task_id, status, owner, version 
        FROM tasks 
        ORDER BY status
    """).fetchall()
    for row in rows:
        print(f"{row['task_id']}: {row['status']} (owner={row['owner']}, v={row['version']})")

# 查看任务依赖
with storage._get_connection() as conn:
    rows = conn.execute("""
        SELECT t.task_id, t.title, 
               GROUP_CONCAT(td.depends_on_id) as deps
        FROM tasks t
        LEFT JOIN task_dependencies td ON t.task_id = td.task_id
        GROUP BY t.task_id
    """).fetchall()
    for row in rows:
        print(f"{row['task_id']}: {row['title']}")
        print(f"  依赖: {row['deps']}")

# 手动重置任务（紧急情况下使用）
with storage._get_connection() as conn:
    conn.execute("""
        UPDATE tasks 
        SET status = 'pending', owner = NULL, version = version + 1
        WHERE task_id = 'task-001'
    """)
    conn.commit()
```

---

## 五、数据库操作指南

### 连接数据库

```python
from skill_storage import SkillStorage

# 自动初始化表结构
storage = SkillStorage(".state/project_storage.db")

# 或使用 sqlite3 直接连接（高级用法）
import sqlite3
conn = sqlite3.connect(".state/project_storage.db")
conn.row_factory = sqlite3.Row  # 启用字典式访问
```

### 常用查询

```python
# 获取项目概览
project = storage.get_project("demo")
print(f"项目: {project['name']}")
print(f"Git hash: {project['git_hash']}")

# 获取任务统计
stats = storage.get_stats("demo")
for status, count in stats['tasks'].items():
    print(f"  {status}: {count}")

# 查询特定任务
task = storage.get_task("task-001")
print(f"任务: {task['title']}")
print(f"状态: {task['status']}")
print(f"版本: {task['version']}")

# 获取任务的依赖
deps = storage.get_task_dependencies("task-001")
for dep in deps:
    print(f"  依赖: {dep['task_id']} - {dep['status']}")
```

### 事务操作

```python
# 手动事务（高级用法）
with storage._get_connection() as conn:
    try:
        conn.execute("BEGIN IMMEDIATE")
        
        # 多个相关操作
        conn.execute("UPDATE tasks SET ...")
        conn.execute("INSERT INTO knowledge_base ...")
        conn.execute("UPDATE teams SET ...")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
```

### 备份与恢复

```python
import shutil
from datetime import datetime

# 备份数据库
def backup_database(db_path=".state/project_storage.db"):
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(db_path, backup_path)
    print(f"备份已创建: {backup_path}")
    return backup_path

# 从备份恢复
def restore_database(backup_path, db_path=".state/project_storage.db"):
    shutil.copy(backup_path, db_path)
    print(f"数据库已恢复: {db_path}")
```

---

## 六、最佳实践总结

### 1. 会话管理

```python
# 每个会话的标准流程
def session_workflow():
    # 1. 恢复
    storage = SkillStorage()
    current_hash = get_current_git_hash()
    storage.recover_orphaned_tasks(current_hash)
    
    # 2. 获取任务
    ready = storage.get_ready_tasks()
    
    # 3. 申领并执行
    for task in ready:
        if storage.atomic_start_task(task['task_id']):
            execute(task)
            storage.complete_task(task['task_id'])
            break
    
    # 4. 提交
    git_commit_changes()
```

### 2. 并发安全

- **总是**使用 `atomic_start_task()` 申领任务
- **绝不**直接修改 `tasks` 表的状态字段
- **绝不**在多个 agent 中手动分配任务
- 依赖数据库的原子性保证正确性

### 3. 错误处理

```python
try:
    success, msg = storage.atomic_start_task(task_id)
    if not success:
        # 正常竞争失败，选择其他任务
        continue
    
    # 执行任务
    result = execute_task(task)
    
except Exception as e:
    # 意外错误，记录并标记失败
    storage.fail_task(task_id)
    record_error(team_name, str(e), context)
    raise
```

### 4. 知识管理

- 关键决策 **立即**记录到知识库
- 使用 `context_tags` 便于后续检索
- 定期回顾 `knowledge_base` 避免重复犯错

### 5. Git 工作流

- 每个有意义的进度都 `git commit`
- Commit message 包含完成的任务 ID
- 始终包含 `.state/` 中的状态文件
- 切换分支后 **必须**执行 `recover()`

---

**相关文档**:
- `infrastructure.md` - 数据库架构详解
- `recovery-protocol.md` - 崩溃恢复协议
- `skill_storage.py` - SkillStorage 完整实现
