# 🚀 Medical Review Skill v2.6.1: 投稿前最终审核报告

**项目名称**: [在此输入你的综述题目]  
**生成日期**: {{DATE}}  
**审核版本**: v2.6.1-final-check  
**状态**: 🔴 待核对 / 🟡 建议修改 / 🟢 准许投递  

---

## 一、数据完整性与提取审计 (Data Integrity)

**核心引擎**: HierarchicalHeaderParser v2.6.1 & Virtual Grid Algorithm

| 检查项目 | 结果 | 状态 | 详细说明 |
|----------|------|------|----------|
| 物理网格对齐 | [OK / Error] | 🟢 | validate_grid_alignment 确认所有表格 colspan/rowspan 无逻辑冲突 |
| 复合 n 值关联 | [n=XXX] | 🟢 | 已准确解析 n=60+60 及 n=145/150 等复杂样本量表达式（v2.6.1 返回 primary_n + total_n） |
| 临床符号保护 | [已提取] | 🟢 | 特殊标记 (*, †, ‡, §) 已建立 FootnoteLinker 关联，无语义丢失 |
| 父节点链接验证 | [Pass] | 🟢 | v2.6.1 向上溯源算法验证通过，空行/装饰行已正确处理 |

### 1.1 样本量解析详情（v2.6.1 增强）

| 列路径 | Primary n | Total n | 格式 | 说明 |
|--------|-----------|---------|------|------|
| [路径1] | {{n1}} | {{N1}} | {{format1}} | 随访表：分子为有效随访数，分母为原始随机化人数 |
| [路径2] | {{n2}} | {{N2}} | {{format2}} | 基线表：两者相同 |

---

## 二、统计学合规性审计 (Statistical Compliance)

**核心引擎**: MedianToMeanConverter & Luo-Wan Estimation

### 2.1 数值转换汇总

本次综述包含以下基于 **Luo (2018) + Wan (2014)** 算法的转换：

| 研究 ID | 原始格式 | 转换后 Mean (SD) | 置信度 | 权重影响 |
|---------|----------|------------------|--------|----------|
| [Study_A] | Mean ± SD | {{X.XX}}±{{X.XX}} | 🟢 高 | 原始数据 |
| [Study_B] | Median (IQR) | {{X.XX}}±{{X.XX}} | 🟡 中 | 算法估算 (n={{n}}) |
| [Study_C] | Median (Range) | {{X.XX}}±{{X.XX}} | 🟠 低 | 算法估算 (n={{n}}<30) |

**统计合规警告**：
- ⚠️ {{count}} 项研究使用了中位数转换（占比 {{ratio}}%）
- 🟡 {{count_low}} 项研究样本量 < 30，估算置信度较低

### 2.2 元回归归因分析 (Statistical Audit Trail)

**运行环境**: Python {{version}} + Statsmodels {{version}}

**条件触发**：仅当 I² > 50% 且研究数 ≥ 5 时执行

- **总异质性 (I²)**: {{XX}}%
- **元回归模型**: 加权最小二乘 (WLS)，权重 = 1/SE²
- **代码执行验证**: [✅ 已执行 / ❌ 未执行]  
  {{若未执行："基于定性分析，无定量 R² 贡献"}}

| 协变量 | R² 贡献 | p 值 | 显著性 | 计算来源 |
|--------|---------|------|--------|----------|
| {{var1}} | {{X.X}}% | {{0.0XX}} | {{sig}} | Python 计算 |
| {{var2}} | {{X.X}}% | {{0.XXX}} | {{sig}} | Python 计算 |

**⚠️ 统计学幻觉防护检查**：
- [ ] 所有 R² 值均来自真实 Python 计算，非 LLM 估算
- [ ] 每个协变量均报告 p 值
- [ ] 模型类型（固定/随机）已说明

---

## 三、质量评估与 GRADE 降级 (Bias & Quality)

**核心引擎**: BiasAssessor & Cochrane RoB 2.0

### 3.1 偏倚风险热图 (Risk of Bias Heatmap)

