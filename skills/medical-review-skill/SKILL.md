---
name: medical-review-skill
description: "Use this skill whenever the user wants to write a medical review, conduct literature search, perform systematic review, or do evidence synthesis. Triggers include: any mention of '医学综述' (medical review), '文献检索' (literature search), '系统评价' (systematic review), 'Meta分析' (meta-analysis), 'PRISMA流程' (PRISMA workflow), '文献筛选' (literature screening), '证据综合' (evidence synthesis), 'Nature Reviews', '叙述性综述' (narrative review), or 'PubMed检索' (PubMed search)."
---

# 医学科研综述撰写技能
> **版本**: 2.6.1 | **最后更新**: 2026-03-13

## 快速开始

### 综述类型说明

本技能支持**高水平综合综述**（参照 Nature Reviews Disease Primers 标准）：
- **结构**: 固定8章框架
- **方法学**: 借鉴 PRISMA 进行系统性文献检索和筛选
- **证据整合**: 全面的文献覆盖和证据分级
- **专家观点**: 允许基于证据的专家解读和临床洞察

## 工作流程（九步骤）

| 步骤 | 子技能 | 功能 |
|------|--------|------|
| STEP -1 | review-worldview | 综述世界观四层对齐 |
| STEP 0 | review-novelty-gate | 综述价值评估与Go/No-Go决策 |
| STEP 1 | literature-search | 文献检索策略设计与执行 |
| STEP 2 | literature-screening | 文献筛选与质量评估 |
| STEP 3-4 | evidence-synthesis | 证据综合与Synthesis Leap |
| STEP 5 | review-outline | 综述大纲设计 |
| STEP 6-7 | review-writing | 综述撰写 |
| STEP 8 | review-checklist | 投稿前检查 |
| STEP 9 | cognitive-manager | 认知调度员 |

## 核心特性 (v2.6.x)

### 1. Adversarial Synthesis（对抗式综合）
AI扮演Nature Reviews审稿人，针对生成的机制图提出3个反直觉临床病例。

### 2. Technological Obsolescence Factor（技术过时系数）
- 指南4年半衰期计算
- 范式转移检测
- 过时指南 vs 革命性证据的冲突分级

### 3. EnhancedNumericEngine（增强型数值识别引擎）
- 自动区分 SD/SE/CI/IQR
- 算子持久化
- 自动尺度对齐

### 4. Cochrane RoB 2.0 BiasAssessor
- D1-D5全领域偏倚风险评估
- 自动GRADE降级映射

## 项目结构规范

```
project/
├── 00_参考资料/
├── 01_文献库/
├── 02_解析数据/
├── 03_知识图谱/
├── 04_综述草稿/
├── 05_提交材料/
└── workflow_runs/
```

## 核心原则

- **科学性**: 所有论述必须有文献支持
- **客观性**: 呈现证据而非观点
- **准确性**: 引用必须准确反映原文
- **规范性**: 遵循学术写作格式
- **透明性**: 公开每条观点的 Evidence Audit Trail
- **学术诚信**: AI作为合作者，而非替代者

## 与其他技能的关系

复杂综述项目可使用 **Agent Teams**：
- researcher agent：负责文献检索和解析
- writer agent：负责章节撰写
- editor agent：负责审核修订

详见: `agent-teams-guide` skill
