"""
MedianToMeanConverter - 中位数/四分位距转换引擎
TableSanitizer 扩展模块，用于 Meta 分析合规性

遵循 Meta 分析合规标准：
- Luo et al. (2018) 均值估算法
- Wan et al. (2014) 标准差估算法

使用场景：
当原始文献报告 Median (IQR) 而非 Mean (SD) 时，
使用此模块进行统计学校正转换，以纳入 Meta 分析。

参考文献：
1. Luo D, et al. (2018). Optimally estimating the sample mean from the sample size, 
   median, mid-range, and/or mid-quartile range. Stat Methods Med Res.
2. Wan X, et al. (2014). Estimating the sample mean and standard deviation from 
   the sample size, median, range and/or interquartile range. BMC Med Res Methodol.
"""

import numpy as np
import scipy.stats as stats
import re
from typing import Dict, Optional, Tuple, NamedTuple, Union, List
from dataclasses import dataclass
from enum import Enum


class ConversionMethod(Enum):
    """转换方法枚举"""
    LUO_WAN = "luo_wan"           # Luo-Wan 组合算法（推荐）
    WAN_ONLY = "wan_only"         # 仅 Wan 方法
    DIRECT = "direct"             # 直接取中位数（不推荐）


class DistributionType(Enum):
    """分布类型检测"""
    NORMAL = "normal"             # 正态分布
    SKEWED = "skewed"             # 偏态分布
    UNKNOWN = "unknown"           # 未知


@dataclass
class ConversionResult:
    """转换结果数据类"""
    mean: float                   # 估算均值
    sd: float                     # 估算标准差
    method: str                   # 使用的方法
    is_estimated: bool            # 是否为估算值
    original_median: float        # 原始中位数
    original_q1: float            # 原始Q1
    original_q3: float            # 原始Q3
    n: int                        # 样本量
    confidence: str               # 置信度 (high/medium/low)
    warning: Optional[str] = None # 警告信息
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "mean": self.mean,
            "sd": self.sd,
            "method": self.method,
            "is_estimated": self.is_estimated,
            "original_median": self.original_median,
            "original_q1": self.original_q1,
            "original_q3": self.original_q3,
            "n": self.n,
            "confidence": self.confidence,
            "warning": self.warning
        }
    
    def format_for_meta(self) -> str:
        """格式化为 Meta 分析输入格式"""
        return f"{self.mean:.2f}±{self.sd:.2f}"


@dataclass
class BatchConversionReport:
    """批量转换报告"""
    results: List[ConversionResult]
    estimated_ratio: float        # 估算数据占比
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int
    grade_imprecision_downgrade: bool  # 是否需要 GRADE 降级
    
    def get_summary(self) -> Dict:
        """获取汇总统计"""
        total = len(self.results)
        return {
            "total_converted": total,
            "estimated_ratio": self.estimated_ratio,
            "confidence_distribution": {
                "high": self.high_confidence_count,
                "medium": self.medium_confidence_count,
                "low": self.low_confidence_count
            },
            "grade_downgrade_recommended": self.grade_imprecision_downgrade
        }


