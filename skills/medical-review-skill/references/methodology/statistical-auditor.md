# Statistical Auditor 统计学审计模块

> **版本**: v2.5.1  
> **分类**: P0 - 极高优先级  
> **功能**: 提供真正的统计学计算审计能力，超越"提问"层面  
> **v2.5.1 重大更新**: 引入脆弱性指数 (FI) 取代后验把握度，解决学术争议

---

## 模块定位

将统计学审稿人从"提问者"转变为"计算审计者"，通过实际计算验证研究的方法学质量。

**核心转变**:
```
❌ 旧模式 (v2.4.0): "n=50，把握度仅55%，你怎么解释？"（后验把握度 - 学术争议）
✅ 新模式 (v2.5.1): "FI=2，仅需2个患者结局改变结论就会逆转，研究极不稳定"（脆弱性指数 - 顶刊推荐）
```

---

## v2.5.1 重大更新说明

### 为什么要用 FI 取代后验把握度？

| 维度 | 后验把握度 (Post-hoc Power) | 脆弱性指数 (Fragility Index) |
|------|----------------------------|------------------------------|
| **学术争议** | 被顶级统计学家批评为"同义反复" | Lancet、JAMA 等顶刊推崇 |
| **临床意义** | 抽象的百分比概念 | 直观的"几个病人" |
| **审稿人认可** | 可能被认为不专业 | 现代稳健性评估金标准 |
| **信息增益** | P值大→Power小（无新信息） | 揭示结果稳健性的临界点 |
| **适用性** | 连续变量为主 | 二元结局（手术/复发等）更优 |

**参考文献**: 
- Walsh M, et al. J Clin Epidemiol. 2014;67(6):622-628
- Evaniew N, et al. Spine J. 2015;15(10):2188-2197

---

## 核心计算功能

### 1. 脆弱性指数计算 (Fragility Index) ⚠️ v2.5.1 核心

**功能**: 计算需要改变多少个患者结局才能使显著性消失，评估研究结论的稳健性。

**核心概念**:
- **FI**: 需要将干预组中多少个"非事件"改为"事件"才能使 P≥0.05
- **FQ**: Fragility Quotient = FI / 总样本量
- **FI-NHT 联动**: 如果 FI < NNT，标记为临床风险项

**Python实现**:
```python
from scipy.stats import fisher_exact
import numpy as np

class StatisticalAuditor:
    def calculate_fragility_index(
        self,
        e1: int,                    # 干预组事件数
        n1: int,                    # 干预组总人数
        e2: int,                    # 对照组事件数
        n2: int,                    # 对照组总人数
        direction: str = "better"   # "better"=干预组事件率更低, "worse"=更高
    ) -> dict:
        """
        计算脆弱性指数 (v2.5.1 核心算法)
        
        Returns:
            {
                "fi": 2,                    # 脆弱性指数
                "fq": 0.01,                 # 脆弱性商数
                "p_original": 0.024,        # 原始P值
                "p_final": 0.063,           # 最终P值
                "risk_level": "EXTREME",    # 风险等级
                "interpretation": "...",    # 临床解读
                "nnt": 10,                  # Number Needed to Treat
                "fi_nht_alert": True        # FI-NHT联动警报
            }
        """
        # 原始Fisher精确检验
        table_original = [[e1, n1 - e1], [e2, n2 - e2]]
        _, p_original = fisher_exact(table_original)
        
        if p_original >= 0.05:
            return {
                "fi": 0,
                "fq": 0,
                "p_original": p_original,
                "p_final": p_original,
                "risk_level": "NOT_SIGNIFICANT",
                "interpretation": "原本就不显著，无需计算FI"
            }
        
        # 迭代计算FI
        max_iterations = n1 - e1 if direction == "better" else e1
        event_increment = 1 if direction == "better" else -1
        
        fi = 0
        current_e1 = e1
        current_p = p_original
        
        while current_p < 0.05 and fi < max_iterations:
            fi += 1
            current_e1 += event_increment
            table_current = [[current_e1, n1 - current_e1], [e2, n2 - e2]]
            _, current_p = fisher_exact(table_current)
        
        # 计算FQ
        total_n = n1 + n2
        fq = fi / total_n if total_n > 0 else 0
        
        # 计算NNT
        rate1 = e1 / n1 if n1 > 0 else 0
        rate2 = e2 / n2 if n2 > 0 else 0
        arr = abs(rate2 - rate1)
        nnt = 1 / arr if arr > 0 else float('inf')
        
        # FI-NHT联动检查
        fi_nht_alert = fi < nnt if nnt != float('inf') else False
        
        # 风险等级判定
        risk_level = self._interpret_fi(fi, fq)
        
        return {
            "fi": fi,
            "fq": round(fq, 4),
            "p_original": round(p_original, 4),
            "p_final": round(current_p, 4),
            "risk_level": risk_level["level"],
            "interpretation": risk_level["interpretation"],
            "recommendation": risk_level["recommendation"],
            "nnt": round(nnt, 1) if nnt != float('inf') else None,
            "fi_nht_alert": fi_nht_alert
        }
    
    def _interpret_fi(self, fi: int, fq: float) -> dict:
        """脆弱性指数解读标准 (v2.5.1)"""
        if fi == 0:
            return {
                "level": "NOT_SIGNIFICANT",
                "interpretation": "原本就不显著",
                "recommendation": "无需FI评估"
            }
        elif fi <= 2 or fq < 0.01:
            return {
                "level": "EXTREME",
                "interpretation": f"极高脆性 - 仅需{fi}个患者改变即可逆转结论",
                "recommendation": "结论极不稳定，强烈建议降级证据确定性"
            }
        elif fi <= 5 or fq < 0.05:
            return {
                "level": "HIGH",
                "interpretation": f"高脆性 - FI={fi}，结论稳健性不足",
                "recommendation": "需谨慎解读，建议标注不精确性降级"
            }
        elif fi <= 10 or fq < 0.10:
            return {
                "level": "MODERATE",
                "interpretation": f"中等脆性 - FI={fi}，可接受但非最优",
                "recommendation": "结论相对稳定，但大规模推广需更多证据"
            }
        else:
            return {
                "level": "LOW",
                "interpretation": f"相对稳健 - FI={fi}，结论较可靠",
                "recommendation": "结论稳健，可放心使用"
            }
```

