# Agent Teams 模板库

本目录包含 Agent Teams 的配置文件模板和角色提示词模板。

---

## 快速开始

### 方法 1：直接使用工具参数（推荐）

```bash
# 1. 创建团队
TeamCreate(
  team_name="my-project",
  description="我的项目描述"
)

# 2. 创建任务
TaskCreate(
  subject="实现用户登录功能",
  description="在 src/auth.ts 中实现登录，包含密码验证和 JWT 生成",
  activeForm="正在实现用户登录功能"
)

# 3. 生成成员（使用 role.md 中的 Prompt 模板）
Task(
  prompt="[从 role.md 复制 Developer Prompt 模板，替换 {team_name} 为 my-project]",
  subagent_type="general-purpose",
  name="developer",
  team_name="my-project",
  run_in_background=true
)
```

### 方法 2：参考模板文件

1. 参考 `team-config.json` 了解团队配置结构
2. 参考 `task-template.json` 了解任务字段
3. 参考 `role-prompt-template.md` 获取角色 Prompt 模板

---

## 模板文件说明

| 模板 | 用途 | 使用时机 |
|------|------|----------|
| `team-config.json` | 团队配置参考 | 规划团队结构时 |
| `task-template.json` | 任务字段参考 | 规划任务时 |
| `role-prompt-template.md` | 角色 Prompt 模板 | 生成成员时 |
| `workflow-template.json` | 工作流定义参考 | 规划项目流程时 |
| `loop-protection-template.md` | 循环防护模板 | 自定义角色时 |

---

## 变量说明

模板中使用 `{{VARIABLE}}` 或 `{variable}` 格式的变量需要替换：

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `{{TIMESTAMP}}` | ISO 时间戳 | 2026-03-11T12:00:00Z |
| `{team_name}` | 团队名称 | my-project |
| `{leader_name}` | Leader 名称 | team-lead |

---

## 详细字段说明

### team-config.json（配置参考）

此文件描述团队配置的结构，但 **不是直接传入 TeamCreate 的参数**。

```json
{
  "team_name": "your-project-name",      // 团队名称
  "description": "项目描述",              // 项目描述
  "created_at": "{{TIMESTAMP}}",         // 创建时间
  "roles": {
    "developer": {
      "subagent_type": "general-purpose", // 成员类型
      "model": "sonnet",                  // 模型选择
      "prompt_template": "See role.md",   // Prompt 参考
      "tools": ["Read", "Write", ...]     // 可用工具
    }
  },
  "communication_policy": {...},          // 通信策略
  "task_policy": {...}                    // 任务策略
}
```

**正确用法**：参考此结构规划团队，然后调用：
```bash
TeamCreate(team_name="your-project-name", description="项目描述")
```

### task-template.json（字段参考）

此文件描述任务的结构：

```json
{
  "subject": "任务标题",           // 必填
  "description": "详细描述...",    // 必填
  "activeForm": "正在进行中...",   // 必填
  "priority": "high",             // 可选：high/medium/low
  "owner": null,                  // 自动分配
  "status": "pending",            // 初始状态
  "depends_on": [],               // 别名，等同于 blockedBy
  "blocked_by": []                // 依赖的任务 ID 列表
}
```

**正确用法**：参考此结构规划任务，然后调用：
```bash
TaskCreate(
  subject="任务标题",
  description="详细描述...",
  activeForm="正在进行中..."
)
```

### role-prompt-template.md

角色提示词模板，包含：
- Developer（开发者）
- Tester（测试员）
- Reviewer（审查员）
- Researcher（研究员）
- Architect（架构师）

每个模板都包含：
- 职责说明
- 工作流程
- 沟通规则
- 循环防护

**正确用法**：
```bash
# 1. 从 role-prompt-template.md 复制 Developer 模板
# 2. 替换 {team_name} 和 {leader_name}
# 3. 在 Task 的 prompt 参数中使用

Task(
  prompt="你是团队 'my-project' 中的开发者...",
  subagent_type="general-purpose",
  name="developer",
  team_name="my-project",
  run_in_background=true
)
```

### workflow-template.json

工作流模板，定义：
- 工作流名称和描述
- 参与角色
- 各阶段定义

**正确用法**：参考此文件规划项目阶段和任务依赖。

---

## 常见错误

### ❌ 错误：尝试将 JSON 文件作为参数传入

```bash
# 错误！TeamCreate 不接受 config_path 参数
TeamCreate(config_path="my-team-config.json")

# 错误！TaskCreate 不接受 task_data 参数
TaskCreate(task_data=task-1.json)
```

### ✅ 正确：使用工具的正式参数

```bash
# 正确
TeamCreate(team_name="my-project", description="项目描述")

TaskCreate(
  subject="任务标题",
  description="详细描述",
  activeForm="正在进行中"
)
```

---

## 最佳实践

1. **先规划后执行**：使用模板文件规划团队结构和任务
2. **复制 Prompt 模板**：从 `role-prompt-template.md` 复制角色 Prompt
3. **替换变量**：确保替换所有 `{variable}` 变量
4. **包含循环防护**：每个角色 Prompt 都应包含循环防护段落
5. **版本控制**：将规划文档纳入版本控制

---

## 相关资源

- [quick-start.md](../quick-start.md) - 快速开始指南
- [role.md](../role.md) - 角色定义详解
- [workflow.md](../workflow.md) - 工作流详解
- [protocol.md](../protocol.md) - 通信协议
- [loop-protection-template.md](./loop-protection-template.md) - 循环防护模板
