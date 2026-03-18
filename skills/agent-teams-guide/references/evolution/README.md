# Agent Teams 自进化架构 - 文档索引

> 本目录包含 Agent Teams 自进化系统的详细技术文档

[返回主文档](../evolution-architecture.md)

---

## 文档导航

### 核心架构层

| 文档 | 描述 | 关键内容 |
|------|------|----------|
| [L0-data-infrastructure.md](./L0-data-infrastructure.md) | 数据基础设施层 | 数据收集、结构化存储、指标计算、版本控制 |
| [L1-experience-accumulation.md](./L1-experience-accumulation.md) | 经验积累层 | 任务指纹识别、成员能力建模、模式匹配、经验索引 |
| [L2-behavior-adaptation.md](./L2-behavior-adaptation.md) | 行为适应层 | 自适应分配、自适应通信、依赖优化 |
| [L3-strategy-evolution.md](./L3-strategy-evolution.md) | 策略进化层 | 模式发现、策略生成、优化器、A/B 测试 |

### 交叉功能层

| 文档 | 描述 | 关键内容 |
|------|------|----------|
| [domain-extension.md](./domain-extension.md) | 领域扩展架构 | 领域定义、角色模板、工作流模板、领域加载 |
| [context-awareness.md](./context-awareness.md) | 上下文感知系统 | 项目上下文、会话上下文、上下文感知决策 |
| [resource-optimization.md](./resource-optimization.md) | 资源感知与优化 | 资源监控、成本优化、时间优化 |
| [security-recovery.md](./security-recovery.md) | 安全与恢复机制 | 安全检查、恢复机制、错误处理策略 |

### 实施文档

| 文档 | 描述 | 关键内容 |
|------|------|----------|
| [implementation-roadmap.md](./implementation-roadmap.md) | 实现路线图 | Phase 0-10 分阶段实施计划 |
| [risk-assessment.md](./risk-assessment.md) | 风险评估 | 技术风险、运行风险、使用风险及缓解措施 |

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     L3: 策略进化层                    │
│  模式发现引擎  │  策略生成器  │  优化器                       │
├─────────────────────────────────────────────────────────────────┤
│                     L2: 行为适应层                    │
│  自适应分配器  │  自适应通信  │  依赖优化器                   │
├─────────────────────────────────────────────────────────────────┤
│                     L1: 经验积累层                  │
│  任务指纹识别  │  成员能力建模  │  模式匹配器  │  经验索引器   │
├─────────────────────────────────────────────────────────────────┤
│                     L0: 数据基础设施层                  │
│  数据收集器  │  结构化存储  │  指标计算器  │  版本控制        │
└─────────────────────────────────────────────────────────────────┘

                交叉功能层 (Cross-Functional Layers)
┌─────────────────────────────────────────────────────────────────┐
│  领域扩展层      │  上下文感知层      │  资源优化层        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 了解架构
阅读 [主文档](../evolution-architecture.md) 获取整体概览

### 2. 实施顺序
推荐按以下顺序实施：
1. **Phase 0**: [L0 数据基础设施](./L0-data-infrastructure.md)
2. **Phase 1**: [L1 经验积累层](./L1-experience-accumulation.md)
3. **Phase 2**: [L2 行为适应层](./L2-behavior-adaptation.md)
4. **Phase 3**: [领域扩展](./domain-extension.md)
5. **Phase 4-10**: 按需实施其他功能

### 3. 查看路线图
详细的实施计划请参考 [implementation-roadmap.md](./implementation-roadmap.md)

---

## 核心概念

| 概念 | 说明 | 相关文档 |
|------|------|----------|
| 任务指纹 | 基于任务描述生成的特征向量 | L1-experience-accumulation.md |
| 能力建模 | 对角色能力进行量化建模 | L1-experience-accumulation.md |
| 模式匹配 | 匹配历史成功/失败模式 | L1-experience-accumulation.md |
| 自适应分配 | 基于历史数据动态分配任务 | L2-behavior-adaptation.md |
| 策略进化 | 自动发现和优化协作模式 | L3-strategy-evolution.md |
| 领域扩展 | 支持多领域协作 | domain-extension.md |

---

## 数据结构位置

所有数据存储在 `~/.claude/skills/agent-teams/knowledge/` 目录：

```
knowledge/
├── base/                    # 基础数据
│   ├── task-patterns.json   # 任务模式库
│   ├── role-performance.json # 角色表现数据
│   └── domain-knowledge/    # 领域知识
├── history/                 # 历史数据
│   ├── sessions/           # 会话历史
│   └── metrics/            # 历史指标
├── learned/                 # 学习成果
│   ├── success-patterns.json
│   ├── error-patterns.json
│   └── optimization-hints.json
├── cache/                   # 运行时缓存
└── config/                  # 配置文件
```

---

**文档版本**: 1.0.0  
**最后更新**: 2026-03-03