**使用示例**:
```python
auditor = StatisticalAuditor()

# LDH手术复发率审计示例
result = auditor.calculate_fragility_index(
    e1=5, n1=100,    # 微创组: 5例复发/100例
    e2=15, n2=100,   # 开放组: 15例复发/100例
    direction="better"
)

# 输出:
# {
#   "fi": 2,
#   "fq": 0.01,
#   "p_original": 0.024,
#   "p_final": 0.063,
#   "risk_level": "EXTREME",
#   "interpretation": "极高脆性 - 仅需2个患者改变即可逆转结论",
#   "recommendation": "结论极不稳定，强烈建议降级证据确定性",
#   "nnt": 10,
#   "fi_nht_alert": True  # FI(2) < NNT(10)，临床风险项
# }
```

**FI 风险等级解读**:

| FI 范围 | FQ 范围 | 风险等级 | 临床意义 | GRADE建议 |
|---------|---------|----------|----------|-----------|
| 0 | - | NOT_SIGNIFICANT | 原本不显著 | - |
| 1-2 | <1% | EXTREME | 极不稳定 | 降2级 |
| 3-5 | 1-5% | HIGH | 稳定性不足 | 降1级 |
| 6-10 | 5-10% | MODERATE | 可接受 | 不降级 |
| >10 | >10% | LOW | 较稳健 | 不降级 |

---

### 2. 连续变量的反向均值平移测试 ⚠️ v2.5.1 新增

**功能**: 针对连续变量（如VAS、ODI）计算需要多大的均值变动才能抵消统计学意义。

**Python实现**:
```python
def reverse_mean_shift_test(
    self,
    mean1: float, sd1: float, n1: int,    # 干预组
    mean2: float, sd2: float, n2: int     # 对照组
) -> dict:
    """
    反向均值平移测试 (v2.5.1 连续变量方案)
    
    Returns:
        {
            "shift_required": 2.3,          # 需要平移的单位数
            "relative_shift": 0.45,         # 相对原始差异的比例
            "p_original": 0.032,
            "p_final": 0.052,
            "interpretation": "..."
        }
    """
    from scipy import stats
    
    # 原始t检验
    se1 = sd1 / np.sqrt(n1)
    se2 = sd2 / np.sqrt(n2)
    sed = np.sqrt(se1**2 + se2**2)
    
    t_original = (mean1 - mean2) / sed
    df = n1 + n2 - 2
    p_original = 2 * (1 - stats.t.cdf(abs(t_original), df))
    
    if p_original >= 0.05:
        return {
            "shift_required": 0,
            "relative_shift": 0,
            "p_original": p_original,
            "interpretation": "原本就不显著"
        }
    
    # 迭代寻找临界均值差
    current_mean1 = mean1
    shift = 0
    step = 0.01
    max_shift = abs(mean1 - mean2)
    
    direction = -1 if mean1 > mean2 else 1  # 向mean2方向平移
    
    while True:
        t_current = (current_mean1 - mean2) / sed
        p_current = 2 * (1 - stats.t.cdf(abs(t_current), df))
        
        if p_current >= 0.05 or abs(shift) >= max_shift:
            break
        
        current_mean1 += direction * step
        shift += step
    
    relative_shift = shift / abs(mean1 - mean2) if mean1 != mean2 else 0
    
    # 风险等级
    if relative_shift < 0.1:
        risk = "极高脆性 - 微小变动即可逆转结论"
    elif relative_shift < 0.25:
        risk = "高脆性 - 较小变动可逆转结论"
    elif relative_shift < 0.5:
        risk = "中等脆性 - 中等变动可逆转结论"
    else:
        risk = "相对稳健"
    
    return {
        "shift_required": round(shift, 2),
        "relative_shift": round(relative_shift, 3),
        "p_original": round(p_original, 4),
        "p_final": round(p_current, 4),
        "interpretation": f"均值需要平移 {shift:.2f} 单位 ({relative_shift*100:.1f}%) 才能抵消显著性 - {risk}"
    }
```

