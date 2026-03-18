# Medical Review Skill 示例

本目录包含 medical-review-skill 的使用示例，帮助用户理解如何正确使用该技能撰写医学综述。

## 示例项目

### 1. medical-review-project/ - 2型糖尿病运动干预综述

一个完整的综述项目示例，展示从选题到投稿前检查的完整流程。

**目录结构**:
```
medical-review-project/
├── source/
│   ├── topic-example.md          # 综述选题描述（起点）
│   ├── 01-worldview-card.md      # STEP -1 输出：世界观对齐
│   ├── 02-novelty-assessment.md  # STEP 0 输出：价值评估
│   ├── 03-search-protocol.md     # STEP 1 输出：检索策略
│   ├── 04-screening-results.md   # STEP 2 输出：筛选结果
│   ├── 05-evidence-map.md        # STEP 3-4 输出：知识图谱
│   ├── 06-review-outline.md      # STEP 5 输出：综述大纲
│   ├── 07-review-draft.md        # STEP 6-7 输出：综述初稿
│   └── 08-final-check.md         # STEP 8 输出：投稿前检查
├── outputs/                      # 生成的最终文件
└── .claude/                      # Claude 配置（可选）
```

## 使用流程示例

### 示例 1: 从零开始撰写综述

```
用户: 我要写一篇关于"2型糖尿病运动干预"的医学综述

Claude: 我将使用 medical-review-skill 协助您完成这篇综述。让我们开始第一步...

[执行 STEP -1: review-worldview]
→ 生成 01-worldview-card.md

[执行 STEP 0: review-novelty-gate]
→ 生成 02-novelty-assessment.md

...继续后续步骤...
```

### 示例 2: 已有选题，需要完善

```
用户: 我已经有了综述选题，帮我进行世界观对齐

Claude: 请提供您的综述选题描述，我将使用 review-worldview 子技能进行分析。

用户: [提供 topic.md]

Claude: [执行 worldview 分析]
→ 生成 worldview-card.md
```

### 示例 3: 直接调用子技能

```
用户: 帮我设计文献检索策略

Claude: 使用 /literature-search 子技能
→ 生成 search-protocol.md
```

## 各步骤输入输出示例

| 步骤 | 命令/触发词 | 输入 | 输出 |
|------|-------------|------|------|
| STEP -1 | 世界观对齐 / worldview | 综述选题描述 | worldview-card.md |
| STEP 0 | 价值评估 / novelty-gate | worldview-card.md | novelty-assessment.md |
| STEP 1 | 文献检索 / literature-search | PICO要素 | search-protocol.md |
| STEP 2 | 文献筛选 / screening | 检索结果 | screening-results.md |
| STEP 3-4 | 证据综合 / synthesis | 筛选后文献 | evidence-map.md |
| STEP 5 | 大纲设计 / outline | evidence-map.md | review-outline.md |
| STEP 6-7 | 撰写 / writing | review-outline.md | review-draft.md |
| STEP 8 | 检查 / checklist | review-draft.md | final-check.md |

## 快速开始

1. 复制 `medical-review-project/` 模板
2. 修改 `source/topic-example.md` 为您的综述选题
3. 让 Claude 使用 medical-review-skill 开始撰写

## 注意事项

- 每个步骤必须通过才能进入下一步（硬门控）
- 所有输出文件保存在 `workflow_runs/<run-id>/` 目录
- 引用溯源机制要求每个观点都标注来源
