# L0：数据基础设施层

> Agent Teams 自进化架构的基础数据层

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)

---

## 概述

L0 层是整个进化架构的基石，负责：
- 收集运行时事件数据
- 结构化存储历史数据
- 计算性能指标
- 管理知识库版本

---

## 4.1 数据收集器

### 运行时事件类型

```typescript
interface RuntimeEvent {
  event_id: string;
  timestamp: number;
  event_type: "task_start" | "task_complete" | "message_sent" |
               "error_occurred" | "milestone_reached";
  data: EventData;
  session_id: string;
  team_id: string;
}

interface EventData {
  // 任务事件
  task_id?: string;
  task_type?: string;
  assignee?: string;
  duration?: number;

  // 消息事件
  message_type?: "message" | "broadcast" | "shutdown";
  sender?: string;
  recipient?: string;
  message_length?: number;

  // 错误事件
  error_type?: string;
  error_message?: string;
  recovery_strategy?: string;

  // 里程碑事件
  milestone_name?: string;
  milestone_data?: Record<string, any>;
}
```

### 收集策略

```typescript
interface CollectionPolicy {
  // 采样策略（避免数据过多）
  sampling: {
    message_events: "all" | "milestone_only" | "summary";
    task_events: "detailed" | "summary";
    error_events: "all";
  };

  // 聚合策略
  aggregation: {
    window: "per_task" | "per_milestone" | "per_session";
    metrics: ["count", "avg", "sum", "max", "min"];
  };

  // 过滤策略
  filters: {
    exclude_idle_events: boolean;
    exclude_internal_messages: boolean;
    min_message_length: number;
  };
}
```

---

## 4.2 结构化存储

### 目录结构

```
~/.claude/skills/agent-teams/knowledge/
├── base/                        # 基础数据
│   ├── task-patterns.json       # 任务模式库
│   ├── role-performance.json     # 角色表现数据
│   ├── domain-knowledge/        # 领域知识
│   │   ├── programming/
│   │   ├── medical-research/
│   │   └── [其他领域]/
│
├── history/                     # 历史数据
│   ├── sessions/               # 会话历史
│   │   ├── session_001.json
│   │   ├── session_002.json
│   │   └── ...
│   ├── metrics/                # 历史指标
│   │   ├── daily/
│   │   ├── weekly/
│   │   └── monthly/
│
├── learned/                     # 学习成果
│   ├── success-patterns.json   # 成功模式
│   ├── error-patterns.json     # 错误模式
│   ├── optimization-hints.json  # 优化建议
│   ├── ab-test-results.json    # A/B 测试结果
│   └── evolution-log.json      # 进化日志
│
├── cache/                       # 运行时缓存
│   ├── active-session.json
│   └── temp-metrics.json
│
└── config/                      # 配置
    ├── storage-policy.json
    ├── evolution-config.json
    └── domain-mapping.json
```

### 核心数据结构

#### 1. 任务模式库

```json
{
  "version": "1.0.0",
  "last_updated": 1704067200000,
  "patterns": [
    {
      "pattern_id": "pat_prog_001",
      "task_fingerprint": {
        "domain": "programming",
        "type": "feature_development",
        "complexity": "medium",
        "keywords": ["api", "endpoint", "rest"],
        "file_types": ["ts", "js"],
        "estimated_lines": 200
      },
      "optimal_configuration": {
        "roles": ["developer", "tester", "reviewer"],
        "task_structure": {
          "development": 1,
          "testing": 1,
          "review": 1
        },
        "task_dependencies": [
          {"from": "development", "to": "testing"},
          {"from": "testing", "to": "review"}
        ]
      },
      "performance_metrics": {
        "avg_completion_time": 180,
        "success_rate": 0.95,
        "avg_messages_per_task": 8,
        "api_cost_per_session": 0.15,
        "sample_size": 15
      },
      "learned_from": {
        "first_seen": 1700400000000,
        "last_updated": 1703999999999,
        "successful_runs": 14,
        "failed_runs": 1
      },
      "confidence": 0.93
    },
    {
      "pattern_id": "pat_med_001",
      "task_fingerprint": {
        "domain": "medical_research",
        "type": "literature_review",
        "complexity": "high",
        "keywords": ["review", "systematic", "meta-analysis"],
        "output_types": ["markdown", "pdf"],
        "research_scope": "broad"
      },
      "optimal_configuration": {
        "roles": ["medical-researcher", "medical-writer", "medical-reviewer"],
        "task_structure": {
          "literature_search": 2,
          "analysis": 1,
          "drafting": 1,
          "review": 1
        },
        "task_dependencies": [
          {"from": "literature_search", "to": "analysis"},
          {"from": "analysis", "to": "drafting"},
          {"from": "drafting", "to": "review"}
        ]
      },
      "performance_metrics": {
        "avg_completion_time": 600,
        "success_rate": 0.88,
        "avg_messages_per_task": 12,
        "api_cost_per_session": 0.35,
        "sample_size": 8
      },
      "confidence": 0.78
    }
  ],
  "statistics": {
    "total_patterns": 2,
    "high_confidence_patterns": 1,
    "medium_confidence_patterns": 1,
    "avg_sample_size": 11.5
  }
}
```

