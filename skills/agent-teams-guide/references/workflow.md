# 工作流模板与示例

> 本文档提供常见项目类型的完整工作流模板，可直接套用。

---

## 一、标准三人组工作流（开发+测试+审查）

适用场景：功能开发、Bug 修复、小型重构

### 完整 Leader 操作序列

```
=== 第一步：创建团队 ===
TeamCreate(team_name="feature-x", description="实现功能X")

=== 第二步：创建任务并设置依赖 ===
TaskCreate(
  subject="实现功能X的核心代码",
  description="详细需求...",
  activeForm="正在实现功能X"
)  → 得到 Task#1

TaskCreate(
  subject="为功能X编写单元测试",
  description="覆盖以下场景：正常流程、边界条件、错误处理...",
  activeForm="正在编写功能X的测试"
)  → 得到 Task#2

TaskCreate(
  subject="审查功能X的代码和测试",
  description="审查范围：代码质量、安全性、测试覆盖度...",
  activeForm="正在审查功能X"
)  → 得到 Task#3

// 设置依赖链：开发 → 测试 → 审查
TaskUpdate(taskId="2", addBlockedBy=["1"])
TaskUpdate(taskId="3", addBlockedBy=["2"])

=== 第三步：生成成员（并行生成） ===
// 在一条消息中同时调用多个 Task 工具
Task(
  prompt="[粘贴 role.md 中 Developer 的 Prompt 模板]",
  subagent_type="general-purpose",
  description="生成开发者",
  team_name="feature-x",
  name="developer",
  run_in_background=true
)

Task(
  prompt="[粘贴 role.md 中 Tester 的 Prompt 模板]",
  subagent_type="general-purpose",
  description="生成测试员",
  team_name="feature-x",
  name="tester",
  run_in_background=true
)

Task(
  prompt="[粘贴 role.md 中 Reviewer 的 Prompt 模板]",
  subagent_type="Explore",
  description="生成审查员",
  team_name="feature-x",
  name="reviewer",
  run_in_background=true
)

=== 第四步：分配第一批任务 ===
TaskUpdate(taskId="1", owner="developer")
SendMessage(
  type="message",
  recipient="developer",
  content="任务#1已分配给你。请用 TaskGet(taskId='1') 查看需求详情。完成后通知我。",
  summary="分配开发任务#1"
)
// 注意：Task#2 和 Task#3 被 blockedBy 阻塞，暂不分配

=== 第五步：等待 developer 完成 ===
// 不要轮询！等待 developer 的 SendMessage 通知

=== 第六步：收到 developer 完成通知后 ===
TaskUpdate(taskId="2", owner="tester")
SendMessage(
  type="message",
  recipient="tester",
  content="开发已完成。任务#2已分配给你。请用 TaskGet(taskId='2') 查看测试需求。developer 修改了以下文件：[从 developer 的通知中复制文件列表]",
  summary="分配测试任务#2"
)

=== 第七步：等待 tester 完成 ===

=== 第八步A：如果测试通过 ===
TaskUpdate(taskId="3", owner="reviewer")
SendMessage(
  type="message",
  recipient="reviewer",
  content="开发和测试已完成。任务#3已分配给你。请审查以下文件：[文件列表]",
  summary="分配审查任务#3"
)

=== 第八步B：如果测试失败 ===
TaskCreate(
  subject="修复测试发现的Bug",
  description="[从 tester 通知中复制的失败详情]",
  activeForm="正在修复Bug"
)  → 得到 Task#4
TaskUpdate(taskId="2", status="pending")  // 重置测试任务为待办
TaskUpdate(taskId="2", addBlockedBy=["4"])  // 测试任务依赖Bug修复
TaskUpdate(taskId="4", owner="developer")
SendMessage(
  type="message",
  recipient="developer",
  content="测试发现Bug，请修复。详情见 TaskGet(taskId='4')。",
  summary="分配Bug修复任务"
)
// 回到第五步，等待 developer

=== 第九步：收到审查结果 ===
// 如果审查通过 → 进入关闭流程
// 如果需要修改 → 创建修改任务，分配给 developer，循环

=== 第十步：关闭团队 ===
SendMessage(type="shutdown_request", recipient="developer", content="项目完成")
SendMessage(type="shutdown_request", recipient="tester", content="项目完成")
SendMessage(type="shutdown_request", recipient="reviewer", content="项目完成")
// 等待所有 shutdown_response
TeamDelete()
```

