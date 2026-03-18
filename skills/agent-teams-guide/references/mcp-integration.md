# MCP 工具集成指南

> 本文档说明 Agent Teams 的 MCP（Model Context Protocol）工具集成。

---

## 一、MCP 工具状态

### 1.1 自我进化系统工具

| 工具名称 | 状态 | 说明 |
|---------|------|------|
| `get_learned_rules_tool` | ⚠️ 可选 | 获取已学习的用户反馈规则 |
| `capture_user_feedback_tool` | ⚠️ 可选 | 捕获用户矫正指令并学习 |
| `analyze_feedback_patterns_tool` | ⚠️ 可选 | 分析反馈模式 |
| `delete_rule_tool` | ⚠️ 可选 | 删除特定规则 |
| `update_rule_success_rate_tool` | ⚠️ 可选 | 更新规则成功率 |
| `reset_feedback_rules_tool` | ⚠️ 可选 | 重置所有学习规则 |
| `get_knowledge_summary_tool` | ⚠️ 可选 | 获取知识库摘要 |

### 1.2 诊断与监控工具

| 工具名称 | 状态 | 说明 |
|---------|------|------|
| `diagnose_team_status_tool` | ⚠️ 可选 | 诊断团队状态 |
| `get_team_performance_tool` | ⚠️ 可选 | 获取团队性能指标 |
| `list_active_teams_tool` | ⚠️ 可选 | 列出所有活动的 Agent Teams |
| `save_team_checkpoint_tool` | ⚠️ 可选 | 保存团队当前状态到检查点 |
| `list_checkpoints_tool` | ⚠️ 可选 | 列出保存的检查点 |
| `detect_repeating_errors_tool` | ⚠️ 可选 | 检测成员是否陷入自我修正循环 |

### 1.3 内存感知工具

| 工具名称 | 状态 | 说明 |
|---------|------|------|
| `get_permit_status_tool` | ⚠️ 可选 | 读取内存许可池状态 |
| `get_memory_status_tool` | ⚠️ 可选 | 获取详细内存状态 |

---

## 二、MCP 服务器配置

### 2.1 检查 MCP 是否可用

在使用任何 MCP 工具前，可以检查工具是否存在：

```
# 如果 MCP 服务器已配置，工具会自动出现在可用工具列表中
# 如果工具不存在，系统会返回错误
```

### 2.2 配置 MCP 服务器（可选）

如果需要使用完整的 MCP 功能，需要配置 MCP 服务器：

**步骤 1：安装依赖**

```bash
pip install mcp
```

**步骤 2：配置 Claude Code**

在 Claude Code 的配置文件中添加 `agent-teams-mcp` 服务器：

```json
{
  "mcpServers": {
    "agent-teams-mcp": {
      "command": "python",
      "args": ["/path/to/agent-teams-mcp/server.py"]
    }
  }
}
```

**步骤 3：重启 Claude Code**

---

## 三、无 MCP 时的替代方案

### 3.1 自我进化系统

如果 MCP 工具不可用，可以跳过 SKILL.md 中的"零、自我进化系统"章节。Agent Teams 仍可正常工作。

**替代方案**：
- 手动记录用户反馈规则到项目的 `CLAUDE.md` 或 `USER.md` 文件
- 在生成成员时，在 prompt 中直接包含已知的约束规则

### 3.2 诊断与监控

如果 MCP 诊断工具不可用，使用独立脚本：

| 命令 | 功能 |
|------|------|
| `python3 ~/.claude/mcp-servers/agent-teams-mcp/diagnose.py diagnose <team_name>` | 诊断团队状态 |
| `python3 ~/.claude/mcp-servers/agent-teams-mcp/diagnose.py performance <team_name>` | 获取性能指标 |
| `python3 ~/.claude/mcp-servers/agent-teams-mcp/diagnose.py list` | 列出所有团队 |
| `python3 ~/.claude/mcp-servers/agent-teams-mcp/diagnose.py detect-loop <team_name>` | 检测循环 |

### 3.3 内存监控

如果 MCP 内存工具不可用：

1. 使用系统命令监控内存：
   ```bash
   # Linux
   free -h
   top -o %MEM

   # macOS
   vm_stat
   top -o mem
   ```

2. 根据内存使用情况手动调整并发成员数量

---

## 四、最佳实践

### 4.1 优雅降级

在 prompt 中设计优雅降级机制：

```markdown
## 工具使用优先级

1. 优先使用 MCP 工具（如果可用）
2. 如果 MCP 不可用，使用 Bash 命令替代
3. 如果 Bash 命令失败，手动记录并向用户报告
```

### 4.2 错误处理

```markdown
## MCP 工具调用失败处理

如果 MCP 工具调用返回 "tool not found" 错误：
1. 不要重试
2. 跳过该功能
3. 继续使用标准工具完成任务
```

---

## 五、独立脚本位置

如果 MCP 服务器未配置，可以使用独立脚本：

```
~/.claude/mcp-servers/agent-teams-mcp/
├── diagnose.py          # 诊断脚本
├── mcp_server.py        # MCP 服务器（可选）
└── README.md            # 使用说明
```

**注意**：如果 `~/.claude/mcp-servers/agent-teams-mcp/` 目录不存在，可以跳过 MCP 相关功能，Agent Teams 的核心功能不受影响。