#### 2. 角色表现数据

```json
{
  "version": "1.0.0",
  "last_updated": 1704067200000,
  "role_profiles": {
    "developer": {
      "role_id": "role_dev_001",
      "role_type": "implementation",
      "subagent_type": "general-purpose",
      "capabilities": {
        "coding": 0.95,
        "debugging": 0.88,
        "architecture": 0.72,
        "testing": 0.65,
        "documentation": 0.70
      },
      "performance_history": {
        "total_tasks_completed": 45,
        "successful_tasks": 42,
        "failed_tasks": 3,
        "avg_completion_time": {
          "mean": 120,
          "median": 110,
          "std": 25,
          "min": 45,
          "max": 300
        },
        "error_rate": 0.067,
        "retry_rate": 0.13
      },
      "task_preferences": {
        "preferred_types": [
          {"type": "api_development", "score": 0.92},
          {"type": "frontend_component", "score": 0.88},
          {"type": "data_processing", "score": 0.75}
        ],
        "avoided_types": [
          {"type": "database_migration", "score": 0.45}
        ]
      },
      "collaboration_patterns": {
        "collaboration_score": 0.92,
        "best_partners": ["tester"],
        "communication_style": "efficient",
        "responsiveness": 0.95
      },
      "recent_trend": {
        "direction": "improving",
        "velocity": 0.15,
        "stable_periods": 3
      }
    },
    "tester": {
      "role_id": "role_test_001",
      "role_type": "validation",
      "capabilities": {
        "test_design": 0.90,
        "bug_detection": 0.94,
        "coverage_analysis": 0.85,
        "integration_testing": 0.82
      },
      "performance_history": {
        "total_tests_run": 342,
        "bugs_found": 48,
        "false_positives": 5,
        "bug_detection_rate": 0.94,
        "false_positive_rate": 0.094,
        "avg_test_coverage": 0.87
      },
      "quality_metrics": {
        "precision": 0.91,
        "recall": 0.94,
        "f1_score": 0.925
      }
    },
    "reviewer": {
      "role_id": "role_rev_001",
      "role_type": "validation",
      "capabilities": {
        "code_review": 0.92,
        "security_audit": 0.88,
        "best_practices": 0.90,
        "documentation_review": 0.85
      },
      "performance_history": {
        "total_reviews": 38,
        "critical_issues_found": 12,
        "suggestions_made": 67,
        "avg_review_time": 45
      }
    }
  },
  "team_dynamics": {
    "developer+tester": {
      "collaboration_score": 0.94,
      "avg_handoff_time": 8,
      "success_rate": 0.96
    },
    "tester+reviewer": {
      "collaboration_score": 0.88,
      "avg_handoff_time": 12,
      "success_rate": 0.91
    }
  }
}
```

#### 3. 成功模式库

