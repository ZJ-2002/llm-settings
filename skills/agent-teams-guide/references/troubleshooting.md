# Agent Teams 调试与诊断指南

> 本文档提供 Agent Teams 运行过程中的问题排查方法和诊断技巧。

---

## 一、快速诊断检查清单

### 1.1 团队运行状态检查

**使用 Bash 命令快速检查**：

```bash
# 检查团队配置文件是否存在
ls -la ~/.claude/teams/

# 检查任务列表
ls -la ~/.claude/tasks/

# 检查当前项目的 .state 目录
ls -la .state/
```

**预期输出**：
- 团队存在时：`~/.claude/teams/{team-name}/config.json` 应该存在
- `~/.claude/tasks/{team-name}/` 目录应该包含任务文件
- `~/.claude/teams/{team-name}/.state/session-log.md` 应该记录所有会话

---

### 1.2 成员存活状态检查

**检查成员是否还活着**：

```bash
# 查看团队配置中的成员列表
cat ~/.claude/teams/{team-name}/config.json | grep -A 20 "members"
```

**判断标准**：
| 现象 | 原因 | 解决方案 |
|--------|------|---------|
| 没有任何成员 | 团队未创建或已删除 | 重新创建团队 |
| 成员列表完整但无响应 | 成员可能已退出 | 发送测试消息检查 |
| 部分成员消失 | 部分成员异常退出 | 检查错误日志重新创建 |

---

### 1.3 任务状态一致性检查

**检查任务状态是否合理**：

```python
#!/usr/bin/env python3
import json
import sys

# 读取任务列表
with open('.state/task-queue.json') as f:
    data = json.load(f)

# 统计任务状态
status_counts = {}
for task in data['tasks']:
    status = task.get('status', 'unknown')
    status = status_counts.setdefault(status, 0) + 1

# 检查异常状态
issues = []

# 检查 1：是否有 in_progress 任务
if status_counts.get('in_progress', 0) > 0:
    issues.append(f"⚠️ {status_counts['in_progress']} 个任务处于 in_progress 状态")

# 检查 2：检查依赖关系
for task in data['tasks']:
    if task.get('status') == 'pending':
        # 计算实际阻塞数
        blocked_by = sum(1 for dep in task.get('depends_on', [])
                        if any(t.get('id') == dep and t.get('status') != 'completed'
                               for t in data['tasks']))
        if blocked_by > 0 and task.get('status') != 'blocked':
            issues.append(f"⚠️ 任务 {task['id']} 依赖未满足但状态为 pending")

# 检查 3：检查循环依赖
# （此处省略循环检测代码）

# 输出结果
print("任务状态统计:")
for status, count in sorted(status_counts.items()):
    print(f"  {status}: {count}")

if issues:
    print("\n发现的问题:")
    for issue in issues:
        print(issue)
else:
    print("\n✓ 任务状态正常")
```

---

## 二、成员卡住问题排查

### 2.1 诊断流程

```
成员卡住
  │
  ├─ 步骤 1：确认卡住类型
  │   ├─ 无任何响应 → 可能已崩溃
  │   ├─ 空闲但无任务 → 任务分配问题
  │   └─ 一直 in_progress → 任务执行卡住
  │
  ├─ 步骤 2：查看最后消息
  │   └─ 读取 session-log.md 或 idle 通知
  │
  ├─ 步骤 3：检查任务详情
  │   └─ 用 TaskGet 查看卡住任务描述
  │
  └─ 步骤 4：采取行动
      ├─ 重新分配任务
      ├─ 创建新任务替代
      └─ 必要时重启成员
```

### 2.2 具体场景与解决方案

**场景 A：成员沉默无响应**

```bash
# 检查成员进程
ps aux | grep -i claude

# 检查日志
tail -50 ~/.claude/teams/{team-name}/.state/session-log.md

# 检查是否收到过 idle 通知
grep -i "idle" ~/.claude/teams/{team-name}/.state/session-log.md | tail -10
```

**解决方案**：
1. 发送测试消息：`SendMessage(type="message", recipient="member-name", content="ping", summary="测试连接")`
2. 如果仍无响应，用 `TaskStop` 终止成员
3. 重新生成成员并分配原任务

---

**场景 B：任务一直 in_progress**

