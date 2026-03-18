# 上下文感知系统

> Agent Teams 自进化架构的上下文感知层

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)

---

## 概述

上下文感知系统使 Agent Teams 能够根据不同上下文做出更好的决策，包括：
- 项目上下文
- 会话上下文
- 任务上下文
- 环境上下文

---

## 上下文定义

```typescript
interface ContextAwareness {
  // 项目上下文
  project: ProjectContext;

  // 会话上下文
  session: SessionContext;

  // 任务上下文
  task: TaskContext;

  // 环境上下文
  environment: EnvironmentContext;
}

interface ProjectContext {
  project_id: string;
  name: string;

  // 项目类型
  type: ProjectType;

  // 技术栈
  tech_stack: string[];

  // 项目规模
  scale: {
    total_files: number;
    total_lines: number;
    modules: number;
  };

  // 项目历史
  history: {
    previous_tasks: TaskSummary[];
    common_patterns: string[];
    pain_points: string[];
  };

  // 项目约束
  constraints: {
    deadlines?: Date[];
    resource_limits?: ResourceLimits;
    quality_requirements?: QualityRequirements;
  };
}

interface SessionContext {
  session_id: string;
  start_time: number;

  // 会话目标
  goals: string[];

  // 进度
  progress: {
    completed_tasks: number;
    total_tasks: number;
    percentage: number;
  };

  // 会话状态
  state: "planning" | "executing" | "reviewing" | "completed";

  // 会话历史
  events: RuntimeEvent[];
}

interface TaskContext {
  task_id: string;
  task_type: string;

  // 依赖任务
  dependencies: string[];

  // 相关文件
  related_files: string[];

  // 任务约束
  constraints: {
    max_duration?: number;
    max_cost?: number;
    quality_threshold?: number;
  };
}

interface EnvironmentContext {
  // 计算资源
  resources: {
    cpu_available: number;
    memory_available: number;
    bandwidth: number;
  };

  // 时间
  time: {
    current: number;
    timezone: string;
    business_hours: boolean;
  };

  // 用户偏好
  preferences: {
    communication_style: "concise" | "detailed" | "balanced";
    feedback_frequency: "immediate" | "batch" | "milestone";
    error_handling: "strict" | "lenient" | "adaptive";
  };
}
```

---

## 上下文感知决策

```typescript
interface ContextAwareDecision {
  // 基于上下文的角色选择
  selectRoles(
    task_type: string,
    context: ContextAwareness
  ): RoleSelectionResult;

  // 基于上下文的任务分解
  decomposeTask(
    task_description: string,
    context: ContextAwareness
  ): TaskDecomposition;

  // 基于上下文的优先级调整
  adjustPriorities(
    tasks: Task[],
    context: ContextAwareness
  ): PrioritizedTasks;
}

interface RoleSelectionResult {
  roles: string[];
  reasoning: string[];
  confidence: number;
}

interface TaskDecomposition {
  subtasks: Subtask[];
  dependencies: TaskDependency[];
  estimated_duration: number;
}

interface PrioritizedTasks {
  tasks: PrioritizedTask[];
}

interface PrioritizedTask {
  task_id: string;
  priority: number;
  reason: string;
}
```

---

## 项目类型检测

```typescript
interface ProjectTypeDetector {
  detectProjectType(
    project_root: string
  ): ProjectDetectionResult;
}

interface ProjectDetectionResult {
  project_type: ProjectType;
  confidence: number;

  indicators: {
    package_managers: string[];
    config_files: string[];
    directory_structure: string[];
    file_patterns: string[];
  };

  recommendations: {
    roles: string[];
    tools: string[];
    practices: string[];
  };
}

type ProjectType =
  | "web_frontend"
  | "web_backend"
  | "fullstack"
  | "mobile_app"
  | "desktop_app"
  | "cli_tool"
  | "data_science"
  | "ml_project"
  | "medical_research"
  | "scientific_computing"
  | "library"
  | "monorepo"
  | "unknown";
```

---

## 实施要点

### 优先级：⭐⭐⭐

### 预估时间：6 小时

| 任务 | 估时 | 依赖 |
|------|------|------|
| 实现项目类型检测 | 2h | - |
| 实现上下文收集器 | 1h | - |
| 实现上下文感知决策 | 2h | L1 |
| 集成到任务分配 | 1h | L2, L4 |

### 交付物
- 项目类型自动识别
- 上下文驱动的决策

---

[上一章：领域扩展架构](./domain-extension.md) | [下一章：资源感知与优化 →](./resource-optimization.md)

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)