```json
{
  "version": "1.0.0",
  "patterns": [
    {
      "pattern_id": "success_001",
      "name": "标准开发流程",
      "trigger_fingerprint": {
        "domain": "programming",
        "task_count": 3,
        "has_frontend": true,
        "has_backend": false
      },
      "success_sequence": [
        {
          "step": 1,
          "action": "developer_implements",
          "duration_estimation": 120,
          "prerequisites": []
        },
        {
          "step": 2,
          "action": "tester_validates",
          "duration_estimation": 45,
          "prerequisites": ["step1"]
        },
        {
          "step": 3,
          "action": "reviewer_approves",
          "duration_estimation": 30,
          "prerequisites": ["step2"]
        }
      ],
      "communication_points": [
        {"after": "step1", "type": "handoff", "content": "code_ready_for_test"},
        {"after": "step2", "type": "handoff", "content": "test_results"},
        {"after": "step3", "type": "completion", "content": "approval"}
      ],
      "success_rate": 0.95,
      "occurrence_count": 28
    }
  ]
}
```

#### 4. 错误模式库

```json
{
  "version": "1.0.0",
  "patterns": [
    {
      "pattern_id": "error_001",
      "name": "循环失败模式",
      "symptoms": {
        "test_failure_count": 3,
        "same_file_modified": true,
        "fix_attempts": 3,
        "failure_similarity": 0.85
      },
      "root_cause_hypotheses": [
        {
          "cause": "misunderstood_requirement",
          "probability": 0.6
        },
        {
          "cause": "architectural_issue",
          "probability": 0.3
        },
        {
          "cause": "insufficient_context",
          "probability": 0.1
        }
      ],
      "recommended_recovery": {
        "strategy": "reanalyze_requirement",
        "actions": [
          "pause_development",
          "invoke_researcher",
          "clarify_with_leader",
          "redesign_approach"
        ],
        "success_rate": 0.82
      },
      "occurrence_count": 7,
      "last_seen": 1703900000000
    },
    {
      "pattern_id": "error_002",
      "name": "依赖阻塞模式",
      "symptoms": {
        "blocked_tasks": 2,
        "waiting_time": 120,
        "dependency_not_progressing": true
      },
      "recommended_recovery": {
        "strategy": "break_dependency",
        "actions": [
          "split_task",
          "create_stubs",
          "parallelize"
        ]
      },
      "occurrence_count": 4
    }
  ]
}
```

#### 5. 优化建议库

```json
{
  "version": "1.0.0",
  "suggestions": [
    {
      "suggestion_id": "opt_001",
      "category": "task_allocation",
      "priority": "high",
      "content": "对于文件修改数 < 3 的任务，建议使用 2 人团队而非 3 人",
      "rationale": {
        "analysis": "小任务测试收益递减",
        "data": {
          "avg_time_2_person": 45,
          "avg_time_3_person": 52,
          "savings": "13%"
        }
      },
      "applicable_to": ["programming", "feature_development", "small"],
      "adoption_rate": 0.65,
      "effectiveness": 0.78
    },
    {
      "suggestion_id": "opt_002",
      "category": "communication",
      "priority": "medium",
      "content": "复杂任务（估计时间 > 5分钟）应启用里程碑式通信而非任务边界通信",
      "rationale": {
        "analysis": "复杂任务中间进展监控有价值",
        "data": {
          "early_issue_detection_rate": 0.72
        }
      },
      "applicable_to": ["programming", "medium", "high"],
      "adoption_rate": 0.42
    }
  ]
}
```

#### 6. A/B 测试结果

```json
{
  "version": "1.0.0",
  "experiments": [
    {
      "experiment_id": "ab_exp_001",
      "name": "2人 vs 3人团队效率对比",
      "hypothesis": "小任务使用2人团队更高效",
      "started_at": 1703400000000,
      "status": "completed",
      "variants": {
        "A": {
          "name": "3人团队",
          "configuration": ["developer", "tester", "reviewer"],
          "runs": 10,
          "metrics": {
            "avg_completion_time": 52,
            "success_rate": 0.95,
            "avg_cost": 0.18
          }
        },
        "B": {
          "name": "2人团队",
          "configuration": ["developer", "tester"],
          "runs": 10,
          "metrics": {
            "avg_completion_time": 45,
            "success_rate": 0.92,
            "avg_cost": 0.12
          }
        }
      },
      "conclusion": {
        "winner": "B",
        "confidence": 0.92,
        "improvement": {
          "time_saved": "13.5%",
          "cost_saved": "33.3%"
        }
      }
    },
    {
      "experiment_id": "ab_exp_002",
      "name": "广播 vs 点对点通信",
      "status": "ongoing",
      "variants": {
        "A": {"name": "广播模式", "runs": 5},
        "B": {"name": "点对点模式", "runs": 5}
      }
    }
  ]
}
```