```python
# 检查任务时间
import json
import datetime

with open('.state/task-queue.json') as f:
    data = json.load(f)

now = datetime.datetime.now()
for task in data['tasks']:
    if task.get('status') == 'in_progress':
        updated = datetime.datetime.fromisoformat(task.get('updated_at', ''))
        duration = (now - updated).total_seconds() / 60  # 分钟
        print(f"任务 {task['id']} 已运行 {duration:.1f} 分钟")
        if duration > 30:  # 超过 30 分钟
            print(f"  ⚠️ 可能卡住")
```

**解决方案**：
1. 查看任务描述，确认是否需要长时间运行
2. 如果异常长时间（> 1 小时），标记任务为 pending
3. 创建新任务，描述中明确需要简化

---

**场景 C：成员一直 idle 但有可用任务**

```bash
# 检查任务列表
cat .state/task-queue.json | grep -A 5 '"status": "pending"'

# 检查 blockedBy 字段
cat .state/task-queue.json | grep -A 10 '"blockedBy"'
```

**原因排查**：
| 现象 | 原因 | 解决 |
|--------|------|------|
| pending 任务有 blockedBy | 依赖未满足 | 检查前置任务是否完成 |
| 任务有 owner | 已被分配但未开始 | 检查对应成员状态 |
| 任务无 owner | 无人认领 | 手动分配给 idle 成员 |

---

## 三、通信问题排查

### 3.1 消息未送达

**检查消息发送历史**：

```bash
# 查看 team-lead 发送的消息
grep -i "发送给" ~/.claude/teams/{team-name}/.state/session-log.md

# 查看成员发送的消息
grep -i "完成\|完成" ~/.claude/teams/{team-name}/.state/session-log.md
```

**常见原因**：
1. **Recipient 名称错误**：使用了 agentId 而非 name
2. **类型错误**：使用了错误的 message type
3. **参数缺失**：缺少必需的参数

**调试方法**：

```python
# 验证 recipient 名称
import json

team_config = json.load(open('~/.claude/teams/{team-name}/config.json'))
member_names = [m['name'] for m in team_config['members']]
print(f"可用成员: {member_names}")

# 检查你的目标名称是否在其中
target_name = "developer"  # 替换为你的目标
if target_name not in member_names:
    print(f"❌ 成员 '{target_name}' 不存在")
else:
    print(f"✓ 成员 '{target_name}' 存在")
```

### 3.2 广播消息未收到

**诊断**：

```
广播未收到
  │
  ├─ 检查 1：确认使用了 broadcast 类型
  ├─ 检查 2：确认至少有一个成员存活
  ├─ 检查 3：查看成员的 idle 通知
  │         （idle 通知会显示成员收到的 DM 摘要）
  └─ 检查 4：查看日志中的错误
```

---

## 四、任务依赖问题排查

### 4.1 循环依赖检测

```python
#!/usr/bin/env python3
import json
from collections import defaultdict, deque

def detect_circular_dependencies(tasks):
    """检测循环依赖"""
    # 构建依赖图
    graph = defaultdict(list)
    for task in tasks:
        task_id = task['id']
        for dep in task.get('depends_on', []):
            graph[dep].append(task_id)

    # 检测循环
    visited = set()
    rec_stack = set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph[node]:
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for task in tasks:
        if task['id'] not in visited:
            if dfs(task['id']):
                return True

    return False

# 使用
with open('.state/task-queue.json') as f:
    data = json.load(f)

if detect_circular_dependencies(data['tasks']):
    print("❌ 检测到循环依赖！")
else:
    print("✓ 无循环依赖")
```

### 4.2 依赖未满足但任务未阻塞

```python
# 检查依赖状态
with open('.state/task-queue.json') as f:
    data = json.load(f)

task_map = {t['id']: t for t in data['tasks']}

issues = []
for task in data['tasks']:
    if task['status'] == 'pending':
        for dep_id in task.get('depends_on', []):
            if dep_id in task_map:
                dep_task = task_map[dep_id]
                if dep_task['status'] != 'completed':
                    issues.append(f"⚠️ 任务 {task['id']} 依赖 {dep_id} 未完成")

for issue in issues:
    print(issue)
```

---

## 五、资源泄漏排查