| 研究 ID | D1 随机化 | D2 偏离 | D3 缺失数据 | D4 测量 | D5 选择性报告 | 总体 |
|---------|-----------|---------|-------------|---------|---------------|------|
| {{id1}} | 🟢 | 🟢 | 🟡 | 🟡 | 🟢 | 🟡 |
| {{id2}} | 🟡 | 🟢 | 🔴 | 🟡 | 🟢 | 🔴 |

**图例**: 🟢 Low | 🟡 Some Concerns | 🔴 High

### 3.2 GRADE 自动降级报告（v2.6.1 增强）

| 领域 | 状态 | 降级原因 | 备注 |
|------|------|----------|------|
| 偏倚风险 | {{status}} | {{reason}} | 基于 RoB 2.0 |
| 不精确性 | {{status}} | {{reason}} | v2.6.1: 基于估算数据占比 {{ratio}}% > {{threshold}}% 触发 |
| 不一致性 | {{status}} | {{reason}} | I² = {{i2}}% |
| 间接性 | {{status}} | {{reason}} | 替代指标: {{surrogate}} |

**GRADE 评级分布**：
| 评级 | 研究数 | 占比 |
|------|--------|------|
| ⊕⊕⊕⊕ (High) | {{n}} | {{pct}}% |
| ⊕⊕⊕◯ (Moderate) | {{n}} | {{pct}}% |
| ⊕⊕◯◯ (Low) | {{n}} | {{pct}}% |
| ⊕◯◯◯ (Very Low) | {{n}} | {{pct}}% |

---

## 四、敏感性与稳健性压力测试 (Stress Test)

**核心引擎**: SensitivityAnalyzer

### 4.1 结论稳定性测试

针对剔除"估算数据"后的 Meta 分析：

| 场景 | 纳入研究数 | 效应量 (MD/SMD) | P 值 | 结论状态 |
|------|------------|-----------------|------|----------|
| 全样本分析 | {{n_total}} | {{X.XX}} [{{CI}}] | {{0.0XX}} | {{status}} |
| 剔除估算数据 | {{n_clean}} | {{X.XX}} [{{CI}}] | {{0.0XX}} | {{status}} |

### 4.2 结论翻转风险评估

**检测指标**：
- **显著性翻转**: {{yes/no}} (全样本 p={{p1}} → 剔除后 p={{p2}})
- **效应方向翻转**: {{yes/no}} ({{dir1}} → {{dir2}})
- **效应量变化**: {{change}}% (阈值: 30%)

**风险评级**: {{LOW / MODERATE / HIGH / CRITICAL}}

**AI 预警**：
```
{{if CRITICAL}}
⚠️ 结论翻转风险极高！剔除估算数据后结论发生逆转。
请在讨论部分明确说明这一局限性，建议投稿前补充原始 Mean±SD 的研究。
{{elif HIGH}}
⚠️ 结论处于边缘状态。剔除估算数据后 p 值接近 0.05。
建议在讨论中声明结论的脆弱性。
{{else}}
✅ 敏感性测试通过，结论稳健。估算数据未改变统计学显著性方向。
{{end}}
```

### 4.3 留一法敏感性分析

| 剔除研究 | 效应量变化 | 显著性改变 | 影响评级 |
|----------|------------|------------|----------|
| {{id1}} | {{X}}% | {{yes/no}} | {{high/low}} |
| {{id2}} | {{X}}% | {{yes/no}} | {{high/low}} |

---

## 五、专家视角审稿人攻击模拟 (Reviewer Defense)

**核心机制**: Adversarial Synthesis

### 5.1 统计学审稿人攻击

| 攻击问题 | 防御准备状态 | 应对策略 |
|----------|--------------|----------|
| "如何证明 Luo-Wan 转换不会偏向实验组？" | {{ready/partial/none}} | 已准备 Sensitivity Analysis 数据证明结论稳健性 |
| "R² 贡献度是如何计算的？" | {{ready/partial/none}} | 基于 Python statsmodels WLS 模型，代码可审计 |
| "是否考虑了发表偏倚？" | {{ready/partial/none}} | 漏斗图分析 + Egger 检验 |