---

## 二、研究先行工作流

适用场景：复杂功能、不熟悉的代码库、技术调研

### Leader 操作序列

```
=== 第一阶段：研究 ===
TeamCreate(team_name="complex-feature", description="...")

TaskCreate(
  subject="分析现有代码架构和相关模块",
  description="探索 src/ 目录，找出与X功能相关的所有文件。分析现有的架构模式、数据流、依赖关系。输出：关键文件列表、架构图、技术约束。",
  activeForm="正在分析代码架构"
)  → Task#1

// 只生成研究员
Task(
  prompt="[Researcher Prompt]",
  subagent_type="Explore",
  name="researcher",
  team_name="complex-feature",
  run_in_background=true
)

TaskUpdate(taskId="1", owner="researcher")
SendMessage(type="message", recipient="researcher", content="请开始分析...", summary="启动代码分析")

// 等待研究结果...

=== 第二阶段：基于研究结果创建开发任务 ===
// 收到 researcher 的结果后
// 根据研究发现创建具体的开发、测试、审查任务
// 设置依赖关系
// 生成 developer, tester, reviewer
// 后续同标准三人组工作流

=== 关闭 researcher ===
// 研究完成后，researcher 没有更多任务
SendMessage(type="shutdown_request", recipient="researcher", content="研究阶段完成")
```

---

## 三、并行开发工作流

适用场景：前后端并行开发、多模块并行

### Leader 操作序列

```
TeamCreate(team_name="fullstack-feature", description="...")

// 创建可并行的任务
TaskCreate(subject="实现前端页面", ...) → Task#1
TaskCreate(subject="实现后端API", ...) → Task#2
TaskCreate(subject="集成测试", ...) → Task#3
TaskCreate(subject="代码审查", ...) → Task#4

// 设置依赖：集成测试依赖前端+后端都完成
TaskUpdate(taskId="3", addBlockedBy=["1", "2"])
TaskUpdate(taskId="4", addBlockedBy=["3"])

// 生成两个开发者（并行）
Task(prompt="[Developer-Frontend Prompt]", subagent_type="general-purpose",
     name="dev-frontend", team_name="fullstack-feature", run_in_background=true)
Task(prompt="[Developer-Backend Prompt]", subagent_type="general-purpose",
     name="dev-backend", team_name="fullstack-feature", run_in_background=true)
Task(prompt="[Tester Prompt]", subagent_type="general-purpose",
     name="tester", team_name="fullstack-feature", run_in_background=true)

// 并行分配
TaskUpdate(taskId="1", owner="dev-frontend")
TaskUpdate(taskId="2", owner="dev-backend")
SendMessage(type="message", recipient="dev-frontend", content="请开始任务#1...", summary="分配前端任务")
SendMessage(type="message", recipient="dev-backend", content="请开始任务#2...", summary="分配后端任务")

// 等待两者都完成后再分配测试任务
// 收到 dev-frontend 完成通知 → 记录，等待 dev-backend
// 收到 dev-backend 完成通知 → 两者都完成，分配测试
TaskUpdate(taskId="3", owner="tester")
SendMessage(type="message", recipient="tester", content="前后端都已完成...", summary="分配集成测试")
```

---

## 四、讨论/评审工作流

适用场景：方案评审、技术讨论（用户要求 "让他们开会讨论"）

### Leader 操作序列

