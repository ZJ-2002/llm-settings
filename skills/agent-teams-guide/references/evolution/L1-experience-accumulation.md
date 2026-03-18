# L1：经验积累层

> Agent Teams 自进化架构的经验学习层

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)

---

## 概述

L1 层负责从历史数据中学习和积累经验，包括：
- 任务指纹识别
- 成员能力建模
- 模式匹配
- 经验索引

---

## 任务指纹识别器

### 核心功能

```
任务输入描述
    │
    ▼
┌──────────────────────────────────┐
│ 1. 预处理                      │
│    - 提取关键词                  │
│    - 识别文件类型                │
│    - 检测领域标识                │
└──────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────┐
│ 2. 特征提取                    │
│    - 复杂度评估                  │
│    - 任务类型分类                │
│    - 规范围大小                  │
└──────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────┐
│ 3. 指纹生成                    │
│    - 生成哈希签名                │
│    - 计算相似度                  │
│    - 匹配历史模式                │
└──────────────────────────────────┘
    │
    ▼
任务指纹 {
  fingerprint_id: string,
  domain: string,
  type: string,
  complexity: "low" | "medium" | "high",
  confidence: number,
  matched_pattern?: string
}
```

### 指纹结构

```typescript
interface TaskFingerprint {
  fingerprint_id: string;

  // 基础特征
  domain: "programming" | "medical_research" | "data_analysis" | "other";
  type: "feature" | "bugfix" | "refactor" | "research" | "review";
  complexity: "low" | "medium" | "high";

  // 语义特征
  keywords: string[];
  intent: string;
  entities: {
    files?: string[];
    apis?: string[];
    endpoints?: string[];
    components?: string[];
  };

  // 量级特征
  estimated_duration?: number;
  estimated_task_count?: number;
  estimated_roles_needed?: number;

  // 上下文特征
  context: {
    project_type?: string;
    tech_stack?: string[];
    previous_tasks?: string[];
  };

  // 匹配结果
  matches: {
    pattern_id?: string;
    similarity: number;
    confidence: number;
    historical_performance?: PerformanceMetrics;
  };
}

interface PerformanceMetrics {
  avg_duration: number;
  success_rate: number;
  avg_cost: number;
  sample_size: number;
}
```

### 指纹匹配算法

```typescript
interface FingerprintMatchResult {
  matched: boolean;
  pattern_id?: string;
  similarity: number;           // 0-1
  confidence: number;           // 0-1
  configuration?: TaskConfiguration;
  performance_prediction?: PerformancePrediction;
}

interface PerformancePrediction {
  estimated_duration: number;
  estimated_cost: number;
  success_probability: number;
  recommended_milestones: Milestone[];
}
```

### 任务分类器

```typescript
interface TaskClassifier {
  // 领域分类
  classifyDomain(input: string): DomainType;

  // 类型分类
  classifyType(input: string): TaskType;

  // 复杂度评估
  assessComplexity(
    input: string,
    context?: TaskContext
  ): ComplexityLevel;

  // 全部分类
  classifyTask(
    input: string,
    context?: TaskContext
  ): TaskFingerprintingerprint;
}

type DomainType =
  | "programming"
  | "medical_research"
  | "data_analysis"
  | "content_creation"
  | "unknown";

type TaskType =
  | "feature_development"
  | "bug_fix"
  | "refactoring"
  | "literature_review"
  | "data_processing"
  | "documentation"
  | "unknown";

type ComplexityLevel = "low" | "medium" | "high" | "very_high";
```

### 匹配策略

```typescript
interface MatchingStrategy {
  // 精确匹配
  exactMatch: {
    enabled: boolean;
    threshold: number;  // 0.95+
  };

  // 模糊匹配
  fuzzyMatch: {
    enabled: boolean;
    algorithm: "jaccard" | "cosine" | "embedding";
    threshold: number;  // 0.85+
  };

  // 语义匹配
  semanticMatch: {
    enabled: boolean;
    use_embeddings: boolean;
    threshold: number;  // 0.80+
  };

  // 组合策略
  combination: "exact_first" | "semantic_first" | "ensemble";
}
```

---

## 成员能力建模器

### 核心概念

```
成员能力 = 多维能力向量 + 历史表现数据 + 协作模式
```

### 能力向量

```typescript
interface CapabilityVector {
  // 通用能力 (0-1)
  general: {
    comprehension: number;     // 理解能力
    planning: number;          // 规划能力
    execution: number;         // 执行能力
    problem_solving: number;   // 问题解决能力
    communication: number;     // 沟通能力
  };

  // 领域能力 (0-1)
  domain: {
    programming: {
      coding: number;
      debugging: number;
      architecture: number;
      testing: number;
      refactoring: number;
    };
    medical_research: {
      literature_search: number;
      data_analysis: number;
      writing: number;
      citation_management: number;
    };
  };

  // 任务类型偏好
  task_preferences: TaskPreference[];

  // 协作特征
  collaboration: {
    responsiveness: number;      // 响应速度
    reliability: number;        // 可靠性
    handoff_quality: number;    // 移交质量
    solo_efficiency: number;    // 独立效率
    team_efficiency: number;     // 团队效率
  };
}

interface TaskPreference {
  task_type: string;
  affinity: number;             // 亲和度 (0-1)
  performance: PerformanceSummary;
}

interface PerformanceSummary {
  tasks_completed: number;
  avg_duration: number;
  success_rate: number;
  quality_score: number;
}
```