### 5.2 方法学审稿人攻击

| 攻击问题 | 防御准备状态 | 应对策略 |
|----------|--------------|----------|
| "纳入的 RCT 是否存在选择偏倚？" | {{ready/partial/none}} | RoB 2.0 评估 + 偏倚风险热图 |
| "异质性来源是否充分探讨？" | {{ready/partial/none}} | Meta 回归归因分析 |
| "估算数据占比过高如何处理？" | {{ready/partial/none}} | GRADE 不精确性降级 + 敏感性分析 |

### 5.3 临床审稿人攻击

| 攻击问题 | 防御准备状态 | 应对策略 |
|----------|--------------|----------|
| "PELD 的复发率在不同研究间差异极大，综合结论是否过于乐观？" | {{ready/partial/none}} | Conflict Resolver 识别复发率与术者学习曲线的定量关系 |
| "结果是否可推广到常规临床？" | {{ready/partial/none}} | 讨论中明确限定适用人群 |

---

## 六、投稿材料清单 (Submission Checklist)

### 6.1 必需文件

- [ ] 综述正文（含所有 Evidence Audit Trail）
- [ ] PRISMA 流程图
- [ ] PRISMA 检查清单
- [ ] 利益冲突声明
- [ ] 作者贡献声明

### 6.2 补充材料

- [ ] 检索策略详细记录
- [ ] 纳入研究特征表
- [ ] 偏倚风险热图（高清）
- [ ] GRADE 证据概要表
- [ ] 森林图（如有 Meta 分析）
- [ ] 漏斗图（发表偏倚评估）

### 6.3 数据可用性声明

**推荐文本**：
```
Data Availability Statement:
All data extracted from included studies are available in the supplementary materials. 
Statistical analysis code (Python) used for meta-regression and sensitivity analysis 
is available at [repository/link] to ensure reproducibility.
```

---

## 七、最终审核结论 (Final Verdict)

### 综合评级: [🟢 建议投递 / 🟡 条件投递 / 🔴 建议暂缓]

### 主要优势
1. {{strength1}}
2. {{strength2}}
3. {{strength3}}

### 主要局限与应对
1. {{limitation1}} → 应对: {{mitigation1}}
2. {{limitation2}} → 应对: {{mitigation2}}

### 审稿人最可能攻击的点
1. {{attack1}} → 预备回应: {{response1}}
2. {{attack2}} → 预备回应: {{response2}}

---

## 八、附录：Cover Letter 补充段落

### 统计方法学说明（可选添加至 Cover Letter）

```markdown
Statistical Note on Data Conversion and Robustness:

In this meta-analysis, several included studies reported continuous outcomes as 
Median (Interquartile Range, IQR) rather than Mean±Standard Deviation (SD). 
To ensure maximal data utilization and meta-analytic compliance, we employed the 
established estimation methods proposed by Luo et al. (2018) for mean estimation 
and Wan et al. (2014) for SD estimation.

To maintain the highest level of evidence integrity, we implemented a dual-layered 
quality control protocol:

1. GRADE Imprecision Adjustment: According to GRADE guidelines, studies relying on 
   estimated Mean±SD were assessed for imprecision. A one-level downgrade was applied 
   if estimated data points constituted over 50% of the pooled outcome to reflect 
   increased uncertainty.

2. Sensitivity Analysis: We performed a pre-specified sensitivity analysis by 
   excluding all estimated data. The results confirmed that the inclusion of 
   estimated studies did not result in a "conclusion flip" regarding the direction 
   or statistical significance of the pooled effect size, ensuring the robustness 
   of our clinical findings.
```

---

**报告生成**: Medical Review Skill v2.6.1  
**审核模块**: HierarchicalHeaderParser + MedianToMeanConverter + BiasAssessor + SensitivityAnalyzer  
**统计方法**: Luo-Wan Estimation | Inverse Variance Meta-analysis | WLS Meta-regression  

---

*本报告基于自动化检查生成，建议投稿前由人工最终审核。*