```
TeamCreate(team_name="design-review", description="技术方案评审")

// 阶段1：每人独立准备意见
TaskCreate(subject="从开发角度评估方案可行性", ...) → Task#1
TaskCreate(subject="从测试角度评估方案可测试性", ...) → Task#2
TaskCreate(subject="从安全角度评估方案安全性", ...) → Task#3
TaskCreate(subject="汇总所有意见并形成结论", ...) → Task#4
TaskUpdate(taskId="4", addBlockedBy=["1", "2", "3"])

// 生成角色
Task(prompt="...", name="dev-advisor", subagent_type="Explore", ...)
Task(prompt="...", name="test-advisor", subagent_type="Explore", ...)
Task(prompt="...", name="security-advisor", subagent_type="Explore", ...)

// 并行分配
TaskUpdate(taskId="1", owner="dev-advisor")
TaskUpdate(taskId="2", owner="test-advisor")
TaskUpdate(taskId="3", owner="security-advisor")
SendMessage(type="message", recipient="dev-advisor", content="请评估方案的开发可行性...", summary="请求开发评估")
SendMessage(type="message", recipient="test-advisor", content="请评估方案的可测试性...", summary="请求测试评估")
SendMessage(type="message", recipient="security-advisor", content="请评估方案的安全性...", summary="请求安全评估")

// 等待三方都完成
// 收集所有意见后，Leader 汇总形成结论
// 或者将汇总任务分配给一个成员
```

**关键：不要让成员直接互相 "开会"**。正确的模式是：
1. 每人独立完成自己的评估任务
2. Leader 收集所有结果
3. Leader 汇总或分配汇总任务
4. 如果需要第二轮讨论，基于第一轮结果创建新任务

---

## 五、迭代修复工作流

适用场景：CI 失败修复、代码审查修改、反复调试

### Leader 操作序列

```
// 在 Bug 修复循环中

第1轮：
  TaskCreate(subject="修复登录功能Bug", description="错误详情...", ...)  → Task#N
  TaskCreate(subject="验证登录Bug修复", description="...", ...)  → Task#N+1
  TaskUpdate(taskId="N+1", addBlockedBy=["N"])

  分配 Task#N → developer
  等待完成 → 分配 Task#N+1 → tester

如果 tester 报告仍有问题：
第2轮：
  TaskCreate(
    subject="修复登录Bug（第2轮）",
    description="第1轮修复后仍有问题：[tester的反馈]。之前修改的文件：[文件列表]。请基于tester的反馈进行修复。",
    ...
  )  → Task#N+2
  TaskCreate(subject="验证登录Bug修复（第2轮）", ...)  → Task#N+3
  TaskUpdate(taskId="N+3", addBlockedBy=["N+2"])

  分配 Task#N+2 → developer
  ...

如果第3轮仍然失败：
  重新评估方案，可能需要 researcher 介入分析根因
```

---

## 六、Teammate Prompt 模板汇总

在生成 Teammate 时，prompt 参数中必须包含以下内容：

### 通用模板结构

```
你是团队 "{team_name}" 中的{角色名}（{english_name}）。

## 你的职责
{一句话描述职责}

## 工作流程（严格按此顺序执行）

### 步骤 1：查找任务
1. 调用 TaskList() 查看可用任务
2. 如果任务列表为空，使用 SendMessage 通知 team-lead 并等待新任务分配
3. 不要在没有有效任务的情况下继续

### 步骤 2：获取任务详情
4. 调用 TaskGet(taskId) 读取任务详情
5. 确认 taskId 是有效的字符串（不是空值、不是 "null"、不是 "undefined"）

### 步骤 3：检查依赖
6. 检查任务的 blockedBy 列表
7. 如果有未完成的前置任务，通知 team-lead 并等待

### 步骤 4：标记开始
8. 调用 TaskUpdate(taskId="X", status="in_progress")
9. 确保 taskId 参数正确使用双引号包裹

### 步骤 5：执行工作
10. 执行你的工作
11. 如果遇到无法解决的错误，通知 team-lead 并保持任务状态为 in_progress

### 步骤 6：标记完成
12. 调用 TaskUpdate(taskId="X", status="completed")
13. 只有在真正完成任务后才标记为 completed

### 步骤 7：通知 Leader
14. 调用 SendMessage(type="message", recipient="team-lead", content="任务#X完成。", summary="任务完成通知")

### 步骤 8：循环或等待
15. 调用 TaskList() 查找下一个可用任务
16. 如果有任务，重复步骤 2-7
17. 如果没有任务，等待 team-lead 的消息

## 循环防护（重要）
- 如果发现自己多次输出相同的错误信息，立即停止并通知 team-lead
- 如果 TaskUpdate 调用失败，不要无限重试，通知 team-lead 求助
- 如果 TaskGet 返回错误或空值，不要继续执行，通知 team-lead
- 最多尝试 3 次相同操作，失败后必须求助

## 工具调用格式（必须严格遵守）
- TaskUpdate: {"taskId": "数字", "status": "in_progress|completed|pending"}
- TaskGet: TaskGet(taskId="数字")
- TaskList: TaskList()
- SendMessage: {"type": "message", "recipient": "team-lead", "content": "...", "summary": "..."}

## 沟通规则
- 完成任务后必须用 SendMessage(type="message") 通知 team-lead
- 遇到问题必须用 SendMessage(type="message") 向 team-lead 求助
- 不要使用 broadcast（除非 team-lead 明确要求）
- 收到 shutdown_request 时，用 SendMessage(type="shutdown_response", request_id="...", approve=true) 回复

## 禁止事项
- 不要在没有有效任务的情况下行动
- 不要使用无效的 taskId（空值、null、undefined）
- 不要跳过 TaskUpdate 状态更新
- 不要忘记通知 team-lead
- 不要陷入自我修正循环（如果连续 3 次出现相同错误，立即求助）
- 不要输出 "<parameter=" 这样的无效格式
- 工具调用必须使用正确的 JSON 格式
```

