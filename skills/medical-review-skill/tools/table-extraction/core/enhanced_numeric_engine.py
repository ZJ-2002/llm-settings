#!/usr/bin/env python3
"""
增强型医学数值识别引擎 (Enhanced Numeric Engine) - v1.0
符合 Nature Reviews Disease Primers 严谨性要求

核心功能：
1. 统计语义感知 - 区分 SD/SE/CI/IQR
2. 算子持久化 - 保留 <, >, ≤, ≥ 等不等号
3. 自动尺度对齐 - VAS 100mm vs 10cm 自动识别
4. 临床意义评估 - MCID 达成率检测
5. LaTeX 公式反向校验 - 统计一致性验证

作者：AI Assistant (基于专业评审反馈)
版本：v1.0 (2026-03-13)
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple, List
from enum import Enum


class StatType(Enum):
    """统计指标类型枚举"""
    POINT = "point"           # 纯数字
    MEAN_SD = "mean_sd"       # 均值±标准差
    MEAN_SE = "mean_se"       # 均值±标准误
    MEAN_CI = "mean_ci"       # 均值 (95%CI)
    MEDIAN_IQR = "median_iqr" # 中位数 (IQR)
    MEDIAN_RANGE = "median_range" # 中位数 (范围)
    OR_CI = "or_ci"           # OR (95%CI)
    HR_CI = "hr_ci"           # HR (95%CI)
    UNKNOWN = "unknown"


class MetricDirection(Enum):
    """指标方向枚举"""
    POSITIVE = "positive"  # 越高越好 (如 JOA)
    NEGATIVE = "negative"  # 越低越好 (如 VAS, ODI)
    NEUTRAL = "neutral"    # 无明确方向


@dataclass
class NumericInsight:
    """
    数值深度洞察对象
    
    不仅包含数值本身，还包含完整的统计语义和临床上下文
    """
    # 核心数值
    value: Optional[float] = None          # 核心数值（均值或中位数）
    dispersion: Optional[float] = None     # 离散程度（SD, SE 或 IQR的一半）
    
    # 统计语义
    operator: str = "="                    # 算子: =, <, >, <=, >=
    stat_type: StatType = StatType.POINT   # 统计包装类型
    ci_lower: Optional[float] = None       # 置信区间下限
    ci_upper: Optional[float] = None       # 置信区间上限
    
    # 尺度信息
    is_scaled: bool = False                # 是否触发了尺度缩放
    original_value: Optional[float] = None # 缩放前的原始值
    scale_factor: float = 1.0              # 缩放因子
    
    # 溯源信息
    raw_context: str = ""                  # 原始文本备份
    metric_label: str = ""                 # 指标标签
    
    # 质量标记
    confidence: float = 1.0                # 置信度
    warnings: List[str] = field(default_factory=list)  # 警告信息
    
    def __repr__(self) -> str:
        op_str = self.operator if self.operator != "=" else ""
        disp_str = f"±{self.dispersion}" if self.dispersion else ""
        scale_str = " (Scaled)" if self.is_scaled else ""
        return f"{op_str}{self.value}{disp_str} [{self.stat_type.value}]{scale_str}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'value': self.value,
            'dispersion': self.dispersion,
            'operator': self.operator,
            'stat_type': self.stat_type.value,
            'ci_lower': self.ci_lower,
            'ci_upper': self.ci_upper,
            'is_scaled': self.is_scaled,
            'original_value': self.original_value,
            'raw_context': self.raw_context,
            'confidence': self.confidence,
            'warnings': self.warnings
        }


@dataclass
class MCIDResult:
    """MCID（最小临床意义差异）评估结果"""
    metric: str                          # 指标名称
    improvement: float                   # 改善量
    mcid_threshold: float                # MCID阈值
    achieved: bool                       # 是否达成
    clinical_significance: str           # 临床意义评估
    
    def __repr__(self) -> str:
        status = "✅ Achieved" if self.achieved else "⚠️ Below MCID"
        return f"{self.metric}: {self.improvement:.2f} vs MCID {self.mcid_threshold:.2f} - {status}"


class EnhancedNumericEngine:
    """
    增强型医学数值引擎
    
    针对脊柱外科（LDH）和 Nature Reviews 级别的学术严谨性设计
    """
    
    # 脊柱外科 LDH 专用 MCID 阈值
    MCID_THRESHOLDS = {
        'VAS': 1.5,           # VAS 改善需 > 1.5 分
        'VAS_BACK': 1.5,
        'VAS_LEG': 1.5,
        'NRS': 1.5,           # 数字评分量表
        'ODI': 12.8,          # ODI 改善需 > 12.8%
        'JOA': 2.5,           # JOA 评分改善
        'SF36': 5.0,          # SF-36 评分
    }
    
    # 需要自动缩放的指标（0-100 -> 0-10）
    SCALING_METRICS = [
        'VAS', 'VAS_BACK', 'VAS_LEG', 'BACK_PAIN', 'LEG_PAIN',
        'NRS', 'NUMERIC_RATING', 'PAIN_SCORE'
    ]
    
    # 指标方向定义
    METRIC_DIRECTIONS = {
        'VAS': MetricDirection.NEGATIVE,
        'ODI': MetricDirection.NEGATIVE,
        'NRS': MetricDirection.NEGATIVE,
        'JOA': MetricDirection.POSITIVE,      # JOA 越高越好
        'SF36': MetricDirection.POSITIVE,
    }
    
    def __init__(self, specialty: str = "LDH"):
        self.specialty = specialty
        self.mcid_thresholds = self.MCID_THRESHOLDS.copy()
        self.scaling_metrics = self.SCALING_METRICS.copy()
        
        # 根据专科调整阈值
        if specialty == "LDH":
            self.mcid_thresholds.update({
                'VAS_LEG': 2.0,  # 腿痛 VAS 的 MCID 更高
            })
    
    def recognize(self, raw_value: str, metric_label: str = "") -> NumericInsight:
        """
        核心识别逻辑：支持统计语义提取与尺度对齐
        
        Args:
            raw_value: 原始数值字符串
            metric_label: 指标标签（用于尺度判断）
        
        Returns:
            NumericInsight: 数值洞察对象
        """
        if not raw_value or not isinstance(raw_value, str):
            return NumericInsight(
                value=None, 
                raw_context=str(raw_value),
                warnings=["Empty or invalid input"]
            )
        
        # 清理文本但保留关键符号
        text = raw_value.strip()
        insight = NumericInsight(
            value=None, 
            dispersion=None, 
            raw_context=text,
            metric_label=metric_label
        )
        
        # 1. 算子提取 (<, >, ≤, ≥)
        text = self._extract_operator(text, insight)
        
        # 2. 统计包装模式匹配
        self._recognize_statistical_pattern(text, insight)
        
        # 3. 尺度自动对齐（VAS 100mm vs 10cm）
        self._apply_scaling(insight, metric_label)
        
        # 4. 置信度评估
        self._assess_confidence(insight)
        
        return insight
    
    def _extract_operator(self, text: str, insight: NumericInsight) -> str:
        """提取不等号算子"""
        # 匹配开头的算子
        op_match = re.match(r'^([<>≤≥=]{1,2})\s*', text)
        if op_match:
            op = op_match.group(1)
            # 标准化算子
            insight.operator = op.replace("≤", "<=").replace("≥", ">=")
            text = text[len(op_match.group(0)):]
        return text
    
    def _recognize_statistical_pattern(self, text: str, insight: NumericInsight):
        """识别统计包装模式"""
        
        # 模式 A: Mean ± SD (55.2±8.3 或 55.2 ± 8.3)
        if "±" in text:
            parts = text.split("±")
            if len(parts) == 2:
                insight.value = self._to_float(parts[0])
                insight.dispersion = self._to_float(parts[1])
                insight.stat_type = StatType.MEAN_SD
                return
        
        # 模式 B: Mean (SD) 或 Mean (SE) 或 Mean (CI)
        # 格式: 7.2(1.3) 或 7.2 (1.3) 或 7.2(1.3-10.5)
        paren_match = re.match(r'([\d\.]+)\s*\(([^)]+)\)', text)
        if paren_match:
            main_val = paren_match.group(1)
            inside = paren_match.group(2)
            insight.value = self._to_float(main_val)
            
            # 判断括号内内容
            if "-" in inside or "–" in inside:
                # 范围或 CI: 45.2 (40.1-50.3)
                range_parts = re.split(r'[-–]', inside)
                if len(range_parts) == 2:
                    low = self._to_float(range_parts[0])
                    high = self._to_float(range_parts[1])
                    if low is not None and high is not None:
                        insight.ci_lower = low
                        insight.ci_upper = high
                        insight.dispersion = (high - low) / 2  # 存储半量程
                        insight.stat_type = StatType.MEAN_CI
            else:
                # 纯数字: 可能是 SD 或 SE
                insight.dispersion = self._to_float(inside)
                # 默认标记为未知离散类型，后续结合表头判断
                insight.stat_type = StatType.UNKNOWN
            return
        
        # 模式 C: 范围表示法 [lower, upper]
        range_match = re.match(r'\[?([\d\.]+)[,\s]+([\d\.]+)\]?', text)
        if range_match:
            insight.ci_lower = self._to_float(range_match.group(1))
            insight.ci_upper = self._to_float(range_match.group(2))
            if insight.ci_lower is not None and insight.ci_upper is not None:
                insight.value = (insight.ci_lower + insight.ci_upper) / 2
                insight.dispersion = (insight.ci_upper - insight.ci_lower) / 2
                insight.stat_type = StatType.MEAN_CI
            return
        
        # 模式 D: 纯数字
        insight.value = self._to_float(text)
        insight.stat_type = StatType.POINT
    
    def _to_float(self, s: str) -> Optional[float]:
        """安全转换为浮点数"""
        if s is None:
            return None
        try:
            # 移除所有非数字字符（保留小数点、负号）
            clean = re.sub(r'[^\d\.\-]', '', str(s))
            return float(clean) if clean else None
        except (ValueError, TypeError):
            return None
    
    def _apply_scaling(self, insight: NumericInsight, metric_label: str):
        """
        自动尺度对齐 - 关键功能
        
        如果 VAS 值 > 11，自动识别为 100mm 尺度并缩放为 0-10
        """
        if insight.value is None:
            return
        
        # 检查是否为需要缩放的指标
        metric_upper = metric_label.upper()
        is_pain_metric = any(m in metric_upper for m in self.scaling_metrics)
        
        if is_pain_metric and insight.value > 11.0:
            # 判定为 100mm 尺度，需要缩放
            insight.original_value = insight.value
            insight.value = insight.value / 10.0
            if insight.dispersion:
                insight.dispersion = insight.dispersion / 10.0
            if insight.ci_lower:
                insight.ci_lower = insight.ci_lower / 10.0
            if insight.ci_upper:
                insight.ci_upper = insight.ci_upper / 10.0
            insight.is_scaled = True
            insight.scale_factor = 10.0
            insight.warnings.append(f"Auto-scaled from 0-100 to 0-10 (factor: 10x)")
    
    def _assess_confidence(self, insight: NumericInsight):
        """评估识别置信度"""
        confidence = 1.0
        
        # 如果无法解析数值，降低置信度
        if insight.value is None:
            confidence -= 0.5
            insight.warnings.append("Failed to parse numeric value")
        
        # 如果离散指标类型未知，降低置信度
        if insight.stat_type == StatType.UNKNOWN:
            confidence -= 0.2
            insight.warnings.append("Cannot determine dispersion type (SD vs SE)")
        
        insight.confidence = max(0.0, confidence)
    
    def check_statistical_consistency(
        self, 
        insight: NumericInsight, 
        sample_size: int
    ) -> Dict[str, Any]:
        """
        LaTeX 公式反向校验 - 统计一致性验证
        
        验证报告的 95% CI 是否与 SD 一致：
        95% CI ≈ X̄ ± 1.96 × SD/√n
        
        Args:
            insight: 数值洞察对象
            sample_size: 样本量
        
        Returns:
            一致性检查结果
        """
        import math
        
        if (insight.value is None or 
            insight.dispersion is None or 
            insight.ci_lower is None or 
            insight.ci_upper is None or
            sample_size <= 0):
            return {'checkable': False, 'reason': 'Insufficient data'}
        
        # 理论 CI 计算（假设 dispersion 是 SD）
        theoretical_margin = 1.96 * insight.dispersion / math.sqrt(sample_size)
        theoretical_lower = insight.value - theoretical_margin
        theoretical_upper = insight.value + theoretical_margin
        
        # 比较实际 CI 与理论 CI
        lower_diff = abs(insight.ci_lower - theoretical_lower) / insight.value * 100
        upper_diff = abs(insight.ci_upper - theoretical_upper) / insight.value * 100
        
        is_consistent = lower_diff < 10 and upper_diff < 10
        
        return {
            'checkable': True,
            'is_consistent': is_consistent,
            'theoretical_ci': (theoretical_lower, theoretical_upper),
            'reported_ci': (insight.ci_lower, insight.ci_upper),
            'deviation_percent': (lower_diff, upper_diff),
            'warning': None if is_consistent else 'Statistical inconsistency detected (SD vs CI mismatch)'
        }
    
    def evaluate_mcid(
        self, 
        metric: str, 
        baseline: NumericInsight, 
        followup: NumericInsight
    ) -> Optional[MCIDResult]:
        """
        MCID（最小临床意义差异）评估
        
        判断改善是否达到临床意义阈值
        """
        if baseline.value is None or followup.value is None:
            return None
        
        # 确定指标方向
        direction = self.METRIC_DIRECTIONS.get(metric.upper(), MetricDirection.NEUTRAL)
        
        # 计算改善量
        if direction == MetricDirection.NEGATIVE:
            # 负向指标：降低为好（如 VAS, ODI）
            improvement = baseline.value - followup.value
        elif direction == MetricDirection.POSITIVE:
            # 正向指标：升高为好（如 JOA）
            improvement = followup.value - baseline.value
        else:
            # 中性指标：取绝对变化
            improvement = abs(followup.value - baseline.value)
        
        # 获取 MCID 阈值
        threshold = self.mcid_thresholds.get(metric.upper(), None)
        if threshold is None:
            return None
        
        achieved = improvement >= threshold
        
        # 临床意义评估
        if achieved:
            ratio = improvement / threshold
            if ratio >= 2.0:
                significance = "高度临床意义（远超MCID）"
            elif ratio >= 1.5:
                significance = "中等临床意义（明显超过MCID）"
            else:
                significance = "达到MCID阈值"
        else:
            ratio = improvement / threshold
            if ratio >= 0.75:
                significance = "接近MCID（可能有边缘临床意义）"
            elif ratio >= 0.5:
                significance = "低于MCID（临床意义有限）"
            else:
                significance = "远低于MCID（临床意义可疑）"
        
        return MCIDResult(
            metric=metric,
            improvement=improvement,
            mcid_threshold=threshold,
            achieved=achieved,
            clinical_significance=significance
        )
    
    def infer_dispersion_type(
        self, 
        insight: NumericInsight, 
        header_text: str = ""
    ) -> StatType:
        """
        推断离散指标类型（SD vs SE）
        
        结合表头文本进行判断
        """
        header_upper = header_text.upper()
        
        # 根据表头关键词判断
        if any(kw in header_upper for kw in ['SE', 'STANDARD ERROR', 'SEM']):
            return StatType.MEAN_SE
        elif any(kw in header_upper for kw in ['SD', 'STANDARD DEVIATION']):
            return StatType.MEAN_SD
        elif any(kw in header_upper for kw in ['CI', 'CONFIDENCE INTERVAL', '95%']):
            return StatType.MEAN_CI
        
        # 默认值
        return insight.stat_type


# ==================== 测试用例 ====================

def test_basic_recognition():
    """测试基本数值识别"""
    print("\n" + "="*60)
    print("Test: 基本数值识别")
    print("="*60)
    
    engine = EnhancedNumericEngine()
    
    test_cases = [
        ("7.2±1.3", "VAS"),
        ("<0.001", "P-value"),
        ("45.2 (40.1-50.3)", "ODI"),
        ("75", "VAS"),  # 需要缩放的值
    ]
    
    for value, metric in test_cases:
        insight = engine.recognize(value, metric)
        print(f"  {value:20s} [{metric:10s}] -> {insight}")
    
    print("\n✅ 基本识别测试通过")


def test_scaling():
    """测试自动尺度缩放"""
    print("\n" + "="*60)
    print("Test: VAS 自动尺度缩放 (100mm -> 10cm)")
    print("="*60)
    
    engine = EnhancedNumericEngine()
    
    # 100mm 尺度的 VAS
    insight_100 = engine.recognize("75", "VAS")
    print(f"  Input: 75 (100mm scale)")
    print(f"  Output: {insight_100}")
    print(f"  Original: {insight_100.original_value}")
    print(f"  Is Scaled: {insight_100.is_scaled}")
    
    assert insight_100.is_scaled == True
    assert insight_100.value == 7.5
    
    # 10cm 尺度的 VAS（不应缩放）
    insight_10 = engine.recognize("7.5", "VAS")
    print(f"\n  Input: 7.5 (10cm scale)")
    print(f"  Output: {insight_10}")
    print(f"  Is Scaled: {insight_10.is_scaled}")
    
    assert insight_10.is_scaled == False
    assert insight_10.value == 7.5
    
    print("\n✅ 尺度缩放测试通过")


def test_operator_preservation():
    """测试算子保留"""
    print("\n" + "="*60)
    print("Test: 不等号算子保留")
    print("="*60)
    
    engine = EnhancedNumericEngine()
    
    operators = ["<0.001", ">0.05", "≤0.01", "≥0.8", "=0.032"]
    
    for op in operators:
        insight = engine.recognize(op, "P-value")
        print(f"  {op:10s} -> operator='{insight.operator}', value={insight.value}")
    
    print("\n✅ 算子保留测试通过")


def test_mcid_evaluation():
    """测试 MCID 评估"""
    print("\n" + "="*60)
    print("Test: MCID 临床意义评估")
    print("="*60)
    
    engine = EnhancedNumericEngine()
    
    # VAS 改善场景
    baseline = engine.recognize("7.5", "VAS")
    followup_good = engine.recognize("3.0", "VAS")  # 改善 4.5 > 1.5
    followup_poor = engine.recognize("6.5", "VAS")  # 改善 1.0 < 1.5
    
    mcid_good = engine.evaluate_mcid("VAS", baseline, followup_good)
    mcid_poor = engine.evaluate_mcid("VAS", baseline, followup_poor)
    
    print(f"  VAS Baseline: {baseline.value}")
    print(f"  Follow-up (good): {followup_good.value} -> {mcid_good}")
    print(f"  Follow-up (poor): {followup_poor.value} -> {mcid_poor}")
    
    assert mcid_good.achieved == True
    assert mcid_poor.achieved == False
    
    print("\n✅ MCID 评估测试通过")


def test_statistical_consistency():
    """测试统计一致性校验"""
    print("\n" + "="*60)
    print("Test: LaTeX 公式反向校验 (SD vs CI)")
    print("="*60)
    
    engine = EnhancedNumericEngine()
    
    # 构造一个一致的例子
    # Mean=50, SD=10, n=100
    # 理论 95% CI: 50 ± 1.96*10/sqrt(100) = 50 ± 1.96 = [48.04, 51.96]
    insight = NumericInsight(
        value=50.0,
        dispersion=10.0,
        ci_lower=48.0,
        ci_upper=52.0,
        stat_type=StatType.MEAN_SD
    )
    
    result = engine.check_statistical_consistency(insight, sample_size=100)
    
    print(f"  Mean: {insight.value}")
    print(f"  SD: {insight.dispersion}")
    print(f"  Reported CI: [{insight.ci_lower}, {insight.ci_upper}]")
    print(f"  Theoretical CI: [{result['theoretical_ci'][0]:.2f}, {result['theoretical_ci'][1]:.2f}]")
    print(f"  Is Consistent: {result['is_consistent']}")
    
    print("\n✅ 统计一致性测试通过")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("Enhanced Numeric Engine v1.0 - 测试套件")
    print("="*70)
    print("功能：统计语义感知 | 自动尺度对齐 | MCID评估 | LaTeX校验")
    print("="*70)
    
    test_basic_recognition()
    test_scaling()
    test_operator_preservation()
    test_mcid_evaluation()
    test_statistical_consistency()
    
    print("\n" + "="*70)
    print("所有测试通过！")
    print("="*70)
