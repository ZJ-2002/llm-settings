# 领域扩展架构

> Agent Teams 自进化架构的领域支持系统

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)

---

## 概述

领域扩展架构使 Agent Teams 能够支持多种领域，包括：
- 领域定义框架
- 角色定义模板
- 工作流模板
- 领域知识加载

---

## 领域知识系统

### 领域定义

```typescript
interface DomainDefinition {
  domain_id: string;
  name: string;
  version: string;

  // 角色定义
  roles: DomainRole[];

  // 任务类型
  task_types: DomainTaskType[];

  // 工作流模板
  workflow_templates: WorkflowTemplate[];

  // 领域特定规则
  rules: DomainRule[];

  // 领域知识
  knowledge: DomainKnowledge;
}
```

### 角色定义模板

```typescript
interface DomainRole {
  role_id: string;
  name: string;
  display_name: string;

  // 能力
  capabilities: CapabilityVector;

  // Agent 配置
  agent_config: {
    subagent_type: "general-purpose" | "Explore" | "Plan" | "Bash";
    model_preference?: string;
  };

  // Prompt 模板
  prompt_template: string;

  // 任务偏好
  preferred_tasks: string[];
  avoided_tasks: string[];
}
```

### 领域映射

```json
{
  "version": "1.0.0",
  "domains": {
    "programming": {
      "domain_id": "prog_001",
      "name": "Programming",
      "keywords": ["code", "implement", "develop", "api", "function"],
      "default_roles": ["developer", "tester", "reviewer"],
      "file_extensions": [".ts", ".js", ".py", ".java", ".go", ".rs"]
    },
    "medical_research": {
      "domain_id": "med_001",
      "name": "Medical Research",
      "keywords": ["medical", "research", "review", "literature", "clinical"],
      "default_roles": [
        "medical-researcher",
        "medical-writer",
        "medical-reviewer"
      ],
      "file_extensions": [".md", ".pdf", ".docx", ".bib"]
    },
    "data_analysis": {
      "domain_id": "data_001",
      "name": "Data Analysis",
      "keywords": ["data", "analyze", "visualize", "statistics", "ml"],
      "default_roles": ["data-analyst", "data-scientist", "visualizer"],
      "file_extensions": [".csv", ".json", ".xlsx", ".parquet"]
    }
  }
}
```

---

## 医学科研角色定义