---

## 七、项目规模与角色数量指南

| 项目规模 | 推荐角色数 | 角色组合 |
|----------|-----------|----------|
| 微型（1个文件修改） | 不使用团队 | 直接由 Leader 完成 |
| 小型（2-3个文件） | 2人 | developer + tester |
| 中型（4-10个文件） | 3人 | developer + tester + reviewer |
| 大型（10+个文件） | 4-5人 | researcher + developer(s) + tester + reviewer |
| 多模块并行 | 按模块 | 每模块一个 developer + 共享 tester + reviewer |

**原则**：角色越少越好。每增加一个角色都会增加通信开销。

---

## 八、自动化工作流示例

### 8.1 使用 Trigger 的流水线模式

```python
# ========== 初始化阶段 ==========

# 1. 检查资源并创建团队
get_permit_status_tool()
db_create_team_tool(team_name="pipeline-demo", description="自动化流水线演示")

# 2. 创建任务链
db_create_task_tool(
    task_id="dev-task",
    team_name="pipeline-demo",
    subject="实现核心功能",
    description="实现用户认证功能...",
    priority=1
)

db_create_task_tool(
    task_id="test-task",
    team_name="pipeline-demo",
    subject="编写并执行测试",
    description="覆盖正常流程、边界条件...",
    priority=2
)

db_create_task_tool(
    task_id="review-task",
    team_name="pipeline-demo",
    subject="代码审查",
    description="审查代码质量和安全性...",
    priority=3
)

# 3. 设置依赖
db_add_dependency_tool(task_id="test-task", depends_on_task_id="dev-task")
db_add_dependency_tool(task_id="review-task", depends_on_task_id="test-task")

# 4. 设置自动流转触发器

# 开发完成 → 自动通知测试人员
db_create_trigger_tool(
    team_name="pipeline-demo",
    trigger_type="on_complete",
    source_task_id="dev-task",
    target_task_id="test-task",
    action="notify",
    action_params='{"recipient": "tester", "message": "开发已完成，请开始测试"}'
)

# 测试完成 → 自动通知审查人员
db_create_trigger_tool(
    team_name="pipeline-demo",
    trigger_type="on_complete",
    source_task_id="test-task",
    target_task_id="review-task",
    action="notify",
    action_params='{"recipient": "reviewer", "message": "测试通过，请开始代码审查"}'
)

# 审查完成 → 自动标记项目完成
db_create_trigger_tool(
    team_name="pipeline-demo",
    trigger_type="on_complete",
    source_task_id="review-task",
    action="notify",
    action_params='{"recipient": "team-lead", "message": "所有任务已完成"}'
)

# 5. 创建成员并分配第一个任务
Task(prompt="...", name="developer", team_name="pipeline-demo", ...)
db_update_task_tool(task_id="dev-task", owner="developer")

# 后续流程自动执行：
# - developer 完成 → 自动通知 tester
# - tester 完成 → 自动通知 reviewer
# - reviewer 完成 → 自动通知 team-lead
```

