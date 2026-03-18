# Negative Evidence Detector 负向证据缺失探测

> **版本**: v2.4.0  
> **分类**: P2 - 中等优先级  
> **功能**: 识别选择性报告风险，检测"好得难以置信"的结果

---

## 模块定位

**问题**: 未主动探测负向证据缺失，缺乏对"好得难以置信"结果的警示。

**目标**: 像统计学审稿人一样，识别"只有正面结论且效应量大"的异常模式。

---

## 核心功能

### 1. 选择性报告风险检测

```python
# negative_evidence_detector.py

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

class BiasRiskLevel(Enum):
    MINIMAL = "minimal"     # 低风险
    LOW = "low"             # 较低风险
    MODERATE = "moderate"   # 中等风险
    HIGH = "high"           # 高风险
    CRITICAL = "critical"   # 极高风险

@dataclass
class NegativeEvidenceAnalysis:
    """负向证据分析结果"""
    paper_id: str
    intervention: str
    primary_outcomes: List[str]
    all_measured_outcomes: int
    reported_outcomes: int
    positive_outcomes: int
    negative_outcomes: int
    effect_sizes: List[float]
    risk_level: BiasRiskLevel
    red_flags: List[str]
    recommendations: List[str]

class NegativeEvidenceDetector:
    """
    负向证据缺失探测器
    
    识别选择性报告风险和异常模式
    """
    
    # 警示信号阈值
    THRESHOLDS = {
        "positive_ratio": 0.9,      # 阳性结果比例阈值
        "large_effect_ratio": 0.8,  # 大效应量比例阈值
        "missing_outcome_ratio": 0.3,  # 缺失结局比例阈值
        "effect_size_threshold": 0.8   # 大效应量定义 (Cohen's d)
    }
    
    def __init__(self):
        self.analyses = []
    
    def analyze_study(
        self,
        paper_id: str,
        intervention: str,
        outcomes_data: List[Dict],
        methods_text: Optional[str] = None
    ) -> NegativeEvidenceAnalysis:
        """
        分析单篇研究的负向证据
        
        Args:
            paper_id: 文献ID
            intervention: 干预措施
            outcomes_data: 结局数据列表
            methods_text: Methods章节文本
            
        Returns:
            分析结果
        """
        # 统计结局
        total_outcomes = len(outcomes_data)
        reported_outcomes = sum(1 for o in outcomes_data if o.get("reported", True))
        missing_outcomes = total_outcomes - reported_outcomes
        
        positive_outcomes = sum(1 for o in outcomes_data if o.get("p_value", 1) < 0.05)
        negative_outcomes = reported_outcomes - positive_outcomes
        
        # 收集效应量
        effect_sizes = [o.get("effect_size", 0) for o in outcomes_data if o.get("effect_size")]
        
        # 检测警示信号
        red_flags = self._detect_red_flags(
            outcomes_data, positive_outcomes, negative_outcomes,
            reported_outcomes, missing_outcomes, effect_sizes
        )
        
        # 评估风险等级
        risk_level = self._assess_risk_level(red_flags)
        
        # 生成建议
        recommendations = self._generate_recommendations(red_flags, risk_level)
        
        analysis = NegativeEvidenceAnalysis(
            paper_id=paper_id,
            intervention=intervention,
            primary_outcomes=[o["name"] for o in outcomes_data if o.get("is_primary")],
            all_measured_outcomes=total_outcomes,
            reported_outcomes=reported_outcomes,
            positive_outcomes=positive_outcomes,
            negative_outcomes=negative_outcomes,
            effect_sizes=effect_sizes,
            risk_level=risk_level,
            red_flags=red_flags,
            recommendations=recommendations
        )
        
        self.analyses.append(analysis)
        return analysis
    
    def _detect_red_flags(
        self,
        outcomes: List[Dict],
        positive: int,
        negative: int,
        reported: int,
        missing: int,
        effect_sizes: List[float]
    ) -> List[str]:
        """检测警示信号"""
        flags = []
        
        # 信号1: 阳性结果比例过高
        if reported > 0:
            positive_ratio = positive / reported
            if positive_ratio >= self.THRESHOLDS["positive_ratio"]:
                flags.append(f"阳性结果比例过高 ({positive_ratio:.1%})")
        
        # 信号2: 大效应量过多
        if effect_sizes:
            large_effects = sum(1 for es in effect_sizes if abs(es) >= self.THRESHOLDS["effect_size_threshold"])
            large_effect_ratio = large_effects / len(effect_sizes)
            if large_effect_ratio >= self.THRESHOLDS["large_effect_ratio"]:
                flags.append(f"大效应量比例异常 ({large_effect_ratio:.1%})")
        
        # 信号3: 有缺失结局
        if reported > 0:
            missing_ratio = missing / (reported + missing)
            if missing_ratio >= self.THRESHOLDS["missing_outcome_ratio"]:
                flags.append(f"存在未报告结局 ({missing_ratio:.1%})")
        
        # 信号4: 副作用/不良事件报告不足
        if not any(o.get("is_adverse_event") for o in outcomes):
            flags.append("未报告不良事件数据")
        
        # 信号5: P值分布异常 (过多边界显著结果)
        p_values = [o.get("p_value", 1) for o in outcomes if o.get("p_value")]
        borderline_significant = sum(1 for p in p_values if 0.04 < p < 0.05)
        if p_values and borderline_significant / len(p_values) > 0.3:
            flags.append("P值边界显著结果过多")
        
        # 信号6: 效应量一致性过高 (不同结局效应量异常接近)
        if len(effect_sizes) >= 3:
            try:
                cv = statistics.stdev(effect_sizes) / abs(statistics.mean(effect_sizes))
                if cv < 0.1:  # 变异系数过小
                    flags.append("不同结局效应量异常一致")
            except:
                pass
        
        return flags
    
    def _assess_risk_level(self, red_flags: List[str]) -> BiasRiskLevel:
        """评估风险等级"""
        n_flags = len(red_flags)
        
        if n_flags >= 4:
            return BiasRiskLevel.CRITICAL
        elif n_flags == 3:
            return BiasRiskLevel.HIGH
        elif n_flags == 2:
            return BiasRiskLevel.MODERATE
        elif n_flags == 1:
            return BiasRiskLevel.LOW
        else:
            return BiasRiskLevel.MINIMAL
    
    def _generate_recommendations(
        self,
        red_flags: List[str],
        risk_level: BiasRiskLevel
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if risk_level in [BiasRiskLevel.CRITICAL, BiasRiskLevel.HIGH]:
            recommendations.append("⚠️ 该研究存在严重的选择性报告风险，需谨慎解读")
            recommendations.append("建议：在Evidence Audit Trail中明确标记风险等级")
        
        if "阳性结果比例过高" in str(red_flags):
            recommendations.append("建议：核对是否所有预设终点都被报告")
        
        if "未报告不良事件数据" in str(red_flags):
            recommendations.append("建议：联系作者获取不良事件数据")
        
        if "大效应量比例异常" in str(red_flags):
            recommendations.append("建议：评估是否存在过度乐观估计")
        
        return recommendations
```