### 5.1 检查后台进程

```bash
# 查找所有 Claude Code 相关进程
ps aux | grep -E "claude|anthropic" | grep -v grep

# 统计进程数
ps aux | grep -E "claude|anthropic" | grep -v grep | wc -l
```

**异常情况**：
- 进程数超过预期：可能有未清理的后台进程
- CPU 使用率持续 100%：成员陷入死循环
- 内存持续增长：内存泄漏

### 5.2 检查临时文件

```bash
# 查找 .tmp 文件
find . -name "*.tmp" -type f

# 查找 .bak 文件
find . -name "*.bak" -type f

# 查找锁文件
find . -name "*.lock" -type f
```

**清理命令**（谨慎使用）：

```bash
# 清理超过 1 天的临时文件
find . -name "*.tmp" -type f -mtime +1 -delete

# 清理超过 7 天的备份文件
find . -name "*.bak" -type f -mtime +7 -delete
```

---

## 六、性能问题诊断

### 6.1 API 调用次数统计

```bash
# 从日志中统计 SendMessage 次数
grep -c "SendMessage" ~/.claude/teams/{team-name}/.state/session-log.md

# 统计 TaskUpdate 次数
grep -c "TaskUpdate" ~/.claude/teams/{team-name}/.state/session-log.md
```

### 6.2 消息延迟分析

```python
# 分析消息发送和响应的延迟
import re
from datetime import datetime

with open('~/.claude/teams/{team-name}/.state/session-log.md') as f:
    log = f.read()

# 提取所有时间戳和消息
pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
timestamps = re.findall(pattern, log)

if len(timestamps) >= 2:
    delays = []
    for i in range(1, len(timestamps)):
        t1 = datetime.strptime(timestamps[i-1], '%Y-%m-%d %H:%M:%S')
        t2 = datetime.strptime(timestamps[i], '%Y-%m-%d %H:%M:%S')
        delays.append((t2 - t1).total_seconds())

    avg_delay = sum(delays) / len(delays)
    max_delay = max(delays)
    print(f"平均延迟: {avg_delay:.1f}秒")
    print(f"最大延迟: {max_delay:.1f}秒")
```

---

## 七、常见错误代码

| 错误 | 含义 | 解决方案 |
|------|--------|---------|
| `team_not_found` | 团队不存在或已删除 | 检查 team_name 参数，重新创建团队 |
| `member_not_found` | 成员不存在 | 检查 recipient/name 参数，重新生成成员 |
| `task_not_found` | 任务 ID 不存在 | 检查 taskId 参数，用 TaskList 获取正确 ID |
| `permission_denied` | 文件权限不足 | 检查文件权限，确保 agent 有读写权限 |
| `timeout` | 操作超时 | 检查网络，重试或使用更长的超时时间 |
| `invalid_dependency` | 依赖关系错误 | 检查 blockedBy/addBlockedBy 参数 |

---

## 八、完整错误代码表

### 8.1 团队相关错误

| 错误代码 | 含义 | 触发场景 | 解决方案 |
|----------|------|----------|----------|
| `team_not_found` | 团队不存在 | TeamCreate 未调用或已删除 | 重新创建团队 |
| `team_already_exists` | 团队已存在 | 重复调用 TeamCreate | 检查团队名称，使用不同名称 |
| `team_config_invalid` | 团队配置无效 | config.json 格式错误 | 检查 JSON 格式，修复语法错误 |
| `team_locked` | 团队被锁定 | 另一个进程正在使用 | 等待或强制解锁 |

### 8.2 成员相关错误

| 错误代码 | 含义 | 触发场景 | 解决方案 |
|----------|------|----------|----------|
| `member_not_found` | 成员不存在 | recipient 参数错误 | 检查成员名称，使用 TaskList 获取 |
| `member_busy` | 成员忙碌 | 分配任务给正在工作的成员 | 等待成员完成当前任务 |
| `member_timeout` | 成员超时 | 成员长时间无响应 | 发送测试消息，检查日志 |
| `member_generation_failed` | 成员生成失败 | Task 工具调用失败 | 检查 prompt 参数，重试 |

### 8.3 任务相关错误

