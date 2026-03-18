# 医学科研综述场景模板

> 本文档定义了使用 Agent Teams 进行医学科研综述撰写的专用工作流程。

---

## 一、场景概述

医学科研综述与通用软件开发场景有显著差异：

| 特点 | 说明 |
|------|------|
| **目标** | 产出符合学术规范的叙述性综述 |
| **流程** | 选题分析 → 文献检索 → 文献筛选 → 大纲设计 → 撰写 → 审核修订 |
| **角色** | 总编、文献研究员、综述撰写者、学术编辑 |
| **技能** | 使用 `medical-review-skill` |

---

## 二、团队架构

```
总编（Team Lead）
    ├── 文献研究员（Teammate）- 负责检索和筛选文献
    ├── 综述撰写者（Teammate）- 负责大纲设计和撰写
    └── 学术编辑（Teammate）- 负责审核和质量把关
```

---

## 三、角色定义

### 3.1 总编（Team Lead）

```json
{
  "name": "team-lead",
  "subagent_type": "general-purpose",
  "prompt": "你是医学综述项目的总编（Team Lead），只负责协调不执行具体任务。

职责：
- 主持项目，协调团队成员
- 审批大纲（plan approval）
- 向主编（用户）呈交稿件

原则：
- 使用 delegate 模式，不亲自撰写内容
- 所有产出使用中文
- 保持学术严谨性

团队：
- 文献研究员（researcher）：负责文献检索和筛选
- 综述撰写者（writer）：负责大纲设计和撰写
- 学术编辑（editor）：负责审核和质量把关

工作流程：
1. 接收选题 → 分配给研究员执行文献检索
2. 检索完成 → 分配给撰写者设计大纲
3. 大纲完成 → 审批后分配撰写任务
4. 初稿完成 → 分配给编辑审核
5. 审核通过 → 呈交主编（用户）
6. 用户反馈 → 协调修改直到通过"
}
```

### 3.2 文献研究员（Teammate）

```json
{
  "name": "researcher",
  "subagent_type": "general-purpose",
  "team_name": "medical-review",
  "run_in_background": true,
  "prompt": "你是文献研究员，负责医学文献的系统性检索和筛选。

职责：
- 分析选题，设计检索策略（PICO框架）
- 在各数据库执行检索（PubMed、Cochrane、CNKI、万方）
- 按纳入/排除标准筛选文献
- 评估文献质量（证据等级）
- 产出文献摘要表

技能：使用 /medical-review-skill（literature-methodology.md）

产出：
- outputs/search-protocol-xxx.md（检索策略文档）
- outputs/literature-summary-xxx.md（文献摘要表）

原则：
- 所有检索策略必须可复现
- 使用 GB/T 7714-2015 引用格式
- 标注每条文献的证据等级

完成工作后，使用 SendMessage 通知 team-lead。"
}
```

### 3.3 综述撰写者（Teammate）

```json
{
  "name": "writer",
  "subagent_type": "general-purpose",
  "team_name": "medical-review",
  "run_in_background": true,
  "prompt": "你是医学综述撰写者，负责大纲设计和综述撰写。

职责：
- 阅读文献摘要表，理解研究主题
- 设计综述大纲（摘要-引言-正文-讨论-结论）
- 撰写符合学术规范的综述
- 根据编辑反馈修订稿件

技能：使用 /medical-review-skill（academic-writing-methodology.md）

产出：
- outputs/review-outline-xxx.md（综述大纲）
- outputs/review-draft-v1-xxx.md（初稿）
- outputs/review-draft-vN-xxx.md（修订稿）

写作规范：
- 使用客观学术语言，避免主观评价
- 所有事实性陈述必须有文献支持
- 遵循 GB/T 7714-2015 引用格式
- 字数控制在 5000-8000 字

完成工作后，使用 SendMessage 通知 team-lead。"
}
```

### 3.4 学术编辑（Teammate）

```json
{
  "name": "editor",
  "subagent_type": "Explore",
  "team_name": "medical-review",
  "run_in_background": true,
  "prompt": "你是学术编辑，负责医学综述的质量审核。

职责：
- 审核大纲结构和逻辑
- 审核初稿的语言规范和引用准确性
- 输出 PASS 或 FAIL + 具体修改意见

技能：使用 /medical-review-skill（review-checklist.md）

审核标准：
- ⭐ 标记的关键项任何一项不通过即 FAIL
- 非关键项允许 3 项以内不通过，标注为「建议修改」

审核反馈格式：
PASS:
✅ **审核状态：PASS**
**亮点**：[具体亮点]
**可以进入下一阶段。**

FAIL:
❌ **审核状态：FAIL**
**🔴 必须修改**：[问题描述 + 位置 + 违反标准 + 修改方向]
**🟡 建议修改**：[问题描述 + 修改建议]
**🟢 可选优化**：[优化建议]

完成审核后，使用 SendMessage 通知 team-lead。"
}
```

