---
name: long-running
description: 长期运行代理持久化。当用户要求"初始化一个长期运行项目"、"项目中断了怎么恢复"、"查看项目进度"、"启动后台任务"、"停止后台任务"、"查看执行日志"时触发。适用于大型项目开发、多日协作、跨会话状态管理、中断恢复、Agent Teams 协作。
---

# Long-Running Skill

> **⚠️ 重要**: 本 Skill 管理长期运行项目的状态持久化。每个会话开始时**必须**先执行 `recover()` 进行环境对齐。

## 快速决策表

| 用户意图 | 立即调用 |
|---------|---------|
| "开始一个长期项目" | `initialize_project()` |
| "项目中断了"/"恢复项目" | `recover()` |
| "进度怎么样" | `get_status(show_tasks=true)` |
| "开始执行"/"启动后台" | `start_daemon()` |

## 会话启动强制协议 (SOP)

**⚠️ 每个新会话开始时必须按顺序执行：**

```
1. recover()           → 清理残留、收割孤儿进程、校验 Git 版本
2. get_status()        → 加载全局快照
3. git status          → 同步 Git 状态
```

## MCP 工具快速参考

### SkillStorage API（推荐）

```python
from skill_storage import SkillStorage

# 初始化
storage = SkillStorage(".state/project_storage.db")

# 项目操作
storage.create_project(project_id, name, git_hash=None)
storage.get_stats(project_id)

# 任务 CRUD
storage.create_task(task_id, project_id, title, description="", priority="medium")
storage.atomic_start_task(task_id, owner=None)
storage.complete_task(task_id)

# 依赖管理
storage.add_task_dependency(task_id, depends_on_id)
storage.get_ready_tasks(project_id)
```

### Agent Teams 专用工具

```python
# 创建团队
db_create_team(team_name, description="", agent_type="team-lead")

# 创建任务
db_create_task(task_id, team_name, subject, description="", priority=5)

# 更新任务状态
db_update_task(task_id, status=None, owner=None)

# 诊断团队状态
diagnose_team_status(team_name)

# 创建成果文件
create_artifact(team_name, creator, creator_role, artifact_type, title, content)
```

## 核心概念速查

| 概念 | 说明 |
|------|------|
| **Checkpoint** | 项目状态快照，含 Git hash 绑定 |
| **Task Queue** | 任务列表，含状态、优先级、版本号 |
| **Atomic Operation** | CAS 乐观锁，防止丢失更新 |
| **Recovery** | 清理残留 → 验证 Git → 重置孤儿任务 |
| **Permit System** | 内存/计算资源预算控制 |
| **Artifacts** | 中间成果存储，支持分级可见性 |

## 典型工作流

### 1. 新项目启动
```
initialize_project() → db_create_task() → start_daemon()
```

### 2. 中断后恢复
```
recover() → 校验 Git hash → 重置孤儿任务 → 继续执行
```

### 3. Agent Teams 协作
```
recover() → db_create_team() → db_create_task() → TeamCreate
```

## 最佳实践

1. **⚠️ 强制 recover**: 每个会话开始时必须先调用 `recover()`
2. **原子申领**: 使用 `atomic_start_task()` 防止重复工作
3. **资源预留**: 高负载任务前先 `reserve_permit()`
4. **频繁提交**: 每完成子步骤就 `git commit`
5. **知识记录**: 关键决策使用 `add_knowledge()`