#### 7. 进化日志

```json
{
  "version": "1.0.0",
  "evolution_events": [
    {
      "event_id": "evol_001",
      "timestamp": 1704067200000,
      "type": "pattern_learned",
      "description": "学习到新的任务模式：医学综述撰写",
      "impact": {
        "pattern_id": "pat_med_001",
        "domain": "medical_research",
        "expected_improvement": "faster_initial_setup"
      }

    },
    {
      "event_id": "evol_002",
      "timestamp": 1704000000000,
      "type": "optimization_applied",
      "description": "应用优化建议：小任务使用2人团队",
      "impact": {
        "suggestion_id": "opt_001",
        "tasks_affected": 3,
        "time_saved": 21
      }
    },
    {
      "event_id": "evol_003",
      "timestamp": 1703950000000,
      "type": "ab_test_completed",
      "description": "A/B 测试完成：2人团队对小任务更优",
      "impact": {
        "experiment_id": "ab_exp_001",
        "adoption_rate": 0.8
      }
    }
  ],
  "statistics": {
    "total_evolutions": 3,
    "patterns_learned": 1,
    "optimizations_applied": 1,
    "ab_tests_completed": 1
  }
}
```

---

## 4.3 指标计算器

### 指标体系

```typescript
interface Metrics {
  // 效率指标
  efficiency: {
    total_duration: number;           // 总时长
    task_duration_avg: number;        // 平均任务时长
    task_duration_median: number;      // 中位数任务时长
    parallel_efficiency: number;       // 并行效率 (0-1)
    idle_time_ratio: number;          // 空闲时间占比
  };

  // 质量指标
  quality: {
    success_rate: number;             // 成功率
    error_rate: number;               // 错误率
    retry_rate: number;               // 重试率
    final_accuracy: number;            // 最终准确性
  };

  // 协作指标
  collaboration: {
    total_messages: number;           // 总消息数
    messages_per_task: number;        // 每任务消息数
    broadcast_count: number;           // 广播次数
    handoff_count: number;            // 移交次数
    avg_handoff_time: number;         // 平均移交时间
  };

  // 资源指标
  resource: {
    total_api_calls: number;          // API 调用总数
    api_cost_total: number;           // API 成本
    api_cost_per_task: number;        // 每任务 API 成本
    token_usage: {
      input: number;
      output: number;
      total: number;
    };
  };

  // 复杂度指标
  complexity: {
    task_count: number;               // 任务数量
    role_count: number;               // 角色数量
    dependency_depth: number;          // 依赖深度
    cyclomatic_complexity: number;    // 圈复杂度
  };
}
```

### 基准对比

```typescript
interface Benchmark {
  pattern_id: string;
  current_metrics: Metrics;
  historical_benchmark: Metrics;
  comparison: {
    time_diff: number;                // 时间差异 (%)
    cost_diff: number;                // 成本差异 (%)
    quality_diff: number;              // 质量差异 (%)
    overall_score: number;             // 综合评分 (0-100)
  };
  trend: "improving" | "stable" | "degrading";
}
```

---

## 4.4 版本控制

```typescript
interface KnowledgeVersion {
  version: string;
  created_at: number;
  parent_version?: string;
  changes: {
    added: string[];
    modified: string[];
    removed: string[];
  };
  performance_impact?: {
    before?: Metrics;
    after?: Metrics;
  };
}

interface VersionHistory {
  current_version: string;
  versions: KnowledgeVersion[];
  rollback_points: string[];          // 可回滚的版本
}
```

---

## 实施要点

### 优先级：⭐⭐⭐⭐⭐

### 预估时间：11 小时

| 任务 | 估时 | 依赖 |
|------|------|------|
| 设计数据结构 | 2h | - |
| 实现数据收集器 | 3h | 数据结构 |
| 实现结构化存储 | 3h | 数据结构 |
| 实现指标计算器 | 1h | 数据收集 |
| 实现版本控制 | 2h | 结构化存储 |

### 交付物
- `knowledge/` 目录结构
- 基础数据结构定义
- 运行时数据收集功能

---

[下一章：L1 经验积累层 →](./L1-experience-accumulation.md)

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)
