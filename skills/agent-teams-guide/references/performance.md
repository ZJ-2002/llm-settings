# Agent Teams 性能与成本指南

> 本文档帮助你评估何时使用 Agent Teams，以及如何优化成本和性能。

---

## 一、何时使用 Team vs 单人

### 决策树

```
任务需要处理？
  │
  ├─ 影响 1-2 个文件？
  │   └─ → 单人，不使用 Team
  │
  ├─ 影响 3-5 个文件，逻辑清晰？
  │   ├─ 需要多种视角？
  │   │   ├─ 是 → Team（2-3 成员）
  │   │   └─ 否 → 单人（顺序完成）
  │   └─ 可以一次性完成？
  │       └─ → 单人
  │
  ├─ 影响 5-10 个文件？
  │   ├─ 可以并行？
  │   │   ├─ 是 → Team（并行开发）
  │   │   └─ 否 → Team（顺序开发+测试+审查）
  │   └─ 不确定架构？
  │       └─ → Team（研究+开发）
  │
  └─ 影响 10+ 个文件？
      └─ → Team（3-5 成员）
```

### 详细对比

| 场景 | 单人 | Team |
|------|------|------|
| 修改 1 个函数 | ✅ 快速直接 | ❌ 开销大 |
| 修复简单 Bug | ✅ 快速定位 | ❌ 浪费资源 |
| 重构 2-3 个文件 | ⚠️ 可行 | ✅ 有专人审查更好 |
| 实现新功能（5+ 文件）| ⚠️ 可能遗漏细节 | ✅ 并行效率高 |
| 探索未知代码库 | ⚠️ 深度有限 | ✅ 多角度探索 |
| 全栈开发（前后端）| ❌ 上下文负担大 | ✅ 专人专精 |

**经验法则**：
- 修改 < 100 行代码 → 单人
- 修改 100-500 行代码 → 2 人 Team
- 修改 > 500 行代码 → 3-4 人 Team

---

## 二、成本估算

### 2.1 基本单位成本

| 操作 | 大约消耗 | 说明 |
|------|---------|------|
| TaskCreate | ~500 tokens | 创建任务描述 |
| TaskUpdate | ~300 tokens | 更新状态 |
| TaskList | ~200 tokens | 读取任务列表 |
| TaskGet | ~400 tokens | 读取任务详情 |
| SendMessage (message) | ~800-1500 tokens | 通信消息 |
| SendMessage (broadcast) | ~800-1500 × N | N = 成员数 |
| Leader 一轮编排 | ~2000-3000 tokens | 包括多个工具调用 |
| Developer 完成任务 | ~5000-15000 tokens | 取决于任务复杂度 |
| Tester 运行测试 | ~3000-8000 tokens | 分析测试结果 |

### 2.2 典型场景成本估算

**场景 A：简单功能开发（2 人 Team）**

```
操作序列：
1. TeamCreate: ~500 tokens
2. TaskCreate × 3: 1500 tokens
3. Task × 2 (生成成员): ~1000 tokens
4. Leader 分配任务: ~1500 tokens
5. Developer 工作: ~8000 tokens
6. 测试工作: ~5000 tokens
7. 通信消息 (8 次): ~10000 tokens
8. 关闭流程: ~2000 tokens

总计: ~29,500 tokens ≈ $0.06-0.12 (取决于模型)
```

**场景 B：复杂功能（3 人 Team，循环 2 次）**

```
第一轮开发+测试+审查: ~35,000 tokens
第二轮修复: ~20,000 tokens
总计: ~55,000 tokens ≈ $0.11-0.22
```

**场景 C：单人完成（无 Team）**

```
开发 + 简单自检: ~8000 tokens ≈ $0.016-0.032

对比：
- 单人: $0.016-0.032
- Team: $0.06-0.12
- 成本倍数: Team 是单人的 2-4 倍
```

### 2.3 成本优化建议

| 优化方向 | 具体措施 | 节省约 |
|----------|----------|--------|
| 减少成员数 | 只用必要的角色 | 30-50% |
| 合并消息 | 一次包含多个信息 | 20% |
| 避免 broadcast | 用私聊代替 | 25% × N |
| 使用更轻的模型 | 非核心任务用 Haiku | 60-70% |
| 减少循环次数 | 一次修复成功 | 40% |

---

## 三、性能优化

### 3.1 减少 API 调用次数

**优化前**：

```
每次消息分开发送：
SendMessage("完成文件 A")
SendMessage("完成文件 B")
SendMessage("完成文件 C")

// 3 次调用 = 3 × 通信开销
```

**优化后**：

```
合并发送：
SendMessage("完成文件: A, B, C")

// 1 次调用 = 1 × 通信开销
```

**批量操作示例**：

```javascript
// 收集所有完成的工作
const completedFiles = [];

// 完成文件后
completedFiles.push('src/api/auth.ts');

// 批量上报
if (completedFiles.length >= 5 || isLastFile) {
  SendMessage({
    type: 'message',
    recipient: 'team-lead',
    content: `已完成 ${completedFiles.length} 个文件:\n${completedFiles.join('\n')}`,
    summary: `完成${completedFiles.length}个文件`
  });
}
```

### 3.2 延迟生成成员

**策略**：只有当成员即将有工作时才生成

```
错误：一开始就生成所有成员
TeamCreate()
Task(...)
Task(...)  // developer
Task(...)  // tester (空闲等待)
Task(...)  // reviewer (空闲等待)
// 空闲 = 浪费

正确：按需生成
TeamCreate()
Task(...)  // 开发任务

// 只生成 developer
Task(...)  // developer

// 等待开发完成后再生成 tester
// ... developer 完成
Task(...)  // tester
```