```json
{
  "domain": "medical_research",
  "roles": [
    {
      "role_id": "med_res_001",
      "name": "medical-researcher",
      "display_name": "医学研究员",
      "description": "负责医学文献检索、数据收集和分析",

      "agent_config": {
        "subagent_type": "general-purpose"
      },

      "capabilities": {
        "literature_search": 0.95,
        "data_collection": 0.90,
        "data_analysis": 0.85,
        "citation_management": 0.88,
        "critical_appraisal": 0.82
      },

      "prompt_template": "你是团队中的医学研究员。\n\n## 你的职责\n进行医学文献检索、收集研究数据、分析医学证据。\n\n## 工作流程\n1. 使用 TaskList 查看分配给你的任务\n2. 调用 TaskGet 读取任务详情\n3. 执行医学文献检索（使用 PubMed、Google Scholar 等）\n4. 收集和分析数据\n5. 管理引用和文献\n6. 调用 SendMessage 向 team-lead 汇报结果\n\n## 沟通规则\n- 完成任务后必须用 SendMessage 通知 team-lead\n- 遇到问题时向 team-lead 求助\n- 不要使用 broadcast",

      "preferred_tasks": [
        "literature_review",
        "data_collection",
        "evidence_analysis"
      ]
    },
    {
      "role_id": "med_wri_001",
      "name": "medical-writer",
      "display_name": "医学论文撰写员",
      "description": "负责医学论文、综述的撰写",

      "agent_config": {
        "subagent_type": "general-purpose"
      },

      "capabilities": {
        "scientific_writing": 0.92,
        "structure_organization": 0.90,
        "language_refinement": 0.88,
        "formatting": 0.85,
        "plagiarism_check": 0.80
      },

      "prompt_template": "你是团队中的医学论文撰写员。\n\n## 你的职责\n根据研究结果撰写高质量的医学论文、综述。\n\n## 工作流程\n1. 调用 TaskGet 读取任务详情\n2. 分析研究资料和数据\n3. 按照医学论文规范组织结构（IMRaD）\n4. 撰写内容，确保学术严谨性\n5. 管理参考文献\n6. 调用 SendMessage 向 team-lead 汇报完成情况\n\n## 写作规范\n- 遵循 CONSORT、PRISMA 等报告指南\n- 使用专业的医学学术语言\n- 确保逻辑清晰、论证严密\n- 准确引用文献",

      "preferred_tasks": [
        "paper_drafting",
        "review_writing",
        "abstract_writing"
      ]
    },
    {
      "role_id": "med_rev_001",
      "name": "medical-reviewer",
      "display_name": "医学内容审查员",
      "description": "负责医学内容的审查和质量把关",

      "agent_config": {
        "subagent_type": "Explore"
      },

      "capabilities": {
        "content_review": 0.90,
        "accuracy_check": 0.88,
        "ethical_review": 0.85,
        "peer_review": 0.83,
        "methodology_check": 0.85
      },

      "prompt_template": "你是团队中的医学内容审查员。\n\n## 你的职责\n审查医学论文和综述的质量、准确性和学术规范性。\n\n## 审查要点\n1. 科学准确性\n2. 方法论的严谨性\n3. 数据和结论的一致性\n4. 引用的准确性\n5. 伦理合规性\n6. 写作规范性\n\n## 工作流程\n1. 调用 TaskGet 读取任务详情\n2. 阅读需要审查的内容\n3. 按照审查要点逐项检查\n4. 撰写审查报告\n5. 调用 SendMessage 向 team-lead 汇报审查结果\n\n## 审查报告格式\n在 SendMessage 中包含：\n- 审查范围\n- 发现的问题（按严重程度分类）\n- 改进建议\n- 总体评价"
    },
    {
      "role_id": "med_ill_001",
      "name": "medical-illustrator",
      "display_name": "医学绘图员",
      "description": "负责医学科研绘图的制作",

      "agent_config": {
        "subagent_type": "general-purpose"
      },

      "capabilities": {
        "figure_creation": 0.90,
        "data_visualization": 0.88,
        "scientific_illustration": 0.85,
        "format_compliance": 0.82
      },

      "prompt_template": "你是团队中的医学绘图员。\n\n## 你的职责\n制作高质量的医学科研插图、数据可视化图表。\n\n## 绘图规范\n- 遵循期刊的插图指南\n- 图表清晰、专业\n- 数据准确标注\n- 色彩设计符合色盲友好原则\n- 图例完整\n\n## 支持的工具\n- Python (matplotlib, seaborn, plotly)\n- R (ggplot2)\n- 专业的科学绘图软件\n\n## 工作流程\n1. 调用 TaskGet 读取任务详情\n2. 理解数据和可视化需求\n3. 选择合适的绘图方法和工具\n4. 生成图表\n5. 调整样式以满足期刊要求\n6. 调用 SendMessage 向 team-lead 汇报完成情况"
    }
  ]
}
```

---

## 医学工作流模板

