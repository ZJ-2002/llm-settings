# L2：行为适应层

> Agent Teams 自进化架构的运行时适应层

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)

---

## 概述

L2 层负责运行时的动态适应，包括：
- 自适应任务分配
- 自适应通信策略
- 依赖优化

---

## 自适应分配器

### 核心机制

```
任务分配决策流程：
┌─────────────────────────────────────────────────────────┐
│  输入：任务列表 + 成员能力 + 历史模式                 │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  步骤1: 基础匹配（基于任务类型和角色能力）            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  步骤2: 历史优先级调整（基于成功/失败历史）             │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  步骤3: 负载均衡（考虑当前工作负载）                    │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  步骤4: 协作优化（考虑角色间协作效率）                  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  输出：优化后的任务分配方案                             │
└─────────────────────────────────────────────────────────┘
```

### 分配策略

```typescript
interface AllocationStrategy {
  // 基础策略
  base: "capability_based" | "round_robin" | "random";

  // 优先级策略
  priority: {
    use_historical_priority: boolean;
    use_collaboration_score: boolean;
    use_load_balancing: boolean;
  };

  // 负载均衡
  load_balancing: {
    enabled: boolean;
    algorithm: "least_loaded" | "weighted" | "dynamic";
    max_tasks_per_role: number;
  };

  // 自适应调整
  adaptive: {
    enabled: boolean;
    learning_rate: number;      // 学习率
    adjustment_frequency: number; // 调整频率
  };
}

interface AllocationResult {
  allocations: TaskAllocation[];
  confidence: number;
  reasoning: string[];
  expected_performance: PerformancePrediction;
}
```

---

## 自适应通信器

### 通信频率自适应

```typescript
interface CommunicationPolicy {
  // 默认策略
  default: "task_boundaries" | "milestone_based" | "incremental";

  // 任务复杂度映射
  complexity_mapping: {
    low: "task_boundaries";
    medium: "task_boundaries";
    high: "milestone_based";
    very_high: "incremental";
  };

  // 里程碑配置
  milestones: {
    enabled_for: ["high", "very_high"];
    interval: "time_based" | "progress_based";
    interval_value: number;      // 分钟或百分比
  };

  // 增量配置
  incremental: {
    enabled_for: ["very_high"];
    triggers: {
      time_threshold: number;   // 超过N分钟
      error_threshold: number;   // 出错次数
      complexity_threshold: number;
    };
  };

  // 动态调整
  adaptive: {
    enabled: boolean;
    adjustment_criteria: {
      communication_overhead: number;  // 通信开销占比阈值
      early_detection_gain: number;    // 早期发现问题收益
    };
  };
}
```

### 消息类型决策树

```typescript
interface MessageTypeDecision {
  // 决策因素
  factors: {
    urgency: "low" | "medium" | "high" | "critical";
    audience_size: number;
    content_type: "information" | "request" | "error" | "decision";
    recipient_availability: boolean;
  };

  // 决策规则
  rules: {
    // 使用 broadcast 的条件
    use_broadcast_when: {
      audience_size: number;      // 超过N人
      urgency: "critical" | "high";
    };

    // 使用 message 的条件
    use_message_when: {
      audience_size: number;      // 少于N人
      recipient_specified: boolean;
    };
  };

  // 决策结果
  decision: {
    type: "message" | "broadcast";
    recipient?: string;
    priority: number;
    urgency: string;
  };
}
```

### 沟通效率优化

```typescript
interface CommunicationOptimizer {
  // 分析当前沟通模式
  analyzeCommunicationPattern(
    session_events: RuntimeEvent[]
  ): CommunicationAnalysis;

  // 识别优化机会
  identifyOptimizationOpportunities(
    analysis: CommunicationAnalysis
  ): OptimizationOpportunity[];

  // 应用优化建议
  applyOptimizations(
    opportunities: OptimizationOpportunity[]
  ): void;
}

interface CommunicationAnalysis {
  total_messages: number;
  messages_by_type: {
    message: number;
    broadcast: number;
  };

  message_timing: {
    avg_interval: number;
    distribution: number[];
  };

  efficiency_metrics: {
    communication_overhead: number;  // 通信时间占比
    information_density: number;        // 信息密度
    redundancy_rate: number;            // 冗余率
  };
}

interface OptimizationOpportunity {
  type: "reduce_frequency" | "batch_messages" | "use_broadcast" | "use_message";
  description: string;
  potential_saving: number;
  confidence: number;
}
```

---

## 依赖优化器

### 依赖分析

```typescript
interface DependencyAnalysis {
  tasks: TaskNode[];
  edges: DependencyEdge[];

  metrics: {
    total_tasks: number;
    total_edges: number;
    max_depth: number;
    average_depth: number;
    cyclomatic_complexity: number;
    has_cycles: boolean;
  };

  bottlenecks: Bottleneck[];
  parallel_opportunities: ParallelizationOpportunity[];
}

interface TaskNode {
  task_id: string;
  role?: string;
  estimated_duration?: number;

  dependencies: string[];
  dependents: string[];
}

interface Bottleneck {
  task_id: string;
  type: "sequential" | "blocked" | "overloaded";
  impact_score: number;
  suggestions: string[];
}

interface ParallelizationOpportunity {
  task_ids: string[];
  can_parallelize: boolean;
  expected_speedup: number;
}
```

### 依赖优化策略

```typescript
interface DependencyOptimizationStrategy {
  // 串行化优化
  serialize_when: {
    task_count: number;
    complexity: "low";
  };

  // 并行化优化
  parallelize_when: {
    task_count: number;
    independence_threshold: number;
  };

  // 拆分策略
  split_when: {
    dependency_depth: number;
    task_duration: number;
  };

  // 虚拟依赖（同步点）
  use_virtual_dependencies: boolean;
}
```

---

## 实施要点

### 优先级：⭐⭐⭐⭐

### 预估时间：9 小时

| 任务 | 估时 | 依赖 |
|------|------|------|
| 实现自适应分配器 | 3h | L1 |
| 实现自适应通信器 | 2h | L0 |
| 实现依赖优化器 | 2h | L0 |
| 集成到主流程 | 2h | L1, L2 |

### 交付物
- 动态任务分配
- 自适应通信频率
- 依赖优化建议

---

[上一章：L1 经验积累层](./L1-experience-accumulation.md) | [下一章：L3 策略进化层 →](./L3-strategy-evolution.md)

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)