---

### 2. 跨研究发表偏倚检测

```python
    def analyze_corpus_bias(
        self,
        analyses: Optional[List[NegativeEvidenceAnalysis]] = None
    ) -> Dict:
        """
        分析文献集合的发表偏倚
        
        检测:
        1. 漏斗图不对称 (小研究效应)
        2. 阳性结果率异常
        3. 效应量分布偏态
        """
        if analyses is None:
            analyses = self.analyses
        
        if len(analyses) < 5:
            return {"error": "文献数量不足，无法检测发表偏倚"}
        
        # 统计
        total_studies = len(analyses)
        high_risk_studies = sum(1 for a in analyses if a.risk_level in [BiasRiskLevel.CRITICAL, BiasRiskLevel.HIGH])
        
        # 阳性结果率
        positive_ratios = []
        for a in analyses:
            if a.reported_outcomes > 0:
                ratio = a.positive_outcomes / a.reported_outcomes
                positive_ratios.append(ratio)
        
        avg_positive_ratio = sum(positive_ratios) / len(positive_ratios) if positive_ratios else 0
        
        # 效应量分布
        all_effect_sizes = []
        for a in analyses:
            all_effect_sizes.extend(a.effect_sizes)
        
        # 检测发表偏倚信号
        bias_signals = []
        
        # 信号1: 整体阳性率过高
        if avg_positive_ratio > 0.75:
            bias_signals.append({
                "type": "high_positive_rate",
                "severity": "high",
                "description": f"整体阳性结果率{avg_positive_ratio:.1%}，高于预期",
                "interpretation": "可能存在文件抽屉效应 (file drawer effect)"
            })
        
        # 信号2: 高风险研究比例过高
        high_risk_ratio = high_risk_studies / total_studies
        if high_risk_ratio > 0.3:
            bias_signals.append({
                "type": "high_risk_study_prevalence",
                "severity": "moderate",
                "description": f"{high_risk_ratio:.1%}的研究存在高风险选择性报告",
                "interpretation": "该领域可能存在系统性报告偏倚"
            })
        
        # 信号3: 效应量异常偏大
        if all_effect_sizes:
            mean_es = sum(all_effect_sizes) / len(all_effect_sizes)
            large_effect_ratio = sum(1 for es in all_effect_sizes if abs(es) >= 0.8) / len(all_effect_sizes)
            if large_effect_ratio > 0.5 and mean_es > 0.6:
                bias_signals.append({
                    "type": "inflated_effect_sizes",
                    "severity": "high",
                    "description": f"平均效应量{mean_es:.2f}，大效应占比{large_effect_ratio:.1%}",
                    "interpretation": "可能存在发表偏倚，阴性/小效应研究未发表"
                })
        
        return {
            "total_studies": total_studies,
            "high_risk_studies": high_risk_studies,
            "average_positive_ratio": avg_positive_ratio,
            "mean_effect_size": sum(all_effect_sizes) / len(all_effect_sizes) if all_effect_sizes else 0,
            "bias_signals": bias_signals,
            "overall_assessment": self._assess_corpus_bias(bias_signals)
        }
    
    def _assess_corpus_bias(self, signals: List[Dict]) -> str:
        """评估整体偏倚风险"""
        if not signals:
            return "low"
        
        high_severity = sum(1 for s in signals if s["severity"] == "high")
        if high_severity >= 2:
            return "critical"
        elif high_severity == 1:
            return "high"
        
        return "moderate"
```