### 8.2 使用 ACK 的任务分配流程

```python
# 分配任务时启用 ACK 确认

# 1. 分配任务
db_update_task_tool(task_id="task-1", owner="developer")

# 2. 发送任务通知
SendMessage(
    type="message",
    recipient="developer",
    content="任务#1已分配，请确认接收。",
    summary="分配任务#1"
)

# 3. 等待 developer 发送 ACK
db_add_task_ack_tool(
    task_id="task-1",
    member_name="developer",
    ack_type="understood",
    message="理解任务：预计2小时完成"
)

# 4. Leader 确认 ACK 后继续
# 如果长时间未收到 ACK，可以发送提醒
```

### 8.3 使用 Artifacts 的研究流程

```python
# 研究员使用 Artifacts 产出详细报告

# 1. 创建研究任务
db_create_task_tool(
    task_id="research-1",
    team_name="my-team",
    subject="分析现有代码架构",
    description="探索 src/ 目录，分析架构模式...",
    priority=1
)

# 2. 创建 Researcher
Task(prompt="...", name="researcher", team_name="my-team", subagent_type="Explore", ...)
db_update_task_tool(task_id="research-1", owner="researcher")

# 3. Researcher 完成调研后，创建详细报告
create_artifact_tool(
    team_name="my-team",
    creator="researcher",
    creator_role="researcher",
    artifact_type="research_note",
    title="代码架构分析报告",
    content="""
# 代码架构分析

## 整体架构
项目采用分层架构：
- Controller 层：处理 HTTP 请求
- Service 层：业务逻辑
- Repository 层：数据访问

## 关键文件
- src/controllers/auth.ts: 认证控制器
- src/services/user.ts: 用户服务
- src/repositories/user.ts: 用户数据访问

## 技术约束
1. 使用 TypeScript 4.9
2. 数据库使用 PostgreSQL
3. 缓存使用 Redis

## 建议
基于当前架构，建议新功能按以下方式实现：
...
""",
    visibility="leader_only",
    summary="分层架构分析，关键文件已识别",
    tags='["architecture", "analysis", "typescript"]'
)

# 4. 发送精简消息通知 Leader
SendMessage(
    type="message",
    recipient="team-lead",
    content="调研任务#research-1完成。详细报告：artifacts/my-team/research_note/code_architecture_analysis.md",
    summary="架构调研完成"
)

# 5. Leader 读取报告后创建开发任务
artifact = get_artifact_tool(artifact_id="...")
# 基于报告内容创建具体的开发任务
```

### 8.4 错误处理和恢复流程

```python
# 使用自适应循环检测处理错误

# 成员遇到错误时：
result = record_error_tool(
    team_name="my-team",
    error_content="npm install 失败：权限不足",
    context="任务#3 - 安装依赖"
)

# 根据建议处理
if result["can_retry"]:
    print(f"可以重试，还剩 {result['max_retries'] - result['retry_count']} 次机会")
    print(f"建议：{result['context_hint']}")
    # 尝试修复后重试
else:
    print("无法自动修复，向 Leader 报告")
    SendMessage(
        type="message",
        recipient="team-lead",
        content=f"任务失败：{result['error_type']}，已尝试 {result['retry_count']} 次",
        summary="任务失败需协助"
    )
```

### 8.5 带权重的资源管理流程

```python
# 为不同类型的任务预留资源

# 场景1：创建轻量级 Researcher
reserve_permit_tool(
    team_name="my-team",
    member_name="researcher",
    task_type="read_only",  # 权重 1
    duration_minutes=30
)

# 场景2：创建 Developer
reserve_permit_tool(
    team_name="my-team",
    member_name="developer",
    task_type="development",  # 权重 2
    duration_minutes=60
)

# 场景3：创建执行重构的 Developer
reserve_permit_tool(
    team_name="my-team",
    member_name="refactorer",
    task_type="refactoring",  # 权重 3
    duration_minutes=90
)

# 检查资源使用
status = get_permit_status_tool()
print(f"可用权重: {status['available_weight']}")
print(f"可用许可: {status['available_permits']}")
```

