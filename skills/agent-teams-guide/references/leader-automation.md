# Leader 自动化逻辑模板

> 本模板帮助 Leader 从"手动路由器"进化为"自动化编排器"，实现自我驱动的任务调度和状态流转。

---

## 一、核心理念

### 从被动到主动

**传统模式（被动）**：
- 等待成员发送完成消息
- 手动更新任务状态
- 手动分配下一个任务
- 手动通知相关人员

**自动化模式（主动）**：
- 响应事件自动触发后续动作
- 状态变更自动流转
- 依赖满足自动唤醒
- 资源紧张自动节流

---

## 二、资源感知初始化

### 2.1 启动前系统健康检查

在创建任何成员之前，必须先验证系统资源：

```python
# 检查许可池状态
permit_status = get_permit_status_tool()

if permit_status["available_permits"] == 0:
    # 内存紧张，进入紧急串行模式
    mode = "emergency_serial"
    print("🚨 内存使用率超过90%，进入紧急串行模式")
elif permit_status["available_permits"] <= 2:
    # 资源受限，减少并发
    mode = "reduced_parallelism"
    print("⚠️ 内存使用率较高，减少并发成员数")
else:
    # 正常模式
    mode = "normal"
    print("✅ 系统资源充足，可以正常创建成员")
```

### 2.2 启动序列

```
Step 1: 检查 Memory Guardian 状态
        get_guardian_status_tool()
        
Step 2: 如果未运行，启动守护进程
        start_guardian_tool()
        
Step 3: 获取许可池状态
        get_permit_status_tool()
        
Step 4: 根据可用许可数决定团队规模
        available_permits = 4 → 创建 3-4 个成员
        available_permits = 3 → 创建 2-3 个成员
        available_permits = 2 → 创建 1-2 个成员
        available_permits = 0 → 等待或提示用户
        
Step 5: 创建团队
        db_create_team_tool(team_name, description)
```

---

## 三、自动化任务流转（Trigger-Action）

### 3.1 事件-动作矩阵

| 事件（Trigger） | 自动化逻辑（Action） | MCP 工具 |
|----------------|---------------------|----------|
| 任务状态变更为 `completed` | 1. 查找依赖此任务的其他任务<br>2. 如果依赖任务已有 owner，自动发送唤醒消息 | `db_get_ready_tasks_tool`<br>`SendMessage` |
| 依赖解除 | 1. 扫描可执行的任务<br>2. 自动分配给空闲成员 | `db_get_ready_tasks_tool`<br>`db_update_task_tool` |
| 成员报告 `idle` | 1. 查找待办且未分配的任务<br>2. 自动分配给该成员 | `db_get_ready_tasks_tool`<br>`db_update_task_tool` |
| 任务创建 | 1. 检查依赖关系<br>2. 如果是独立任务且有空闲成员，立即分配 | `db_create_task_tool`<br>`db_update_task_tool` |
| 测试失败 | 1. 自动创建 Bug 修复任务<br>2. 设置依赖关系<br>3. 分配给 Developer | `db_create_task_tool`<br>`db_add_dependency_tool` |

### 3.2 自动流转配置示例

```python
# 示例：当任务 A 完成时，自动通知任务 B 的负责人
db_create_trigger_tool(
    team_name="my-team",
    trigger_type="on_complete",
    source_task_id="task-a",
    target_task_id="task-b",
    action="notify",
    action_params='{"recipient": "developer-b", "message": "前置任务已完成，请开始你的工作"}'
)

# 示例：当开发任务完成时，自动将测试任务状态改为 ready
db_create_trigger_tool(
    team_name="my-team",
    trigger_type="on_complete",
    source_task_id="dev-task-1",
    target_task_id="test-task-1",
    action="update_status",
    action_params='{"status": "pending", "notify_owner": true}'
)
```

### 3.3 自动分配算法