```json
{
  "domain": "medical_research",
  "workflow_templates": [
    {
      "template_id": "med_wf_001",
      "name": "系统综述撰写工作流",
      "description": "适用于撰写系统综述的标准工作流",

      "phases": [
        {
          "phase_id": "planning",
          "name": "规划阶段",
          "roles": ["team-lead"],
          "tasks": ["define_research_question", "design_protocol"]
        },
        {
          "phase_id": "search",
          "name": "文献检索阶段",
          "roles": ["medical-researcher"],
          "tasks": ["literature_search", "screening", "full_text_retrieval"],
          "parallel": true
        },
        {
          "phase_id": "analysis",
          "name": "分析阶段",
          "roles": ["medical-researcher"],
          "tasks": ["data_extraction", "quality_assessment", "data_analysis"]
        },
        {
          "phase_id": "writing",
          "name": "撰写阶段",
          "roles": ["medical-writer"],
          "tasks": ["synthesis", "drafting", "formatting"]
        },
        {
          "phase_id": "review",
          "name": "审查阶段",
          "roles": ["medical-reviewer"],
          "tasks": ["content_review", "accuracy_check"]
        },
        {
          "phase_id": "figures",
          "name": "绘图阶段",
          "roles": ["medical-illustrator"],
          "tasks": ["figure_creation"],
          "parallel_to": "writing"
        }
      ],

      "transitions": [
        {"from": "planning", "to": "search"},
        {"from": "search", "to": "analysis"},
        {"from": "analysis", "to": "writing"},
        {"from": "writing", "to": "review"},
        {"from": "figures", "to": "review"}
      ],

      "communication_points": [
        {
          "point_id": "cp_001",
          "phase": "search",
          "trigger": "completion",
          "type": "handoff",
          "recipient": "team-lead"
        },
        {
          "point_id": "cp_002",
          "phase": "analysis",
          "trigger": "milestone",
          "condition": "every_5_records",
          "type": "update",
          "recipient": "team-lead"
        }
      ]
    },
    {
      "template_id": "med_wf_002",
      "name": "原创研究论文撰写工作流",
      "description": "适用于撰写原创研究论文的工作流",

      "phases": [
        {
          "phase_id": "planning",
          "name": "规划阶段",
          "roles": ["team-lead"],
          "tasks": ["study_design"]
        },
        {
          "phase_id": "data_preparation",
          "name": "数据准备阶段",
          "roles": ["medical-researcher"],
          "tasks": ["data_collection", "data_cleaning", "statistical_analysis"]
        },
        {
          "phase_id": "writing",
          "name": "撰写阶段",
          "roles": ["medical-writer"],
          "tasks": ["abstract", "introduction", "methods", "results", "discussion", "conclusion"]
        },
        {
          "phase_id": "figures",
          "name": "绘图阶段",
          "roles": ["medical-illustrator"],
          "tasks": ["create_figures", "create_tables"]
        },
        {
          "phase_id": "review",
          "name": "审查阶段",
          "roles": ["medical-reviewer"],
          "tasks": ["comprehensive_review"]
        }
      ]
    }
  ]
}
```

---

## 领域知识加载器

```typescript
interface DomainKnowledgeLoader {
  // 加载领域定义
  loadDomain(domain_id: string): DomainDefinition;

  // 自动检测领域
  detectDomain(task_description: string): DomainDetectionResult;

  // 获取领域角色
  getDomainRoles(domain_id: string): DomainRole[];

  // 获取工作流模板
  getWorkflowTemplate(
    domain_id: string,
    template_id: string
  ): WorkflowTemplate;
}

interface DomainDetectionResult {
  detected: boolean;
  domain_id?: string;
  confidence: number;
  indicators: string[];
}
```

---

## 实施要点

### 优先级：⭐⭐⭐⭐

### 预估时间：7 小时

| 任务 | 估时 | 依赖 |
|------|------|------|
| 设计领域定义框架 | 1h | - |
| 实现医学领域角色 | 2h | 领域框架 |
| 实现医学工作流模板 | 2h | 医学角色 |
| 实现领域加载器 | 1h | 领域框架 |
| 集成到主入口 | 1h | L1 |

### 交付物
- `domain-knowledge/` 结构
- 医学科研角色和工作流
- 自动领域检测

---

[上一章：L3 策略进化层](./L3-strategy-evolution.md) | [下一章：上下文感知系统 →](./context-awareness.md)

[返回主目录](./README.md) | [返回主文档](../evolution-architecture.md)
