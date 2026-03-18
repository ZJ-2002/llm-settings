---
name: literature-methodology
description: 医学文献检索方法论。为叙述性综述提供系统性的文献检索策略设计、执行和质量控制指导。
---

# 医学文献检索方法论

本文件指导如何为医学科研综述进行系统性文献检索。叙述性综述虽然不像系统综述那样需要严格的PRISMA流程，但仍需要科学、可复现的检索策略。

---

## 第一部分：选题分析

[研究问题结构化：PICO框架]
    将选题转化为可检索的研究问题：

    - P (Population/Patient)：目标人群/疾病
    - I (Intervention/Exposure)：干预措施/暴露因素
    - C (Comparison)：对照组/比较因素（可选）
    - O (Outcome)：结局指标

    示例：
    选题：「糖尿病患者的运动干预研究进展」
    P: 糖尿病患者（2型糖尿病为主）
    I: 运动干预（有氧运动、抗阻运动、混合运动）
    C: 常规护理/无干预
    O: 血糖控制、并发症、生活质量

[检索范围确定]
    - 时间范围：通常近5-10年，经典文献可扩展
    - 语言范围：中英文为主，必要时纳入其他语种
    - 研究类型：叙述性综述通常纳入各类研究（RCT、队列、病例对照、病例报告等）
    - 证据等级：明确各级证据的权重

---

## 第二部分：数据库选择

[主要数据库]

    | 数据库 | 适用领域 | 特点 |
    |--------|----------|------|
    | PubMed/MEDLINE | 生物医学 | 最全面的生物医学文献库 |
    | Cochrane Library | 循证医学 | 高质量系统综述和RCT |
    | Embase | 药学、欧洲文献 | 药物研究文献丰富 |
    | Web of Science | 综合性 | 引文索引，追踪文献脉络 |
    | CNKI | 中文文献 | 国内期刊全文 |
    | 万方数据 | 中文文献 | 学位论文、会议论文 |
    | 维普 | 中文文献 | 中文生物医学期刊 |

[数据库组合策略]
    叙述性综述推荐组合：
    - 国际文献：PubMed + Cochrane Library（+ Embase如涉及药物）
    - 中文文献：CNKI + 万方
    - 补充检索：Web of Science（追踪引文）

---

## 第三部分：检索策略设计

[关键词选择]

    1. 主题词检索（MeSH/关键词）
       - 在PubMed使用MeSH词
       - 在CNKI使用主题词

    2. 自由词检索
       - 同义词、近义词、变体
       - 英文需考虑英式/美式拼写
       - 中文需考虑术语变体

    3. 组合策略
       - P、I、O分别构建检索式
       - 使用布尔逻辑组合

[布尔逻辑运算]

    AND：缩小范围（P AND I）
        "diabetes mellitus, type 2"[MeSH] AND "exercise"[MeSH]

    OR：扩大范围（同义词）
        "exercise therapy"[MeSH] OR "physical activity"[Title/Abstract]

    NOT：排除干扰（慎用）
        "diabetes mellitus, type 2"[MeSH] NOT "type 1"[Title/Abstract]

[检索式构建示例]

    PubMed检索式（糖尿病运动干预）：
    ```
    # Population
    ("diabetes mellitus, type 2"[MeSH Terms] OR "type 2 diabetes"[Title/Abstract] OR "T2DM"[Title/Abstract])

    # Intervention
    AND ("exercise"[MeSH Terms] OR "exercise therapy"[MeSH Terms] OR "physical activity"[Title/Abstract] OR "aerobic exercise"[Title/Abstract] OR "resistance training"[Title/Abstract])

    # Filters
    AND ("2014/01/01"[Date - Publication] : "3000"[Date - Publication])
    AND English[Language]
    AND (systematic review[Filter] OR randomized controlled trial[Filter] OR observational study[Title/Abstract])
    ```

    CNKI检索式：
    ```
    主题=糖尿病 AND 主题=运动干预
    OR 主题=体力活动
    发表时间：2014-2024
    文献来源：核心期刊 OR CSSCI OR CSCD
    ```

---

## 第四部分：检索执行与记录

[检索执行流程]
    1. 在各数据库执行检索式
    2. 记录检索日期、数据库、检索式
    3. 导出检索结果（文献管理软件）
    4. 去重处理

[检索记录模板]
    ```
    ## 检索记录

    **检索日期**：2024-XX-XX
    **检索人**：XXX

    ### PubMed
    **检索式**：
    [完整检索式]

    **结果数量**：XXX 篇
    **筛选后**：XXX 篇

    ### CNKI
    **检索式**：
    [完整检索式]

    **结果数量**：XXX 篇
    **筛选后**：XXX 篇

    **总计去重后**：XXX 篇
    ```

---

## 第五部分：文献筛选