---

### 3. 机制合理性检查

```python
    def check_mechanistic_plausibility(
        self,
        intervention: str,
        outcomes: List[Dict],
        expected_side_effects: List[str]
    ) -> Dict:
        """
        检查机制合理性
        
        检测:
        - 理论上应观察到的副作用是否报告
        - "好得难以置信"的结果模式
        """
        alerts = []
        
        # 检查预期副作用是否报告
        reported_events = [o["name"].lower() for o in outcomes if o.get("is_adverse_event")]
        
        for expected in expected_side_effects:
            if not any(expected.lower() in reported.lower() for reported in reported_events):
                alerts.append({
                    "type": "missing_expected_side_effect",
                    "expected_effect": expected,
                    "severity": "high",
                    "message": f"理论上应观察到{expected}，但未报告，可能存在选择性报告"
                })
        
        # 检查"完美"结果模式
        if len(outcomes) >= 5:
            all_positive = all(o.get("p_value", 1) < 0.05 and o.get("effect_size", 0) > 0 
                            for o in outcomes if o.get("is_primary"))
            if all_positive:
                alerts.append({
                    "type": "too_good_to_be_true",
                    "severity": "critical",
                    "message": "所有主要终点均阳性且方向一致，这种模式极不寻常，强烈提示选择性报告"
                })
        
        return {
            "intervention": intervention,
            "expected_side_effects": expected_side_effects,
            "reported_adverse_events": reported_events,
            "missing_expected": len(alerts),
            "alerts": alerts,
            "plausibility_score": max(0, 100 - len(alerts) * 25)
        }
```

---

## Evidence Audit Trail 整合

```markdown
**[Negative Evidence Audit]** ⚠️ v2.4.0 新增
- **选择性报告风险**: HIGH
- **警示信号**:
  1. 阳性结果比例过高 (95%)
  2. 未报告不良事件数据
  3. 大效应量比例异常 (85%)
- **机制合理性**: ⚠️ 理论上应观察到感染并发症，但未报告
- **建议**:
  - 该研究存在严重的选择性报告风险
  - 建议联系作者获取完整终点数据
  - 在综述讨论中声明该限制
- **AI判断**: 🚨 **关键降级因素** - 该研究的阳性结论可信度存疑
```

---

## 使用示例

```python
from negative_evidence_detector import NegativeEvidenceDetector

detector = NegativeEvidenceDetector()

# 分析单篇研究
outcomes = [
    {"name": "Pain relief", "is_primary": True, "p_value": 0.001, "effect_size": 1.2},
    {"name": "Function improvement", "is_primary": True, "p_value": 0.002, "effect_size": 0.9},
    {"name": "Quality of life", "is_primary": False, "p_value": 0.003, "effect_size": 0.85},
    # 缺失不良事件数据...
]

analysis = detector.analyze_study(
    paper_id="Smith2023",
    intervention="New surgical technique",
    outcomes_data=outcomes
)

print(f"风险等级: {analysis.risk_level.value}")
print(f"警示信号: {analysis.red_flags}")
for rec in analysis.recommendations:
    print(f"建议: {rec}")

# 机制合理性检查
plausibility = detector.check_mechanistic_plausibility(
    intervention="New surgical technique",
    outcomes=outcomes,
    expected_side_effects=["infection", "bleeding", "nerve injury"]
)

if plausibility["alerts"]:
    print("⚠️ 机制合理性警示:")
    for alert in plausibility["alerts"]:
        print(f"  - {alert['message']}")

# 批量分析
all_analyses = [analysis1, analysis2, analysis3, ...]
corpus_analysis = detector.analyze_corpus_bias(all_analyses)

if corpus_analysis["bias_signals"]:
    print("🚨 发表偏倚信号:")
    for signal in corpus_analysis["bias_signals"]:
        print(f"  - {signal['description']}")
```

---

## 实现状态

- [x] 选择性报告风险检测
- [x] 跨研究发表偏倚分析
- [x] 机制合理性检查
- [x] 风险分级系统
- [x] Evidence Audit Trail 整合
- [ ] 自动P值分布分析 (v2.5.0)
- [ ] 漏斗图不对称检测 (v2.5.0)

---

*创建日期: 2026-03-12*  
*版本: v2.4.0*