---
name: agent-teams
description: Agent Teams 协作框架使用指南。当用户要求组建团队、并行开发、代码审查、多 agent 协作、任务编排，或提到 "team"、"swarm"、"协作"、"多 agent" 时，必须使用此技能。适用于需要多人协作的复杂任务（5+文件修改、全栈开发、研究+开发组合）。
---

# Agent Teams 快速参考

> 📚 **完整文档**：`references/` 目录 | 🤖 **自动化指南**：`references/leader-automation.md`

## 零、自我进化（可选）

- **获取规则**：`get_learned_rules_tool()`
- **记录矫正**：`capture_user_feedback_tool(instruction="...", category="...")`
- **MCP 不可用时**：手动记录到 `CLAUDE.md`

**详情**：`references/mcp-integration.md`

## 一、何时使用 Agent Teams

### 使用决策树

```
任务复杂吗？
  ├─ 修改 1-2 个文件 → 单人完成
  ├─ 修改 3-5 个文件 + 需要审查 → 2 人 Team
  ├─ 修改 5+ 文件或需要并行 → 3+ 人 Team
  └─ 需要研究 + 开发 → Researcher + Developer(s)
```

**经验法则**：
- < 100 行代码：单人
- 100-500 行：2 人 Team
- > 500 行：3-4 人 Team
- 全栈开发：前后端各 1 人 + 共享 tester
- 需要代码审查：增加 Reviewer

## 二、快速启动（5分钟）

### 最简单的 Team 使用示例

```bash
# 1. 检查系统资源（推荐）
get_permit_status_tool()  # 返回可用许可数，0表示内存紧张

# 2-3. 创建团队和任务
db_create_team_tool(team_name="hello-world", description="...")
db_create_task_tool(task_id="task-1", team_name="hello-world", subject="...", description="...", active_form="...")

# 4. 生成成员
Task(prompt="你是开发者...", name="developer", subagent_type="general-purpose", ...)

# 5. 分配任务并通知
db_update_task_tool(task_id="task-1", owner="developer")
SendMessage(type="message", recipient="developer", content="开始任务#1", summary="启动")

# 6. 等待完成通知...

# 7. 关闭团队
SendMessage(type="shutdown_request", recipient="developer", content="完成")
TeamDelete(team_name="hello-world")
```

## 三、核心架构

```
Leader (主控)
  ├── db_create_team_tool    → 创建团队（SQLite 原子操作）
  ├── db_create_task_tool    → 创建任务
  ├── db_update_task_tool    → 分配/更新任务（支持触发器）
  ├── db_get_ready_tasks_tool → 获取可执行任务
  ├── db_add_dependency_tool → 添加任务依赖（自动检测循环）
  ├── db_create_trigger_tool → 创建自动流转触发器
  ├── Task                   → 生成团队成员
  ├── SendMessage            → 与成员通信
  └── TeamDelete             → 删除团队

Teammate (成员)
  ├── db_get_ready_tasks_tool → 查找可用任务
  ├── TaskGet                → 获取任务详情
  ├── db_update_task_tool    → 更新任务状态/认领任务
  ├── db_add_task_ack_tool   → 发送任务确认
  ├── create_artifact_tool   → 创建成果文件
  ├── SendMessage            → 通知 Leader
  └── 专属工具              → Read/Write/Edit/Bash/Grep/Glob
```

## 四、关键工具速查

### 资源管理

```bash
get_permit_status_tool()

reserve_permit_tool(
    team_name="my-team",
    member_name="developer",
    task_type="refactoring",
    duration_minutes=30
)
```

### 团队与任务管理

```bash
db_create_team_tool(team_name="project-x", description="...")
db_create_task_tool(task_id="task-1", team_name="project-x", subject="...", description="...", active_form="...")
db_update_task_tool(task_id="task-1", owner="developer")
db_add_dependency_tool(task_id="task-2", depends_on_task_id="task-1")
db_get_ready_tasks_tool(team_name="project-x")
```

### 自动流转触发器

```bash
db_create_trigger_tool(
    team_name="project-x",
    trigger_type="on_complete",
    source_task_id="task-a",
    target_task_id="task-b",
    action="notify",
    action_params='{"recipient": "developer", "message": "前置任务已完成"}'
)
```

### 成果文件（Artifacts）

```bash
create_artifact_tool(
    team_name="project-x",
    creator="researcher-1",
    creator_role="researcher",
    artifact_type="research_note",
    title="API 设计方案调研",
    content="# 调研结果...",
    visibility="leader_only",
    summary="REST vs GraphQL 对比分析",
    tags='["api", "design"]'
)
```

## 五、标准工作流程

**Leader 流程**：检查资源 → 创建团队 → 创建任务/依赖 → 生成成员 → 分配任务 → 等待完成 → 关闭

**Teammate 流程**：等待分配 → ACK 确认 → 执行 → 标记完成 → SendMessage 通知

## 六、任务权重系统

| 类型 | 权重 | 预估内存 |
|------|------|---------|
| `read_only` | 1 | 200MB |
| `development` | 2 | 500MB |
| `testing` | 2 | 600MB |
| `refactoring` | 3 | 800MB |
| `build` | 3 | 1000MB |
| `heavy_analysis` | 3 | 900MB |

## 七、特殊场景

- **医学科研综述**：使用 `medical-review-skill`
