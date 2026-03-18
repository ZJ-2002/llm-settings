# 使用示例

本页面提供了 long-running skill 的常见使用场景和最佳实践。

---

## 快速开始

### 场景 1：初始化新项目

**目标**：开始一个新的长期运行项目，确保可以跨会话持久化。

```
用户: 我想开发一个大型电商系统，需要分成多个任务执行

Claude: [使用 MCP 工具初始化项目]
initialize_project(
    project_dir: "/path/to/ecommerce",
    project_name: "电商系统",
    total_tasks: 50
)
```

**输出**：
```
✓ 项目初始化成功
  状态目录: /path/to/ecommerce/.state
  检查点: /path/to/ecommerce/.state/checkpoint.json
  任务队列: /path/to/ecommerce/.state/task-queue.json
  知识库: /path/to/ecommerce/.state/knowledge.json
  预估任务数: 50
```

### 场景 2：查询项目进度

**目标**：随时了解项目当前状态和进度。

```
用户: 项目进展怎么样了？

Claude: [使用 MCP 工具获取状态]
status = get_status(
    project_dir: "/path/to/ecommerce",
    show_tasks: true,
    show_errors: true
)
```

**输出**：
```
{
  "status": "active",
  "progress_percent": 45.5,
  "tasks": {
    "total": 50,
    "completed": 22,
    "pending": 12,
    "in_progress": 1,
    "blocked": 1,
    "failed": 0
  },
  "dependency_health": "valid",
  "summary": "已完成用户模块和订单模块，当前实现支付接口",
  ...
}
```

### 场景 3：启动自动化执行

**目标**：在后台持续执行任务，无需手动干预。

```
用户: 开始执行吧

Claude: [使用 MCP 工具启动守护进程]
result = start_daemon(
    project_dir: "/path/to/ecommerce",
    iterations: 1000,
    max_failures: 3
)
```

**输出**：
```
✓ 后台循环已启动（增强版）
  PID: 12345
  迭代次数: 1000
  最大失败阈值: 3
  日志文件: /path/to/ecommerce/run.log

查看实时日志:
  tail -f /path/to/ecommerce/run.log

停止执行:
  stop_daemon(project_dir="/path/to/ecommerce")
```

### 场景 4：项目中断后恢复

**目标**：处理崩溃、断网、Agent Teams 中断等异常情况。

```
用户: 昨天执行时断网了，项目状态可能有问题

Claude: [使用 MCP 工具执行增强恢复]
result = recover(
    project_dir: "/path/to/ecommerce",
    force: false
)
```

---

## Agent Teams 使用示例

### 场景 5：创建并注册 Agent Team

**目标**：使用 Agent Teams 并行执行复杂任务。

```
用户: 用 Agent Teams 来开发这个后端模块

Claude: [执行完整 Teams 设置流程]

# 1. 确保环境干净
recover(project_dir=".")

# 2. 启动子代理进程
member_pids = [12346, 12347]

# 3. 注册团队
register_team(
    project_dir: ".",
    team_id: "backend-dev-team",
    member_pids: "12346,12347",
    task_id: "task-010"
)

# 4. 启动心跳守护
```

### 场景 6：收割孤儿 Agent Teams

**目标**：Leader 崩溃后清理残留子进程。

```
用户: 检查是否有残留的 Agent Teams

Claude: [检测孤儿团队]
result = reap_orphaned_teams(
    project_dir: ".",
    dry_run: false
)
```

---

## 最佳实践

### 任务定义

每个任务应该足够详细，使新会话无需额外上下文即可执行。

### 频繁提交策略

每完成一个子步骤就提交，不要等到整个任务完成。

### Agent Teams 最佳实践

1. **注册必须成功**：子进程启动后必须成功注册
2. **心跳必启**：每个子代理必须启动心跳守护
3. **任务绑定**：注册时指定 task_id
4. **及时清理**：任务完成后立即清理

---

## 常见问题

### Q: 如何停止正在运行的循环？

**A**: 使用 MCP 工具：
```bash
stop_daemon(project_dir="/path/to/project")
```

### Q: 如何查看执行日志？

**A**: 使用 MCP 工具或直接查看日志文件：
```bash
tail -f /path/to/project/run.log
```

### Q: recover() 检测到循环依赖怎么办？

**A**: 
1. 查看 `recover()` 输出中的循环路径
2. 编辑 `.state/task-queue.json`，修复依赖关系
3. 重新运行 `recover()`