class MedianToMeanConverter:
    """
    TableSanitizer 扩展模块：中位数/四分位距转换引擎
    
    核心功能：
    1. 将 Median (IQR) 转换为 Mean (SD) 以符合 Meta 分析要求
    2. 使用 Luo (2018) 和 Wan (2014) 估算法确保统计学校正
    3. 提供置信度评估和警告机制
    4. 支持批量转换和 GRADE 降级建议
    
    使用示例：
        converter = MedianToMeanConverter()
        
        # 单条转换
        result = converter.convert(n=85, median=1.5, q1=0.8, q3=2.5)
        print(result.format_for_meta())  # "1.52±1.28"
        
        # 从单元格文本解析
        result = converter.process_cell("1.5 (0.8-2.5)", n=85)
        
        # 批量转换
        studies = [
            {"n": 120, "median": 1.2, "q1": 0.5, "q3": 2.0},
            {"n": 85, "median": 1.5, "q1": 0.8, "q3": 2.5}
        ]
        report = converter.batch_convert(studies)
    """
    
    # 小样本阈值（样本量小于此值时置信度降低）
    SMALL_SAMPLE_THRESHOLD = 30
    
    # 极大 IQR 警告阈值（IQR/Median > 此值时标记为偏态）
    SKEWNESS_THRESHOLD = 1.5
    
    def __init__(self, method: ConversionMethod = ConversionMethod.LUO_WAN):
        """
        初始化转换器
        
        Args:
            method: 转换方法，默认 LUO_WAN
        """
        self.method = method
        self._stats_citation = "Luo et al. (2018) + Wan et al. (2014)"
    
    def convert(self, n: int, median: float, q1: float, q3: float,
                method: Optional[ConversionMethod] = None) -> ConversionResult:
        """
        核心转换逻辑：Median (IQR) → Mean (SD)
        
        Args:
            n: 样本量
            median: 中位数
            q1: 第25百分位数
            q3: 第75百分位数
            method: 可选，覆盖默认转换方法
            
        Returns:
            ConversionResult: 包含估算均值、标准差及元数据的结果对象
            
        Raises:
            ValueError: 当输入参数无效时
        """
        # 参数校验
        if n <= 0:
            raise ValueError(f"样本量必须大于0，当前: {n}")
        if not (q1 <= median <= q3):
            raise ValueError(f"数值顺序错误，应为 Q1({q1}) <= Median({median}) <= Q3({q3})")
        
        use_method = method or self.method
        warnings = []
        
        # 检测分布偏态
        iqr = q3 - q1
        if median != 0 and iqr / abs(median) > self.SKEWNESS_THRESHOLD:
            warnings.append(f"检测到高度偏态分布 (IQR/Median={iqr/abs(median):.2f})，估算准确性可能降低")
        
        # 小样本警告
        if n < self.SMALL_SAMPLE_THRESHOLD:
            warnings.append(f"小样本研究 (n={n})，估算标准差可能不够稳健")
        
        # 执行转换
        if use_method == ConversionMethod.LUO_WAN:
            mean, sd = self._luo_wan_conversion(n, median, q1, q3)
            method_name = "Luo-Wan Estimation"
        elif use_method == ConversionMethod.WAN_ONLY:
            mean, sd = self._wan_only_conversion(n, median, q1, q3)
            method_name = "Wan Estimation Only"
        else:
            mean, sd = median, iqr / 1.35  # 粗略估计
            method_name = "Direct Approximation (Not Recommended)"
            warnings.append("使用直接近似法，建议改用 Luo-Wan 方法")
        
        # 置信度评估
        confidence = self._assess_confidence(n, median, q1, q3, warnings)
        
        # 构建警告文本
        warning_text = " | ".join(warnings) if warnings else None
        
        return ConversionResult(
            mean=round(mean, 2),
            sd=round(sd, 2),
            method=method_name,
            is_estimated=True,
            original_median=median,
            original_q1=q1,
            original_q3=q3,
            n=n,
            confidence=confidence,
            warning=warning_text
        )
    
    def _luo_wan_conversion(self, n: int, median: float, q1: float, q3: float) -> Tuple[float, float]:
        """
        Luo (2018) + Wan (2014) 组合估算法
        
        算法说明：
        1. 均值估算使用 Luo et al. (2018) 的加权算法，
           在样本量小时更倾向于使用 (Q1+Q3)/2，样本量大时更倾向于 Median
           
        2. 标准差估算使用 Wan et al. (2014) 的正态分布修正公式，
           通过 Φ⁻¹ 函数修正样本量对 IQR 的影响
        """
        # Luo (2018) 均值估算
        # 权重 w = 4 / (4 + n^0.75)，动态平衡 Median 和 (Q1+Q3)/2
        w = 4 / (4 + n**0.75)
        estimated_mean = w * ((q1 + q3) / 2) + (1 - w) * median
        
        # Wan (2014) 标准差估算
        # 公式: SD ≈ (q3 - q1) / (2 * Φ⁻¹((0.75n - 0.125) / (n + 0.25)))
        norm_inv = stats.norm.ppf((0.75 * n - 0.125) / (n + 0.25))
        estimated_sd = (q3 - q1) / (2 * norm_inv)
        
        return estimated_mean, estimated_sd
    
    def _wan_only_conversion(self, n: int, median: float, q1: float, q3: float) -> Tuple[float, float]:
        """
        仅使用 Wan (2014) 方法
        均值 = (Q1 + Median + Q3) / 3
        标准差使用 Wan 公式
        """
        # 基础 Wan 均值估算（简单平均）
        estimated_mean = (q1 + median + q3) / 3
        
        # Wan 标准差估算
        norm_inv = stats.norm.ppf((0.75 * n - 0.125) / (n + 0.25))
        estimated_sd = (q3 - q1) / (2 * norm_inv)
        
        return estimated_mean, estimated_sd
    
    def _assess_confidence(self, n: int, median: float, q1: float, 
                          q3: float, warnings: List[str]) -> str:
        """评估转换结果的置信度"""
        if n >= 50 and len(warnings) == 0:
            return "high"
        elif n >= 30 or (n >= 20 and len(warnings) <= 1):
            return "medium"
        else:
            return "low"
    
    def process_cell(self, cell_text: str, n: int) -> Optional[ConversionResult]:
        """
        解析单元格文本并转换
        
        支持格式：
        - "15.0 (10.0-22.5)"  # 标准格式
        - "15.0 [10.0, 22.5]" # 方括号格式
        - "15.0 (10.0~22.5)"  # 波浪线格式
        - "median 15.0 (IQR 10.0-22.5)" # 带标签格式
        
        Args:
            cell_text: 单元格原始文本
            n: 样本量
            
        Returns:
            ConversionResult 或 None（解析失败时）
        """
        if not cell_text or not isinstance(cell_text, str):
            return None
        
        # 清理文本
        text = cell_text.strip().lower()
        
        # 移除常见标签
        text = re.sub(r'(median|med|m|iqr|range|q1-q3)\s*[:=]?\s*', '', text)
        
        # 匹配数值模式
        # 支持: "15.0 (10.0-22.5)", "15.0 [10.0, 22.5]", "15.0 (10.0~22.5)"
        patterns = [
            # 标准格式: median (q1-q3)
            r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-,~]\s*(-?\d+\.?\d*)\s*\)',
            # 方括号格式: median [q1, q3]
            r'(-?\d+\.?\d*)\s*\[\s*(-?\d+\.?\d*)\s*[-,~]\s*(-?\d+\.?\d*)\s*\]',
            # 带中位数标签: Median: 15.0 (10.0-22.5)
            r'(?:median|med|m)[:\s]+(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-,~]\s*(-?\d+\.?\d*)\s*\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    median = float(match.group(1))
                    q1 = float(match.group(2))
                    q3 = float(match.group(3))
                    
                    # 确保顺序正确（处理负数情况）
                    values = sorted([q1, median, q3])
                    q1, median, q3 = values[0], values[1], values[2]
                    
                    return self.convert(n, median, q1, q3)
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def batch_convert(self, studies: List[Dict[str, Union[int, float]]]) -> BatchConversionReport:
        """
        批量转换多个研究的数据
        
        Args:
            studies: 研究数据列表，每项包含 n, median, q1, q3
                    例如: [{"n": 85, "median": 1.5, "q1": 0.8, "q3": 2.5}, ...]
                    
        Returns:
            BatchConversionReport: 批量转换报告
        """
        results = []
        
        for study in studies:
            try:
                n = int(study.get('n', 0))
                median = float(study.get('median', study.get('med', 0)))
                q1 = float(study.get('q1', study.get('Q1', 0)))
                q3 = float(study.get('q3', study.get('Q3', 0)))
                
                result = self.convert(n, median, q1, q3)
                results.append(result)
            except (ValueError, TypeError) as e:
                # 记录转换失败的项
                results.append(ConversionResult(
                    mean=0, sd=0, method="FAILED", is_estimated=False,
                    original_median=0, original_q1=0, original_q3=0, n=0,
                    confidence="none", warning=f"转换失败: {str(e)}"
                ))
        
        # 统计汇总
        total = len(results)
        high_conf = sum(1 for r in results if r.confidence == "high")
        medium_conf = sum(1 for r in results if r.confidence == "medium")
        low_conf = sum(1 for r in results if r.confidence == "low")
        
        # 计算估算数据占比
        estimated_count = sum(1 for r in results if r.is_estimated)
        estimated_ratio = estimated_count / total if total > 0 else 0
        
        # GRADE 降级建议（估算占比 > 50% 时建议降级）
        grade_downgrade = estimated_ratio > 0.5
        
        return BatchConversionReport(
            results=results,
            estimated_ratio=estimated_ratio,
            high_confidence_count=high_conf,
            medium_confidence_count=medium_conf,
            low_confidence_count=low_conf,
            grade_imprecision_downgrade=grade_downgrade
        )
    
    def generate_conversion_note(self, result: ConversionResult) -> str:
        """
        生成转换说明文本（用于 Evidence Audit Trail）
        
        Returns:
            符合学术规范的转换说明文本
        """
        note = f"""
## 统计转换说明 (Statistical Conversion Note)

**原始数据**: Median (IQR) = {result.original_median} ({result.original_q1}-{result.original_q3})
**样本量**: n = {result.n}
**转换结果**: Mean ± SD = {result.format_for_meta()}
**转换方法**: {result.method}
**参考文献**: {self._stats_citation}
**置信度**: {result.confidence.upper()}
**估算标记**: {result.is_estimated}
"""
        if result.warning:
            note += f"\n**⚠️ 警告**: {result.warning}\n"
        
        note += """
**统计假设**: 
本转换假设数据服从正态分布或近似正态分布。
若原始数据高度偏态，估算结果可能存在偏差。
"""
        return note


# 便捷函数接口
def convert_median_to_mean(n: int, median: float, q1: float, q3: float) -> ConversionResult:
    """
    便捷函数：快速转换中位数到均值
    
    Example:
        >>> result = convert_median_to_mean(85, 1.5, 0.8, 2.5)
        >>> print(result.mean, result.sd)
        1.52 1.28
    """
    converter = MedianToMeanConverter()
    return converter.convert(n, median, q1, q3)


def batch_convert_studies(studies: List[Dict]) -> BatchConversionReport:
    """
    便捷函数：批量转换多个研究
    
    Example:
        >>> studies = [
        ...     {"n": 120, "median": 1.2, "q1": 0.5, "q3": 2.0},
        ...     {"n": 85, "median": 1.5, "q1": 0.8, "q3": 2.5}
        ... ]
        >>> report = batch_convert_studies(studies)
        >>> print(report.estimated_ratio)
    """
    converter = MedianToMeanConverter()
    return converter.batch_convert(studies)