```python
def auto_assign_task(team_name: str, task_id: str = None):
    """
    自动分配任务给最合适的成员
    """
    # 获取可执行任务
    if task_id:
        # 分配指定任务
        task = db_get_task(task_id)
    else:
        # 获取第一个可执行任务
        ready_tasks = db_get_ready_tasks_tool(team_name=team_name)
        if not ready_tasks["ready_tasks"]:
            return {"status": "no_ready_tasks"}
        task = ready_tasks["ready_tasks"][0]
    
    # 根据任务类型匹配合适的角色
    task_subject = task["subject"].lower()
    
    if "测试" in task_subject or "test" in task_subject:
        preferred_role = "tester"
    elif "审查" in task_subject or "review" in task_subject:
        preferred_role = "reviewer"
    elif "研究" in task_subject or "调研" in task_subject or "research" in task_subject:
        preferred_role = "researcher"
    else:
        preferred_role = "developer"
    
    # 查找空闲的合适成员
    idle_members = get_idle_members(team_name, preferred_role)
    
    if idle_members:
        # 分配给第一个空闲的合适成员
        assigned_member = idle_members[0]
        db_update_task_tool(
            task_id=task["id"],
            owner=assigned_member["name"]
        )
        
        # 发送通知
        SendMessage(
            type="message",
            recipient=assigned_member["name"],
            content=f"任务 #{task['id']} '{task['subject']}' 已自动分配给你。请开始工作。",
            summary=f"自动分配任务#{task['id']}"
        )
        
        return {
            "status": "assigned",
            "task_id": task["id"],
            "member": assigned_member["name"]
        }
    
    # 没有空闲成员，检查是否可以创建新成员
    permit_status = get_permit_status_tool()
    if permit_status["available_permits"] > 0:
        # 创建新成员
        new_member = create_member(team_name, preferred_role)
        db_update_task_tool(
            task_id=task["id"],
            owner=new_member["name"]
        )
        return {
            "status": "created_and_assigned",
            "task_id": task["id"],
            "member": new_member["name"]
        }
    
    return {
        "status": "queued",
        "task_id": task["id"],
        "reason": "no_available_members"
    }
```

---

## 四、通信与成果交付物协议

### 4.1 消息精简规则

为防止 Leader 上下文窗口爆炸，强制执行以下规则：

**禁止行为**：
- ❌ 在 `SendMessage` 中发送超过 500 字的详细报告
- ❌ 发送未经结构化的长文本
- ❌ 重复发送相同信息

**强制行为**：
- ✅ 使用 `create_artifact_tool` 创建详细的成果文件
- ✅ 在 `SendMessage` 中只发送摘要（< 200 字）和文件路径
- ✅ 使用结构化格式：`【动作】任务#X完成。详情见：[文件路径]`

### 4.2 ACK 确认机制

成员接收任务后必须发送轻量级确认：

```python
# 成员收到任务分配后，立即发送 ACK
db_add_task_ack_tool(
    task_id="task-1",
    member_name="developer-1",
    ack_type="understood",  # received/started/understood
    message="理解任务：实现用户登录功能，预计需要2小时"
)
```

ACK 类型说明：
- `received` - 已收到任务通知
- `understood` - 理解任务需求
- `started` - 已开始执行任务

### 4.3 成果文件（Artifacts）规范

**Explore 类型角色**（Researcher、Reviewer）必须使用成果文件：

```python
# Researcher 完成调研后
create_artifact_tool(
    team_name="my-team",
    creator="researcher-1",
    creator_role="researcher",
    artifact_type="research_note",  # research_note/review_report/analysis_result/design_doc
    title="API 设计方案调研报告",
    content="# 调研结果...",  # 详细内容
    visibility="leader_only",  # 保持 Leader 上下文整洁
    summary="REST vs GraphQL 对比分析，推荐 REST",
    tags='["api", "design", "rest", "graphql"]'
)

# 然后发送精简消息
SendMessage(
    type="message",
    recipient="team-lead",
    content="调研任务#1完成。报告已生成：.teams/artifacts/research_note/api_design_research.md",
    summary="调研完成-API设计方案"
)
```

**可见性级别选择**：
- `public` - 所有成员可读（如设计文档）
- `team` - 团队成员可读（如测试报告）
- `leader_only` - 仅 Leader（如详细调研笔记，推荐）
- `private` - 仅创建者（不推荐）

---

## 五、智能错误处理

### 5.1 自适应重试策略