**节省**：早期生成的成员空闲期间的资源

### 3.3 合理选择模型

| 任务类型 | 推荐模型 | 原因 |
|----------|----------|------|
| Leader 编排 | Son | 需要强逻辑 |
| 核心开发 | Opus/Son | 需要高质量代码 |
| 测试运行 | Haiku | 主要是模式匹配 |
| 简单文档生成 | Haiku | 结构化输出 |
| 代码搜索 | Haiku | 关键词匹配 |

**模型选择示例**：

```javascript
// 为不同成员选择模型
const members = [
  {
    name: 'leader',
    subagent_type: 'general-purpose',
    model: 'sonnet'  // 编排需要强推理
  },
  {
    name: 'developer',
    subagent_type: 'general-purpose',
    model: 'opus'  // 核心代码需要最高质量
  },
  {
    name: 'tester',
    subagent_type: 'general-purpose',
    model: 'haiku'  // 测试分析可以用轻量模型
  },
  {
    name: 'reviewer',
    subagent_type: 'Explore',
    model: 'sonnet'  // 审查需要良好判断
  }
];
```

### 3.4 缓存策略

**可以缓存的信息**：

| 信息类型 | 缓存位置 | 有效期 |
|----------|----------|--------|
| 项目结构 | 任务描述中 | 整个项目期间 |
| 常用命令 | 任务描述中 | 整个项目期间 |
| 文件路径列表 | 任务描述中 | 整个项目期间 |
| 代码规范 | README 或单独文件 | 永久 |

**示例**：

```json
{
  "description": "实现登录功能。\n\n项目结构提示：\n- src/api/: API 接口\n- src/models/: 数据模型\n- src/routes/: 路由定义\n\n常用命令：\n- npm run test: 运行测试\n- npm run lint: 代码检查"
}
```

---

## 四、瓶颈识别与解决

### 4.1 常见瓶颈

| 瓶颈 | 症状 | 解决方案 |
|------|--------|---------|
| 成员空闲等待 | idle 通知频繁 | 延迟生成成员 |
| 消息传递延迟 | 响应时间 > 30s | 合并消息，减少次数 |
| 任务切换开销 | 频繁 TaskUpdate | 批量更新 |
| 上下文过大 | 成员重复解释 | 在任务描述中提供完整信息 |
| 依赖链过长 | blockedBy 深度 > 5 | 拆分任务 |

### 4.2 性能监控

**监控脚本示例**：

```javascript
// 性能追踪器
const performanceTracker = {
  sendMessageCount: 0,
  taskUpdateCount: 0,
  startTime: Date.now(),

  trackSendMessage() {
    this.sendMessageCount++;
  },

  trackTaskUpdate() {
    this.taskUpdateCount++;
  },

  report() {
    const elapsed = (Date.now() - this.startTime) / 1000;
    console.log(`=== 性能报告 ===`);
    console.log(`运行时间: ${elapsed.toFixed(1)}秒`);
    console.log(`SendMessage 调用: ${this.sendMessageCount}次`);
    console.log(`TaskUpdate 调用: ${this.taskUpdateCount}次`);
    console.log(`平均调用频率: ${(this.sendMessageCount / elapsed).toFixed(2)}次/秒`);
  }
};

// 在关键操作处插入
performanceTracker.trackSendMessage();
```

---

## 五、最佳实践总结

### 成本最佳实践

1. **最小化 Team 规模**
   - 从 2 人开始，必要时再增加
   - 每增加 1 人，成本增加 ~40%

2. **避免循环依赖**
   - 每次循环都是额外成本
   - 一次修复成功的目标

3. **选择合适的模型**
   - 非关键任务用 Haiku
   - 可节省 60-70% 成本

4. **精确的任务描述**
   - 一次说清，避免来回通信
   - 节省澄清消息的成本

### 性能最佳实践

1. **按需生成成员**
   - 不要提前生成会空闲的成员
   - 延迟生成节省等待成本

2. **批量操作**
   - 合并多个更新为一次
   - 合并多个消息为一次

3. **合理设置依赖**
   - 避免不必要的阻塞
   - 并行执行可并行的任务

4. **及时关闭 Team**
   - 完成后立即关闭
   - 避免成员持续运行消耗资源

---

## 六、成本效益分析示例

### 示例：实现用户认证模块

| 方案 | 成本 | 时间 | 质量 | 推荐度 |
|------|------|------|------|--------|
| 单人快速实现 | $0.03 | 10分钟 | ⭐⭐⭐ | 小型项目 |
| 2人 Team | $0.08 | 15分钟 | ⭐⭐⭐⭐ | 一般项目 |
| 3人 Team（含审查）| $0.15 | 20分钟 | ⭐⭐⭐⭐⭐⭐ | 生产项目 |

**决策依据**：
- 如果是原型/演示 → 单人
- 如果是内部工具 →项目 → 2人 Team
- 如果是面向用户的产品 → 3人 Team

---

## 七、警告信号

| 指标 | 警告阈值 | 行动 |
|--------|----------|------|
| 成员数 | > 5 | 考虑拆分项目 |
| 依赖深度 | > 5 | 拆分任务 |
| 消息频率 | > 10次/分钟 | 检查是否有死循环 |
| 成本增长 | > $0.5 | 评估是否值得 |
| 运行时间 | > 30分钟 | 考虑拆分会话 |