| 错误代码 | 含义 | 触发场景 | 解决方案 |
|----------|------|----------|----------|
| `task_not_found` | 任务不存在 | taskId 参数错误 | 使用 TaskList 获取正确 ID |
| `task_blocked` | 任务被阻塞 | 前置任务未完成 | 检查 blockedBy 列表 |
| `task_already_completed` | 任务已完成 | 重复更新已完成任务 | 检查任务状态 |
| `circular_dependency` | 循环依赖 | 依赖关系形成环 | 重新设计依赖关系 |
| `invalid_dependency` | 依赖错误 | addBlockedBy 参数错误 | 检查任务 ID 是否存在 |

### 8.4 通信相关错误

| 错误代码 | 含义 | 触发场景 | 解决方案 |
|----------|------|----------|----------|
| `invalid_message_type` | 消息类型错误 | type 参数不是有效值 | 使用 message/broadcast/shutdown_* |
| `message_delivery_failed` | 消息送达失败 | 网络或系统问题 | 检查网络，重试 |
| `broadcast_failed` | 广播失败 | 无活跃成员 | 检查成员状态 |
| `recipient_unavailable` | 接收者不可用 | 成员已关闭或异常 | 重新生成成员 |

### 8.5 权限相关错误

| 错误代码 | 含义 | 触发场景 | 解决方案 |
|----------|------|----------|----------|
| `permission_denied` | 权限不足 | 文件或目录权限问题 | 检查文件权限 |
| `tool_not_available` | 工具不可用 | 成员类型不支持该工具 | 检查 subagent_type |
| `file_access_denied` | 文件访问被拒 | 文件被其他进程锁定 | 关闭占用进程 |

### 8.6 系统相关错误

| 错误代码 | 含义 | 触发场景 | 解决方案 |
|----------|------|----------|----------|
| `timeout` | 操作超时 | 网络或服务问题 | 检查网络，重试 |
| `resource_exhausted` | 资源耗尽 | 内存或磁盘不足 | 清理磁盘，关闭其他程序 |
| `api_rate_limit` | API 限流 | 调用频率过高 | 等待后重试 |
| `model_unavailable` | 模型不可用 | 指定的模型不存在 | 使用有效模型名称 |

---

## 九、日志分析技巧

### 8.1 查看最近的错误

```bash
# 查看最近的 10 条错误消息
grep -i "error\|fail\|失败" ~/.claude/teams/{team-name}/.state/session-log.md | tail -10
```

### 8.2 查看特定成员的活动

```bash
# 查看特定成员的所有活动
grep "member-name" ~/.claude/teams/{team-name}/.state/session-log.md
```

### 8.3 查看任务生命周期

```bash
# 查看特定任务的所有状态变更
grep "task-001" ~/.claude/teams/{team-name}/.state/session-log.md
```

---

## 十、成员陷入自我修正循环

### 10.1 诊断

**症状识别**：

如果你的成员持续输出以下内容，说明陷入了自我修正循环：

**类型 A：工具调用格式循环**
```
● 我需要使用正确的工具调用格式，尝试使用正确的工具调用语法。
● 我需要使用正确的工具调用格式，尝试使用正确的参数格式。
● 我需要使用正确的工具调用格式，尝试使用正确的工具名称。
● 我需要使用正确的工具调用格式，尝试使用正确的任务 ID。
```

**类型 B：参数构造失败循环**
```
● 我需要使用正确的语法。
  <parameter=
● 我需要使用正确的语法。
  <parameter=
● 我需要使用正确的语法。
  <parameter=
```

**类型 C：自我反思文本循环**
```
● 我需要使用正确的语法。
● 我需要使用正确的格式。
● 我需要检查参数...
```

**问题根源**：
- 模型在构造工具调用时遇到困难
- 缺少明确的"停止自我修正"机制
- 成员 Prompt 中没有循环防护指令
- 参数格式或任务 ID 获取方式有问题

### 10.2 检查方法

```bash
# 查看最近的输出
tail -30 ~/.claude/teams/{team-name}/.state/session-log.md

# 统计重复模式
tail -100 ~/.claude/teams/{team-name}/.state/session-log.md | grep -c "我需要使用正确的"
tail -100 ~/.claude/teams/{team-name}/.state/session-log.md | grep -c "我需要使用正确的语法"

# 检查未完成的工具调用
tail -100 ~/.claude/teams/{team-name}/.state/session-log.md | grep "<parameter="

# 查看特定成员的活动
grep -A 5 "member-name" ~/.claude/teams/{team-name}/.state/session-log.md | tail -30
```