不再使用固定的"2次失败即停止"，而是根据错误类型调整：

```python
# 记录错误并获取处理建议
result = record_error_tool(
    team_name="my-team",
    error_content="npm install 失败：权限不足",
    context="任务#3 - 安装依赖"
)

# 返回示例：
# {
#   "error_type": "bash_execution",
#   "severity": "medium",
#   "max_retries": 4,
#   "can_retry": true,
#   "suggested_action": "retry_with_context",
#   "context_hint": "检查命令语法和环境配置"
# }
```

| 错误类型 | 重试次数 | 处理建议 |
|---------|---------|---------|
| 工具格式错误 | 2 次 | 立即求助 |
| 参数格式错误 | 2 次 | 提供示例后重试 |
| Bash 执行错误 | 4 次 | 尝试替代命令 |
| 业务逻辑错误 | 5 次 | 深度分析后重试 |

### 5.2 冲突检测与死锁预防

```python
# 定期调用诊断工具
diagnose_team_status_tool(team_name="my-team")

# 返回示例：
# {
#   "status": "has_issues",
#   "issues": [
#     "检测到循环依赖: Task#2 -> Task#3 -> Task#2"
#   ]
# }
```

死锁处理流程：
1. **检测到死锁**：使用 `diagnose_team_status_tool`
2. **分析依赖图**：使用 `db_get_ready_tasks_tool` 查看阻塞情况
3. **解除死锁**：删除或修改导致循环的依赖关系
4. **恢复执行**：重新分配任务

---

## 六、自动关闭序列

### 6.1 正常关闭流程

```python
def auto_shutdown_sequence(team_name: str):
    """
    自动关闭团队
    """
    # Step 1: 确认所有任务完成
    ready_tasks = db_get_ready_tasks_tool(team_name=team_name)
    all_tasks = list_all_tasks(team_name)
    
    completed_count = sum(1 for t in all_tasks if t["status"] == "completed")
    total_count = len(all_tasks)
    
    if completed_count < total_count:
        return {
            "status": "incomplete_tasks",
            "message": f"还有 {total_count - completed_count} 个任务未完成"
        }
    
    # Step 2: 广播完成通知
    SendMessage(
        type="broadcast",
        content=f"项目已完成！所有 {total_count} 个任务已通过审查。即将发送关闭请求。",
        summary="项目完成通知"
    )
    
    # Step 3: 逐个发送关闭请求
    members = get_team_members(team_name)
    shutdown_timeout = 120  # 2分钟超时
    
    for member in members:
        SendMessage(
            type="shutdown_request",
            recipient=member["name"],
            content="所有任务完成，感谢你的工作。请批准关闭。",
            summary=f"关闭请求-{member['name']}"
        )
    
    # Step 4: 等待所有响应（实际由系统自动处理）
    # Step 5: 保存最终检查点
    save_team_checkpoint_tool(
        team_name=team_name,
        checkpoint_name="final"
    )
    
    # Step 6: 删除团队
    TeamDelete(team_name=team_name)
    
    return {"status": "success", "message": "团队已正常关闭"}
```

### 6.2 紧急关闭流程

当系统资源严重不足时的紧急处理：

```python
def emergency_shutdown(team_name: str):
    """
    紧急关闭所有成员，不等待任务完成
    """
    # Step 1: 广播紧急通知
    SendMessage(
        type="broadcast",
        content="🚨 系统资源严重不足，需要紧急关闭所有成员。请立即保存工作并响应关闭请求。",
        summary="紧急关闭通知"
    )
    
    # Step 2: 快速关闭（不等响应）
    members = get_team_members(team_name)
    for member in members:
        SendMessage(
            type="shutdown_request",
            recipient=member["name"],
            content="紧急关闭，请立即批准",
            summary=f"紧急关闭-{member['name']}"
        )
    
    # Step 3: 保存检查点（记录未完成状态）
    save_team_checkpoint_tool(
        team_name=team_name,
        checkpoint_name="emergency"
    )
    
    # Step 4: 强制清理
    stop_guardian_tool()
    TeamDelete(team_name=team_name)
```

---

## 七、完整自动化示例

