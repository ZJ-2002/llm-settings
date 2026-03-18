# 投稿写作模板集 (Submission Writing Templates)

**Medical Review Skill v2.6.1**  
**用途**: 为投稿附言 (Cover Letter)、方法学 (Methods)、结果 (Results)、讨论 (Discussion) 提供标准化学术文本模板

---

## 一、投稿附言补充段落 (Cover Letter Supplement)

### 1.1 统计方法学说明（推荐必加）

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

All statistical analysis code (Python) is available upon request to ensure full 
reproducibility of our findings.
```

### 1.2 中文对照版本

```markdown
统计转换与稳健性说明：

在本 Meta 分析中，部分纳入研究以中位数（四分位距，IQR）形式报告连续结局指标，
而非均值±标准差（Mean±SD）。为确保最大化数据利用并符合 Meta 分析合规标准，
我们采用了 Luo 等（2018）提出的均值估算法和 Wan 等（2014）提出的标准差估算法。

为维持最高水平的证据完整性，我们实施了双层质量控制方案：

1. GRADE 不精确性调整：根据 GRADE 指南，对依赖估算 Mean±SD 的研究进行不精确性评估。
   若估算数据点占合并结局的 50% 以上，则降级一级以反映不确定性增加。

2. 敏感性分析：我们进行了预设的敏感性分析，排除所有估算数据。结果证实，
   纳入估算研究并未导致合并效应量的方向或统计学显著性发生"结论翻转"，
   确保了临床发现的稳健性。

所有统计分析代码（Python）可根据要求提供，以确保研究发现的完全可重复性。
```

---

## 二、统计学方法描述 (Methods: Statistical Analysis)

### 2.1 标准版本（推荐）

```markdown
## Statistical Analysis

**Data Synthesis**
Continuous outcomes were synthesized using either a fixed-effects or random-effects 
model based on the level of clinical and statistical heterogeneity. The choice of 
model was guided by the I² statistic, where I² > 50% indicated significant heterogeneity 
warranting a random-effects model.

**Data Transformation for Meta-Analytic Compliance**
For studies reporting continuous outcomes as medians and interquartile ranges (IQR) 
rather than means and standard deviations (SD), we employed established mathematical 
conversion algorithms. The mean was estimated using the optimized method proposed by 
**Luo et al. (2018)**, which utilizes a weighted approach balancing the median and 
mid-quartile range based on sample size. The SD was estimated using the method of 
**Wan et al. (2014)**, which applies normal distribution theory to derive an 
approximation from the sample size and IQR.

**Meta-Regression for Heterogeneity Exploration**
When significant heterogeneity was detected (I² > 50%), we conducted meta-regression 
analysis using weighted least squares (WLS) with inverse variance weighting (weights = 1/SE²). 
All meta-regression analyses were performed using Python 3.10 with the `statsmodels` 
library (version 0.14.0) to ensure computational accuracy. Covariates explored included 
surgeon experience, baseline disease severity, and follow-up duration.

**Quality Assessment and Sensitivity Analysis**
The quality of evidence for each outcome was evaluated using the **GRADE (Grading of 
Recommendations, Assessment, Development, and Evaluation)** approach. For outcomes where 
estimated data (converted from medians) constituted a significant portion (>50%) of the 
total weight, we assessed the **imprecision domain** and applied a one-level downgrade 
to reflect increased uncertainty from the estimation process.

To verify the robustness of our pooled estimates, a **pre-specified sensitivity analysis** 
was conducted by excluding all studies that required data transformation. A "conclusion flip" 
(i.e., a change in the direction of effect or loss of statistical significance at α = 0.05) 
during this analysis was used as a critical indicator of outcome instability.

**Publication Bias Assessment**
Funnel plots were visually inspected for asymmetry, and Egger's regression test was 
performed when sufficient studies (≥10) were available. Trim-and-fill analysis was 
conducted to estimate the potential impact of missing studies.

**Software and Reproducibility**
All statistical analyses were performed using Python 3.10 utilizing the `statsmodels`, 
`scipy`, and `numpy` libraries. Analysis scripts are available in the supplementary 
materials to ensure full reproducibility.
```

### 2.2 简化版本（字数受限时使用）

```markdown
## Statistical Analysis

Continuous outcomes were synthesized using random-effects models when I² > 50%. 
For studies reporting medians (IQR), we converted to means (SD) using Luo (2018) 
and Wan (2014) estimation methods. Quality was assessed using GRADE, with 
downgrades for imprecision when estimated data exceeded 50% of pooled weight. 
Sensitivity analysis excluded estimated data to test robustness. Meta-regression 
(WLS, weights = 1/SE²) explored heterogeneity sources. Analyses used Python 3.10 
(statsmodels 0.14.0). Code available in supplements.
```

---

## 三、结果章节模板 (Results)

### 3.1 术后疼痛结局示例

```markdown
## Results

### Primary Outcome: Post-operative Pain Relief