### 能力评估

```typescript
interface CapabilityAssessment {
  role_name: string;

  // 能力评估
  capabilities: CapabilityVector;

  // 性能历史
  history: {
    total_sessions: number;
    total_tasks: number;
    successful_tasks: number;
    failed_tasks: number;
    avg_session_duration: number;
    avg_task_duration: number;
  };

  // 趋势分析
  trends: {
    learning_curve: "steep" | "moderate" | "flat";
    stability: number;          // 稳定性 (0-1)
    improvement_rate: number;    // 改进速度
  };

  // 适用场景
  best_for: string[];           // 最适合的任务类型
  avoid_for: string[];          // 应避免的任务类型
}
```

### 任务-角色匹配

```typescript
interface TaskRoleMatching {
  task_fingerprint: TaskFingerprint;

  // 角色匹配度
  role_scores: {
    [role_name: string]: {
      match_score: number;       // 匹配度 (0-1)
      reasoning: string[];       // 匹配理由
      confidence: number;       // 置信度
    };
  };

  // 推荐配置
  recommended_configuration: {
    roles: string[];
    allocation: RoleAllocation[];
  };
}

interface RoleAllocation {
  role: string;
  weight: number;              // 权重
  tasks: TaskAssignment[];
}

interface TaskAssignment {
  task_id: string;
  confidence: number;
}
```

---

## 模式匹配器

### 成功模式匹配

```typescript
interface SuccessPatternMatcher {
  // 查找匹配的成功模式
  findMatchingPatterns(
    task_fingerprint: TaskFingerprint
  ): PatternMatch[];

  // 获取推荐序列
  getRecommendedSequence(
    pattern_id: string
  ): ExecutionSequence;

  // 检查当前执行是否符合模式
  checkExecutionConformance(
    pattern_id: string,
    current_state: ExecutionState
  ): ConformanceResult;
}

interface PatternMatch {
  pattern: SuccessPattern;
  similarity: number;
  confidence: number;
  applicability: number;
}

interface ExecutionSequence {
  steps: ExecutionStep[];
  communication_points: CommunicationPoint[];
}

interface ConformanceResult {
  conforming: boolean;
  deviations: Deviation[];
  recovery_suggestions?: RecoverySuggestion[];
}
```

### 错误模式检测

```typescript
interface ErrorPatternDetector {
  // 检测错误模式
  detectErrorPattern(
    error_context: ErrorContext
  ): ErrorPatternMatch;

  // 获取恢复建议
  getRecoveryStrategy(
    pattern_id: string
  ): RecoveryStrategy;

  // 记录新模式
  recordNewPattern(
    pattern: ErrorPattern
  ): void;
}

interface ErrorContext {
  error_type: string;
  error_message: string;
  stack_trace?: string;
  task_id: string;
  role: string;
  recent_history: ExecutionEvent[];
  retry_count: number;
}

interface ErrorPatternMatch {
  matched: boolean;
  pattern?: ErrorPattern;
  similarity?: number;
  suggested_action?: RecoveryAction;
}

interface RecoveryAction {
  action_type: "retry" | "alternate_approach" | "pause_and_analyze";
  description: string;
  parameters?: Record<string, any>;
}
```

---

## 经验索引器

### 索引结构

```typescript
interface ExperienceIndex {
  // 按任务类型索引
  by_task_type: {
    [task_type: string]: ExperienceEntry[];
  };

  // 按领域索引
  by_domain: {
    [domain: string]: ExperienceEntry[];
  };

  // 按复杂度索引
  by_complexity: {
    [complexity: string]: ExperienceEntry[];
  };

  // 按角色组合索引
  by_role_combination: {
    [combination_hash: string]: ExperienceEntry[];
  };

  // 语义索引（用于模糊搜索）
  semantic_index: SemanticIndex;
}

interface ExperienceEntry {
  entry_id: string;
  session_id: string;
  timestamp: number;

  task_fingerprint: TaskFingerprint;
  configuration_used: TaskConfiguration;

  outcome: {
    success: boolean;
    duration: number;
    cost: number;
    quality_score: number;
  };

  lessons_learned: string[];
}
```

---

## 实施要点

### 优先级：⭐⭐⭐⭐⭐

### 预估时间：11 小时

| 任务 | 估时 | 依赖 |
|------|------|------|
| 实现任务指纹识别器 | 3h | L0 |
| 实现成员能力建模器 | 3h | L0 |
| 实现成功模式匹配器 | 2h | 指纹识别 |
| 实现错误模式检测器 | 2h | L0 |
| 实现经验索引器 | 1h | L0 |

### 交付物
- `task-patterns.json` 生成
- `role-performance.json` 生成
- 模式匹配功能

---

[上一章：L0 数据基础设施层](./L0-data-infrastructure.md) | [下一章：L2 行为适应层 →](./L2-behavior-adaptation.md)

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)