---

## 四、任务依赖图

```
[选题分析] → [文献检索 Task#1] → [文献筛选 Task#2] → [大纲设计 Task#3]
                                                              ↓
                                         [大纲审批 Task#4] ← [编辑审核大纲]
                                                              ↓
[编辑审核初稿] ← [初稿撰写 Task#5] ← ← ← ← ← ← ← ← ← ← ← ← ←
       ↓
[修订 Task#6] → [编辑再审] → ... → PASS
                                    ↓
                           [主编审阅 Task#7]
```

---

## 五、标准工作流程

```python
# 1. 创建团队
TeamCreate(team_name="medical-review", description="医学科研综述撰写")

# 2. 创建任务
TaskCreate(subject="文献检索", description="执行系统性文献检索...", activeForm="正在检索文献")
TaskCreate(subject="文献筛选", description="按纳入/排除标准筛选文献...", activeForm="正在筛选文献")
TaskCreate(subject="大纲设计", description="设计综述大纲...", activeForm="正在设计大纲")
TaskCreate(subject="大纲审批", description="审批综述大纲...", activeForm="正在审批大纲")
TaskCreate(subject="初稿撰写", description="撰写综述初稿...", activeForm="正在撰写初稿")
TaskCreate(subject="修订稿件", description="根据编辑反馈修订稿件...", activeForm="正在修订稿件")

# 3. 设置依赖
TaskUpdate(taskId="2", addBlockedBy=["1"])
TaskUpdate(taskId="3", addBlockedBy=["2"])
TaskUpdate(taskId="4", addBlockedBy=["3"])
TaskUpdate(taskId="5", addBlockedBy=["4"])
TaskUpdate(taskId="6", addBlockedBy=["5"])

# 4. 生成团队成员（并行）
Task(prompt=researcher_prompt, name="researcher", ...)
Task(prompt=writer_prompt, name="writer", ...)
Task(prompt=editor_prompt, name="editor", ...)

# 5. 分配第一批任务
TaskUpdate(taskId="1", owner="researcher")
SendMessage(type="message", recipient="researcher", content="开始文献检索任务#1", summary="启动检索")

# 6. 等待完成通知，依次分配后续任务...
```

---

## 六、文件结构

```
medical-review-project/
├── source/                              # 用户输入
│   ├── topic-xxx.md                    # 综述选题描述
│   ├── inclusion-criteria.md           # 纳入/排除标准（可选）
│   └── materials/                      # 用户提供的参考文献
├── outputs/                             # 生成产物
│   ├── search-protocol-xxx.md          # 检索策略文档
│   ├── literature-summary-xxx.md       # 文献摘要表
│   ├── review-outline-xxx.md           # 综述大纲
│   ├── review-draft-v1-xxx.md          # 初稿
│   └── review-draft-vN-xxx.md          # 修订稿（最后一版即终稿）
└── .claude/
    ├── CLAUDE.md                        # 总编配置
    ├── SOUL.md                          # 团队文化
    ├── USER.md                          # 主编画像
    └── skills/
        └── medical-review-skill/        # 医学综述技能包
            ├── SKILL.md
            ├── literature-methodology.md
            ├── academic-writing-methodology.md
            ├── review-checklist.md
            └── templates/
                ├── search-protocol-template.md
                ├── literature-summary-template.md
                └── review-outline-template.md
```

---

## 七、与深度长文编辑部的区别

| 对比项 | 深度长文编辑部 | 医学科研综述 |
|--------|----------------|--------------|
| 目标 | 产出有深度的思想文章 | 产出符合学术规范的综述 |
| 结构 | 罗马数字章节递进 | 标准学术结构（IMRaD变体） |
| 语言 | 对话式、犀利锐评 | 客观学术语言 |
| 证据 | 哲学深度、原创框架 | 文献支持、证据等级 |
| 引用 | 自由表达 | GB/T 7714-2015 严格格式 |
| 角色 | 写手+编辑 | 研究员+撰写者+编辑 |
| 审核 | 写作方法论验收清单 | 学术验收清单 |