### 8.6 完整的自动化项目启动

```python
# 完整的自动化启动流程

def auto_start_project(project_name: str, tasks: list):
    """
    自动化启动项目
    """
    # 1. 检查资源
    permit_status = get_permit_status_tool()
    if permit_status["available_permits"] == 0:
        return {"status": "error", "message": "资源不足，无法创建团队"}
    
    # 2. 创建团队
    db_create_team_tool(
        team_name=project_name,
        description=f"自动创建的项目: {project_name}"
    )
    
    # 3. 创建任务并设置依赖
    prev_task_id = None
    for i, task_info in enumerate(tasks):
        task_id = f"task-{i+1}"
        db_create_task_tool(
            task_id=task_id,
            team_name=project_name,
            subject=task_info["subject"],
            description=task_info["description"],
            priority=task_info.get("priority", 5)
        )
        
        # 设置依赖（链式依赖）
        if prev_task_id:
            db_add_dependency_tool(
                task_id=task_id,
                depends_on_task_id=prev_task_id
            )
            
            # 设置自动流转
            db_create_trigger_tool(
                team_name=project_name,
                trigger_type="on_complete",
                source_task_id=prev_task_id,
                target_task_id=task_id,
                action="notify",
                action_params=f'{{"message": "前置任务完成，请开始: {task_info["subject"]}"}}'
            )
        
        prev_task_id = task_id
    
    # 4. 创建第一个成员并分配任务
    Task(
        prompt="...",
        name="developer",
        team_name=project_name,
        subagent_type="general-purpose",
        run_in_background=True
    )
    db_update_task_tool(task_id="task-1", owner="developer")
    
    # 5. 保存初始检查点
    save_team_checkpoint_tool(
        team_name=project_name,
        checkpoint_name="initial"
    )
    
    return {
        "status": "success",
        "team_name": project_name,
        "task_count": len(tasks),
        "message": "项目已自动启动，第一个任务已分配给 developer"
    }

# 使用示例
tasks = [
    {"subject": "实现登录功能", "description": "...", "priority": 1},
    {"subject": "编写测试", "description": "...", "priority": 2},
    {"subject": "代码审查", "description": "...", "priority": 3}
]
result = auto_start_project("login-feature", tasks)
```

---

## 九、自动化工具速查表

| 工具 | 用途 | 调用时机 |
|------|------|---------|
| `db_create_trigger_tool` | 设置自动流转 | 创建任务后 |
| `db_get_ready_tasks_tool` | 获取可执行任务 | 成员空闲时 |
| `db_add_task_ack_tool` | 添加 ACK 确认 | 成员接收任务后 |
| `create_artifact_tool` | 创建成果文件 | Explore 角色产出报告时 |
| `reserve_permit_tool` | 预留资源 | 创建高内存消耗成员前 |
| `record_error_tool` | 记录错误并获取建议 | 成员遇到错误时 |
| `analyze_loop_patterns_tool` | 分析循环模式 | 怀疑成员陷入循环时 |
| `diagnose_team_status_tool` | 诊断团队状态 | 定期检查或发现问题时 |
| `save_team_checkpoint_tool` | 保存检查点 | 重要里程碑或关闭前 |

---

## 十、自动化模式总结

### 模式 1：流水线模式
```
[任务A] → [任务B] → [任务C]
   ↓        ↓        ↓
 完成时   完成时   完成时
 自动触发 自动触发 自动通知
```

### 模式 2：并行合并模式
```
[任务A] ──┐
          ├──→ [任务C]
[任务B] ──┘
   ↓
 两者都完成时触发任务C
```

### 模式 3：条件分支模式
```
[测试任务]
    ↓
 通过? → [审查任务]
 失败? → [修复任务] → [测试任务]
```

### 模式 4：研究先行模式
```
[研究] → [开发] → [测试]
  ↓       ↓        ↓
Artifact 基于研究 基于实现
产出    进行开发  进行测试
```