A total of {{N}} studies comprising {{total_n}} patients were included in the 
meta-analysis of post-operative pain improvement at 12 months. 

**Pooled Effect Estimation**
The pooled analysis demonstrated a statistically significant improvement in 
VAS leg pain scores (pooled MD = {{X.XX}}, 95% CI: {{X.XX}} to {{X.XX}}; 
p = {{0.XXX}}). The improvement exceeded the minimally clinically important 
difference (MCID = 1.5 points) for all sensitivity scenarios.

**Heterogeneity Assessment**
Moderate statistical heterogeneity was observed (I² = {{XX}}%, τ² = {{X.XX}}). 
Meta-regression analysis revealed that surgeon experience significantly 
contributed to the observed heterogeneity (R² = {{XX.X}}%, p = {{0.0XX}}), 
accounting for approximately {{XX}}% of the between-study variance. Other 
explored covariates (patient age, baseline severity, follow-up duration) did 
not reach statistical significance (all p > 0.10).

**Data Source Transparency**
Among the {{N}} included studies, {{n_estimated}} studies ({{XX}}%) reported 
medians (IQR) and were converted to means (SD) using the Luo-Wan algorithm 
to enable meta-analytic inclusion. The converted values were: Study B 
(Mean±SD = {{X.XX}}±{{X.XX}}, converted from Median [IQR] = {{X.X}} [{{X.X}}–{{X.X}}]); 
Study C (Mean±SD = {{X.XX}}±{{X.XX}}, converted from {{X.X}} [{{X.X}}–{{X.X}}]).

### Sensitivity and Robustness Analysis

**Exclusion of Estimated Data**
When studies requiring data transformation were excluded (leaving {{n_clean}} 
studies with {{n_clean_total}} patients), the pooled effect remained directionally 
consistent (MD = {{X.XX}}, 95% CI: {{X.XX}} to {{X.XX}}; p = {{0.XXX}}), and 
statistical significance was maintained. No "conclusion flip" was detected, 
confirming the robustness of our primary findings to the inclusion of 
estimated data.

**Leave-One-Out Analysis**
Sequential exclusion of individual studies demonstrated that no single study 
exerted disproportionate influence on the pooled estimate (all effect changes 
< 25%). The pooled effect remained significant (p < 0.05) across all 
leave-one-out scenarios.

### GRADE Evidence Quality

The overall quality of evidence for the primary outcome was rated as 
**{{GRADE_rating}}** ({{rating_description}}) according to GRADE criteria. 
Key downgrades included:
- **Risk of Bias**: {{n_risk}} studies were rated as high risk in at least one domain
- **Imprecision**: Estimated data constituted {{estimated_ratio}}% of the pooled weight, 
  triggering a downgrade for uncertainty in the transformation process

The certainty rating reflects moderate confidence that the true effect lies 
close to the estimate, with further research likely to have an important 
impact on confidence in the estimate.

---

[Evidence Audit Trail - Core Data Points]
Study A (n={{n_A}}): {{X.XX}}±{{X.XX}} [Original Mean±SD]
Study B (n={{n_B}}): {{X.XX}}±{{X.XX}} [Converted from {{med_B}} ({{q1_B}}-{{q3_B}})]
Study C (n={{n_C}}): {{X.XX}}±{{X.XX}} [Converted from {{med_C}} ({{q1_C}}-{{q3_C}})]
```

---

## 四、讨论章节模板 (Discussion)

### 4.1 标准讨论结构

```markdown
## Discussion

### Summary of Main Findings

This systematic review and meta-analysis of {{N}} RCTs comprising {{total_n}} 
patients demonstrates that [intervention] significantly improves [primary outcome] 
in [population]. The pooled effect size (MD = {{X.XX}}) exceeded the MCID threshold, 
suggesting clinically meaningful benefit. However, the quality of evidence was 
moderated to {{GRADE_rating}} due to [main limitations].

### Interpretation in Context of Heterogeneity

A novel finding of this review is the quantification of heterogeneity sources 
through meta-regression. Our analysis indicates that [factor] explains 
approximately {{XX}}% of the observed between-study variance (R² = {{X.XX}}, 
p = {{0.0XX}}). This has important clinical implications: [clinical interpretation].

The relationship between [factor] and [outcome] aligns with established 
understanding of [mechanism], supporting the biological plausibility of our 
findings. This also suggests that [practical implication for clinicians].

### Methodological Rigor and Data Handling

**Handling of Non-Standard Data Reports**
A strength of this review is our transparent handling of studies reporting 
medians (IQR) rather than means (SD). Using the Luo-Wan estimation algorithms, 
we were able to include {{n_estimated}} additional studies that would otherwise 
have been excluded, maximizing the evidence base. Our pre-specified sensitivity 
analysis confirmed that the inclusion of these estimated data points did not 
alter the overall conclusion, supporting the robustness of our approach.