### 10.3 解决方案

**步骤 1：立即终止陷入循环的成员**

```bash
# 获取成员的 task_id（需要从团队配置或日志中查找）
# 使用 TaskStop 终止成员
# 注意：TaskStop 需要知道成员的 task_id
```

**步骤 2：分析失败原因**

检查以下方面：
- 任务描述是否清晰明确
- 参数要求是否易于理解
- 是否有特殊字符或编码问题
- taskId/recipient 等关键参数的获取方式是否正确

**步骤 3：重新生成成员并改进 Prompt**

在生成成员时，在 prompt 中添加：

```
## 重要：循环防护

如果任何工具调用失败：
1. 最多尝试 2 次修正参数
2. 如果仍失败，立即用 SendMessage 通知 team-lead
3. 消息包含：工具名、参数、错误信息

禁止行为：
- 重复输出"我需要使用正确的工具调用格式"
- 输出未完成的工具调用（如 "<parameter="）
- 超过 2 次重试后继续尝试
```

**步骤 4：从检查点恢复或重新分配任务**

```如果可用，使用 MCP 诊断工具从检查点恢复：
python3 ~/.claude/mcp-servers/agent-teams-mcp/server.py checkpoint <team_name> <checkpoint_name>

或使用独立脚本：
python3 ~/.claude/mcp-servers/agent-teams-mcp/server.py list_checkpoints <team_name>
```

### 10.4 预防措施

**在角色 Prompt 中添加循环防护**：

参考 [role.md](./role.md) 中的"循环防护"和"工具调用失败处理"章节，确保每个角色的 Prompt 模板都包含：

1. 明确的循环检测指令
2. 最多重试次数限制（2次）
3. 立即向 Leader 报告的机制
4. 禁止行为的明确列表

**示例**：
```
## 循环防护（重要！）

如果你发现自己陷入了循环：
1. **立即停止**自我修正尝试
2. 向 {leader_name} 发送消息报告问题
3. 消息格式：
   SendMessage(
     type="message",
     recipient="{leader_name}",
     content="无法调用工具：[工具名称]。错误：[具体错误信息]。已尝试自我修正但失败，需要协助。",
     summary="工具调用失败-[工具名称]"
   )

## 工具调用失败处理

如果工具调用失败：
- 检查参数是否完整
- 检查参数类型是否正确
- 检查关键参数是否有效
- 如果连续 2 次失败，立即向 {leader_name} 求助
- 禁止输出未完成的工具调用（如 "<parameter="）
- 禁止重复输出"我需要使用正确的..."这类自我反思文本
```

---

## 十一、应急恢复脚本

```bash
#!/bin/bash
# emergency-recover.sh - 应急恢复脚本

TEAM_NAME=${1:-"unknown"}
LOG_FILE=~/.claude/teams/$TEAM_NAME/.state/session-log.md

echo "=== Agent Teams 应急恢复 ==="
echo ""

echo "1. 检查团队配置"
if [ -f ~/.claude/teams/$TEAM_NAME/config.json ]; then
    echo "  ✓ 团队配置存在"
else
    echo "  ✗ 团队不存在！"
    exit 1
fi

echo ""
echo "2. 检查任务状态"
if [ -f ~/.claude/tasks/$TEAM_NAME/*.json ]; then
    echo "  ✓ 任务文件存在"
else
    echo "  ✗ 任务文件丢失！"
fi

echo ""
echo "3. 检查会话日志"
if [ -f "$LOG_FILE" ]; then
    echo "  ✓ 会话日志存在"
    echo ""
    echo "  最近的 5 行日志："
    tail -5 "$LOG_FILE" | sed 's/^/    /'
else
    echo "  ✗ 会话日志缺失！"
fi

echo ""
echo "4. 建议操作"
echo "  - 检查所有成员状态"
echo "  - 查看任务列表"
echo "  - 评估是否需要重新创建团队"
```

使用：
```bash
~/.claude/skills/agent-teams/emergency-recover.sh team-name
```