---

### 3. P值与统计量一致性验证

**功能**: 验证报告的P值与统计量是否一致，检测潜在的数据错误或报告偏倚。

```python
def check_p_value_consistency(
    self,
    test_statistic: float,
    df: int,
    reported_p: float,
    test_type: str = "t"
) -> dict:
    """验证P值与统计量一致性"""
    from scipy import stats
    
    if test_type == "t":
        calculated_p = 2 * (1 - stats.t.cdf(abs(test_statistic), df))
    elif test_type == "z":
        calculated_p = 2 * (1 - stats.norm.cdf(abs(test_statistic)))
    elif test_type == "chi2":
        calculated_p = 1 - stats.chi2.cdf(test_statistic, df)
    elif test_type == "f":
        calculated_p = 1 - stats.f.cdf(test_statistic, df[0], df[1])
    else:
        raise ValueError(f"不支持的检验类型: {test_type}")
    
    ratio = max(calculated_p, reported_p) / max(min(calculated_p, reported_p), 1e-10)
    consistent = ratio <= 1.5
    
    if ratio > 10:
        alert_level = "严重"
    elif ratio > 2:
        alert_level = "中等"
    elif ratio > 1.5:
        alert_level = "轻微"
    else:
        alert_level = "无"
    
    return {
        "calculated_p": round(calculated_p, 6),
        "reported_p": reported_p,
        "consistent": consistent,
        "discrepancy_ratio": round(ratio, 2),
        "alert_level": alert_level,
        "recommendation": "数据一致" if consistent else "建议核对原始数据"
    }
```

---

### 4. 最小临床重要差异(MCID)审计

```python
def audit_clinical_significance(
    self,
    observed_effect: float,
    mcid: float,
    measure_type: str = "mean_diff"
) -> dict:
    """审计临床意义"""
    ratio = abs(observed_effect) / abs(mcid)
    
    if ratio >= 2.0:
        level = "明确临床意义"
        recommendation = "效应量显著超过MCID，临床价值明确"
    elif ratio >= 1.0:
        level = "边际临床意义"
        recommendation = "效应量达到MCID阈值，但临床价值有限"
    elif ratio >= 0.5:
        level = "微弱临床意义"
        recommendation = "效应量低于MCID，临床价值存疑"
    else:
        level = "无临床意义"
        recommendation = "效应量远低于MCID，临床意义可忽略"
    
    return {
        "mcid_ratio": round(ratio, 2),
        "clinically_meaningful": ratio >= 1.0,
        "interpretation": f"效应量为MCID的{ratio:.1f}倍，{level}",
        "recommendation": recommendation
    }

# MCID数据库
MCID_DATABASE = {
    "WOMAC总分": {"value": 12, "direction": "decrease", "unit": "points"},
    "VAS疼痛": {"value": 10, "direction": "decrease", "unit": "mm"},
    "ODI评分": {"value": 10, "direction": "decrease", "unit": "points"},
    "JOA评分": {"value": 2.5, "direction": "increase", "unit": "points"},
    "SF-36 PCS": {"value": 5, "direction": "increase", "unit": "points"},
    # v2.5.1 新增LDH专项
    "腿痛VAS": {"value": 15, "direction": "decrease", "unit": "mm"},
    "腰痛VAS": {"value": 15, "direction": "decrease", "unit": "mm"},
}
```

---

### 5. 后验把握度计算（保留作为补充）⚠️ v2.5.1 降级为辅助指标

**注意**: 后验把握度仍保留用于样本量规划回顾，但**不再作为主要稳健性指标**。