However, we acknowledge that this estimation introduces additional uncertainty. 
The GRADE downgrade for imprecision appropriately reflects this limitation, 
and our conservative interpretation of the evidence strength guards against 
overconfidence in the findings.

**GRADE Assessment and Clinical Implications**
The {{GRADE_rating}} quality rating indicates [interpretation]. While the 
estimated effect is likely to be close to the true effect, [caveats]. 
Clinicians should consider [practical recommendation] when applying these 
findings to individual patients.

### Comparison with Existing Literature

[Compare with previous reviews and guidelines]

### Limitations

**Study-Level Limitations**
- {{Limitation 1 with context}}
- {{Limitation 2 with context}}

**Review-Level Limitations**
- **Data Estimation**: {{XX}}% of pooled data required conversion from medians, 
  introducing uncertainty reflected in our GRADE assessment
- **Heterogeneity**: Despite meta-regression exploration, residual heterogeneity 
  (I² = {{XX}}%) suggests unmeasured sources of variation
- **Generalizability**: [Population limitations]

### Implications for Practice and Research

**Clinical Recommendations**
1. [Recommendation 1 with strength and certainty]
2. [Recommendation 2 with strength and certainty]

**Future Research Priorities**
1. [Research gap 1]: [Specific suggestion]
2. [Research gap 2]: [Specific suggestion]
3. **Methodological Priority**: Future studies should report means (SD) rather 
   than medians (IQR) to facilitate more precise meta-analytic synthesis. 
   Standardized outcome reporting guidelines should be adopted in [field].

### Conclusion

[Concise summary of key findings and implications]
```

---

## 五、Nature Reviews 风格专家建议框 (Expert Recommendations Box)

```markdown
> 🟢 **Box: Conclusion and Expert Recommendations**
>
> **1. Core Clinical Findings**
> - Significant Efficacy: Evidence demonstrates [intervention] provides 
>   clinically meaningful improvement in [outcome], exceeding MCID thresholds.
> - Evidence Robustness: Sensitivity analysis confirmed core superiority 
>   conclusions remain stable even after exclusion of estimated data.
>
> **2. Learning Curve and Surgeon Selection**
> - Quantified Impact: Meta-regression indicates surgeon experience explains 
>   {{XX}}% of outcome variance (R²={{X.XX}}, p={{0.0XX}}).
> - Expert Recommendation: Given the steep learning curve, complex cases should 
>   be referred to high-volume centers (>200-500 cases). Trainees should 
>   complete supervised proctorship for initial 100 cases.
>
> **3. Precision Medicine and Patient Selection**
> - Non-linear Decision: Imaging severity alone is not an absolute surgical 
>   indicator; responsible segment identification is key.
> - Recurrence Prevention: Preoperative annular integrity assessment should 
>   guide adjunctive repair techniques in high-risk patients.
>
> **4. Methodological Transparency**
> - Data Conversion Standard: For Median(IQR) reporting common in field, 
>   recommend Luo (2018) + Wan (2014) algorithms for compliant conversion.
> - GRADE Rating: Downgrade for imprecision when estimated data >50% of 
>   pooled weight to reflect scientific conservatism.
>
> **5. Future Research Gaps**
> - Technological Obsolescence: Urgent need to assess impact of new-generation 
>   equipment on conclusions from early studies.
> - Long-term Follow-up: Evidence for disease-modifying effects beyond 5-10 
>   years remains insufficient.
```

---

## 六、参考文献格式

### 统计方法学核心引用

```bibtex
@article{luo2018estimating,
  title={Optimally estimating the sample mean from the sample size, median, mid-range, and/or mid-quartile range},
  author={Luo, Dehui and Wan, Xiang and Liu, Jiming and Tong, Tiejun},
  journal={Statistical Methods in Medical Research},
  volume={27},
  number={6},
  pages={1785--1805},
  year={2018},
  publisher={Sage Publications}
}

@article{wan2014estimating,
  title={Estimating the sample mean and standard deviation from the sample size, median, range and/or interquartile range},
  author={Wan, Xiang and Wang, Wenqian and Liu, Jiming and Tong, Tiejun},
  journal={BMC Medical Research Methodology},
  volume={14},
  number={1},
  pages={135},
  year={2014},
  publisher={BioMed Central}
}

@article{higgins2019cochrane,
  title={Cochrane Handbook for Systematic Reviews of Interventions},
  author={Higgins, Julian PT and Thomas, James and Chandler, Jacqueline and 
          Cumpston, Miranda and Li, Tianjing and Page, Matthew J and 
          Welch, Vivian A},
  journal={Wiley Blackwell},
  year={2019}
}

@article{grade2008grading,
  title={GRADE: an emerging consensus on rating quality of evidence and strength of recommendations},
  author={{GRADE Working Group}},
  journal={BMJ},
  volume={336},
  number={7650},
  pages={924--926},
  year={2008}
}
```

---

**模板版本**: v2.6.1  
**最后更新**: 2026-03-13  
**适用技能**: Medical Review Skill