### 7.1 场景：自动化功能开发

```python
# ========== 初始化阶段 ==========

# 1. 启动 Memory Guardian
start_guardian_tool()

# 2. 检查资源
permit_status = get_permit_status_tool()
if permit_status["available_permits"] < 3:
    print("⚠️ 资源不足，将使用串行模式")

# 3. 创建团队
db_create_team_tool(
    team_name="feature-x",
    description="实现功能X"
)

# ========== 任务创建阶段 ==========

# 4. 创建任务
db_create_task_tool(
    task_id="dev-1",
    team_name="feature-x",
    subject="实现核心功能",
    description="...",
    priority=1
)

db_create_task_tool(
    task_id="test-1",
    team_name="feature-x",
    subject="编写单元测试",
    description="...",
    priority=2
)

# 5. 设置依赖
db_add_dependency_tool(
    task_id="test-1",
    depends_on_task_id="dev-1"
)

# 6. 设置自动流转触发器
db_create_trigger_tool(
    team_name="feature-x",
    trigger_type="on_complete",
    source_task_id="dev-1",
    target_task_id="test-1",
    action="notify",
    action_params='{"message": "开发完成，请开始测试"}'
)

# ========== 成员创建阶段 ==========

# 7. 预留资源给开发任务
reserve_permit_tool(
    team_name="feature-x",
    member_name="developer",
    task_type="development",
    duration_minutes=60
)

# 8. 创建成员
Task(
    prompt="...",
    name="developer",
    team_name="feature-x",
    subagent_type="general-purpose",
    run_in_background=True
)

# ========== 自动化执行阶段 ==========

# 9. 分配第一个任务
db_update_task_tool(
    task_id="dev-1",
    owner="developer"
)

SendMessage(
    type="message",
    recipient="developer",
    content="任务#dev-1已分配，请开始工作",
    summary="分配开发任务"
)

# 10. 等待 developer 完成（自动化处理）
# - developer 标记任务完成
# - 触发器自动通知 test-1 的 owner
# - 系统自动分配 test-1 给 tester

# ========== 关闭阶段 ==========

# 11. 项目完成后自动关闭
auto_shutdown_sequence("feature-x")
```

---

## 八、快速参考：自动化工具清单

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

## 九、常见自动化模式

### 模式 1：流水线模式

```
[开发] → [测试] → [审查]
   ↓        ↓        ↓
 完成时   完成时   完成时
 自动分配 自动分配 自动关闭
```

### 模式 2：并行开发模式

```
[前端开发] ──┐
             ├──→ [集成测试] → [审查]
[后端开发] ──┘
   ↓              ↓
 完成时         两者都完成时
 通知测试        自动分配
```

### 模式 3：研究先行模式

```
[研究] → [开发] → [测试]
  ↓       ↓        ↓
产出    基于研究   基于实现
报告    进行开发   进行测试
```

---

## 十、故障排除

### 问题 1：自动流转未触发

**检查点**：
1. 触发器是否正确创建？
   ```python
   # 检查触发器状态
   diagnose_team_status_tool(team_name="my-team")
   ```

2. 任务状态是否正确更新？
   ```python
   # 确保使用 db_update_task_tool 而非手动修改
   db_update_task_tool(task_id="task-1", status="completed")
   ```

3. 依赖关系是否正确设置？
   ```python
   # 检查依赖
   task = db_get_task("task-2")
   print(task["blocked_by"])  # 应显示 ["task-1"]
   ```

### 问题 2：成员未收到自动分配通知

**检查点**：
1. 成员是否正确创建？
2. 任务是否已设置 owner？
3. SendMessage 的 recipient 是否正确？

### 问题 3：资源预留失败

**检查点**：
1. Memory Guardian 是否运行？
   ```python
   get_guardian_status_tool()
   ```

2. 可用许可数是否足够？
   ```python
   permit_status = get_permit_status_tool()
   print(permit_status["available_permits"])
   ```

3. 任务权重是否计算正确？
   - `read_only`: 1
   - `development`: 2
   - `testing`: 2
   - `refactoring`: 3
   - `build`: 3
   - `heavy_analysis`: 3