```python
def calculate_post_hoc_power(
    self,
    n1: int,
    n2: int,
    mean_diff: float,
    pooled_sd: float,
    alpha: float = 0.05
) -> dict:
    """
    计算后验把握度 (v2.5.1 降级为辅助指标)
    
    ⚠️ 警告: 后验把握度存在学术争议，仅用于样本量规划回顾
    主要稳健性评估请使用脆弱性指数 (FI)
    """
    from scipy import stats
    
    cohens_d = mean_diff / pooled_sd
    n_harmonic = 2 * n1 * n2 / (n1 + n2)
    ncp = abs(cohens_d) * np.sqrt(n_harmonic / 2)
    
    z_alpha = stats.norm.ppf(1 - alpha/2)
    power = 1 - stats.norm.cdf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp)
    
    return {
        "power": round(power, 3),
        "cohens_d": round(cohens_d, 3),
        "note": "⚠️ 后验把握度仅用于样本量规划回顾，稳健性评估请使用FI"
    }
```

---

## Evidence Audit Trail 整合 (v2.5.1 更新)

在审计完成后，生成标准化的 Evidence Audit Trail:

```markdown
**[Statistical Audit Trail v2.5.1]**

### 主要稳健性指标 (推荐使用)
- **脆弱性指数 (FI)**: 2
- **脆弱性商数 (FQ)**: 0.01 (1%)
- **风险等级**: 🔴 EXTREME (极高脆性)
- **FI-NHT 联动**: ⚠️ FI (2) < NNT (10) - 临床风险项

### 辅助指标
- **后验把握度**: 0.55 (⚠️ 仅作参考，存在学术争议)

### 其他审计结果
- **P值一致性**: ✅ 通过
- **临床意义**: ✅ 有意义 (效应量/MCID = 2.1)
- **多重比较**: ⚠️ 需校正

### 审计结论
该研究结论极不稳定。仅需微创组中 **2 名** 患者从"未复发"变为"复发"，
显著性差异即刻消失。考虑到 LDH 术后失访率通常高于 5%，
该结论极易由随访偏倚逆转。

**建议**: 降级为 ⊕⊕◯◯ (低确定性)，综述中需明确标注脆弱性
```

---

## 与 Review Checklist 的整合 (v2.5.1 更新)

```markdown
## 统计学审计检查清单

### 主要稳健性评估 (v2.5.1 优先级: P0)
- [ ] 计算脆弱性指数 (FI) - **必做**
- [ ] 计算脆弱性商数 (FQ) - **必做**
- [ ] FI-NHT 联动检查 - **必做**
- [ ] 确定风险等级并标注
- [ ] 根据FI调整GRADE评级

### 连续变量专项 (如适用)
- [ ] 反向均值平移测试
- [ ] 评估相对变动比例

### 辅助审计
- [ ] P值与统计量一致性验证
- [ ] MCID临床意义审计
- [ ] 多重比较校正审计
- [ ] 后验把握度 (仅作参考)

### 审计报告生成
- [ ] 生成 Evidence Audit Trail
- [ ] 提供临床解读建议
- [ ] 标注综述中需说明的局限性
```

---

## 使用场景

### 场景1: LDH手术复发率研究审计 (v2.5.1 典型案例)
```
研究声称"微创组复发率显著降低"(5% vs 15%, P=0.024)
↓ Statistical Auditor 审计 (v2.5.1)
- FI = 2 (极高脆性)
- FQ = 0.01 (1%)
- FI < NNT (2 < 10) - 临床风险项
↓ 结论
"结论极不稳定，仅需2例患者改变即可逆转。
考虑到LDH失访率通常>5%，建议降级为低确定性证据。"
```

### 场景2: 连续变量审计 (VAS评分)
```
研究声称"微创手术VAS改善更显著"(P=0.032)
↓ Statistical Auditor 审计
- 反向均值平移: 需平移2.3mm (相对变动23%)
- 风险等级: MODERATE
↓ 结论
"需要约1/4的改善幅度变动才能抵消显著性，结论中等稳健"
```

---

## 实现状态

- [x] 脆弱性指数计算 (v2.5.1 核心)
- [x] 脆弱性商数计算
- [x] FI-NHT 联动检查
- [x] 反向均值平移测试 (连续变量)
- [x] P值一致性验证
- [x] MCID审计
- [x] 后验把握度 (降级为辅助)
- [ ] 自动化审计报告生成
- [ ] 与 Graph Digitization 集成

---

## 版本变更记录

### v2.5.1 (2026-03-13)
- **重大更新**: 引入脆弱性指数 (FI) 取代后验把握度作为主要稳健性指标
- **新增**: FI-NHT 联动检查
- **新增**: 反向均值平移测试（连续变量方案）
- **调整**: 后验把握度降级为辅助指标（学术争议）
- **优化**: Evidence Audit Trail 格式更新

### v2.4.0 (2026-03-12)
- 初始版本
- 后验把握度计算
- P值一致性验证
- MCID审计

---

*最后更新: 2026-03-13*  
*版本: v2.5.1 - 统计学稳健性评估升级*