[筛选流程]
    1. 标题筛选：快速浏览，排除明显不相关
    2. 摘要筛选：按纳入/排除标准筛选
    3. 全文筛选：阅读全文，最终确定纳入

[纳入/排除标准示例]

    纳入标准：
    - 研究类型：原始研究、系统综述、Meta分析
    - 研究对象：2型糖尿病患者
    - 干预措施：运动干预（有氧、抗阻或混合）
    - 结局指标：血糖控制、HbA1c、并发症
    - 发表时间：2014年至今
    - 语言：中英文

    排除标准：
    - 研究类型：个案报告、综述（非系统综述）、述评
    - 研究对象：1型糖尿病、妊娠糖尿病
    - 干预措施：运动+药物联合干预（无法分离运动效果）
    - 重复发表或数据不全

[筛选记录]
    使用文献管理软件（EndNote/Zotero）或PRISMA流程图记录筛选过程

---

## 第六部分：文献质量评估

[证据等级分类]

    | 等级 | 研究类型 | 可信度 |
    |------|----------|--------|
    | Level 1 | 系统综述/Meta分析 | 最高 |
    | Level 2 | 随机对照试验(RCT) | 高 |
    | Level 3 | 队列研究 | 中高 |
    | Level 4 | 病例对照研究 | 中 |
    | Level 5 | 横断面研究、病例系列 | 较低 |
    | Level 6 | 病例报告、专家意见 | 低 |

[质量评估要点]

    RCT质量评估：
    - 随机化方法
    - 分配隐藏
    - 盲法
    - 失访率
    - 意向性分析

    观察性研究质量评估：
    - 样本量
    - 随访时间
    - 混杂因素控制
    - 测量方法

---

## 第七部分：信息提取

[提取内容模板]

    | 字段 | 内容 |
    |------|------|
    | 文献ID | PMID/DOI |
    | 作者 | 第一作者 |
    | 年份 | 发表年份 |
    | 期刊 | 期刊名称 |
    | 研究类型 | RCT/队列/病例对照等 |
    | 样本量 | 研究对象数量 |
    | 研究对象 | 人口学特征 |
    | 干预措施 | 具体内容 |
    | 对照 | 对照组设置 |
    | 结局指标 | 主要/次要结局 |
    | 主要结果 | 定量/定性结果 |
    | 局限性 | 作者说明的局限性 |
    | 证据等级 | Level 1-6 |
    | 备注 | 其他重要信息 |

---

## 第八部分：检索产出

[产出文件]
    按照 templates/search-protocol-template.md 的格式输出检索策略文档
    按照 templates/literature-summary-template.md 的格式输出文献摘要表

[质量检查]
    - 检索策略是否可复现？
    - 纳入文献是否覆盖主要研究？
    - 是否遗漏重要文献（手工检索补充）？
    - 文献质量评估是否完整？

---

## 第九部分：参考范文分析

[Nature Reviews Disease Primers - Osteoarthritis (2025)]

    这篇范文展示了高水平综述的文献检索和整合标准：

    [文献数量与质量]
        - 总参考文献：284篇
        - 涵盖文献类型：
          - 系统综述/Meta分析（约40%）
          - RCT（约30%）
          - 队列研究（约15%）
          - 基础研究（约10%）
          - 指南/共识（约5%）

    [文献时效性]
        - 大部分文献来自2015-2024年
        - 关键经典文献追溯到1990年代
        - 包含2024-2025年最新研究

    [引用分布]
        - 每个主要观点引用1-3篇文献
        - 共识点引用多篇高质量研究
        - 争议点引用各方观点

    [可借鉴的检索策略]
        ```
        核心检索词（骨关节炎）：
        - "Osteoarthritis"[MeSH] OR "osteoarthritis"[Title/Abstract]
        - "Knee osteoarthritis" OR "Hip osteoarthritis" OR "Hand osteoarthritis"

        检索策略特点：
        - 按解剖部位细分检索
        - 包含疼痛机制相关检索
        - 纳入治疗干预的各类研究
        - 重点关注高质量证据（系统综述、RCT）
        ```

[应用于椎间盘突出综述的建议]

    基于骨关节炎范文的检索经验，椎间盘突出综述应：

    1. **核心文献层**（20-30篇）
       - 近5年系统综述/Meta分析
       - 权威指南/共识
       - 高影响因子期刊研究

    2. **重要支撑层**（50-80篇）
       - RCT研究
       - 大型队列研究
       - 机制研究

    3. **补充参考层**（20-30篇）
       - 经典文献
       - 病理机制基础研究
       - 诊断标准研究

    [检索数据库建议]
        - PubMed/MEDLINE（主要英文来源）
        - Cochrane Library（高质量证据）
        - CNKI/万方（中文文献）
        - Web of Science（引文追踪）