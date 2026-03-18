"""
SensitivityAnalyzer - 敏感性分析引擎
Medical Review Skill v2.6.0

功能：自动对比原始数据与估算数据对 Meta 分析结论的影响，
      识别"结论翻转（Conclusion Flip）"风险。

核心用途：
1. 验证合并效应量是否对"估算数据"（Median转换而来）具有依赖性
2. 检测剔除估算数据后结论是否发生逆转
3. 为投稿前检查提供统计学稳健性证据

统计方法：
- 逆方差加权 Meta 分析（Inverse Variance Method）
- 固定效应模型（Fixed-effect Model）
- 显著性水平默认 α = 0.05

输出：
- 全样本 vs 剔除估算数据后的效应量对比
- 结论翻转风险评估
- 投稿前检查报告建议
"""

import numpy as np
from scipy import stats
from typing import List, Dict, Any, Tuple, Optional, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import warnings


class ConclusionStatus(Enum):
    """结论状态枚举"""
    SIGNIFICANT = "significant"       # 显著 (p < alpha)
    NOT_SIGNIFICANT = "not_significant"  # 不显著 (p >= alpha)
    BORDERLINE = "borderline"         # 边缘 (alpha < p < 0.10)


class RiskLevel(Enum):
    """风险等级枚举"""
    CRITICAL = "CRITICAL"     # 结论翻转，极其危险
    HIGH = "HIGH"             # 效应方向改变或边缘显著
    MODERATE = "MODERATE"     # 数值变化较大但结论稳定
    LOW = "LOW"               # 结论稳健


@dataclass
class MetaAnalysisResult:
    """Meta 分析结果"""
    pooled_effect: float      # 合并效应量
    pooled_se: float          # 合并标准误
    z_score: float            # Z 值
    p_value: float            # P 值
    ci_lower: float           # 95% CI 下限
    ci_upper: float           # 95% CI 上限
    n_studies: int            # 纳入研究数
    heterogeneity_i2: Optional[float] = None  # I² 异质性
    
    def get_conclusion_status(self, alpha: float = 0.05) -> ConclusionStatus:
        """获取结论状态"""
        if self.p_value < alpha:
            return ConclusionStatus.SIGNIFICANT
        elif self.p_value < 0.10:
            return ConclusionStatus.BORDERLINE
        else:
            return ConclusionStatus.NOT_SIGNIFICANT
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pooled_effect": round(self.pooled_effect, 3),
            "pooled_se": round(self.pooled_se, 3),
            "z_score": round(self.z_score, 3),
            "p_value": round(self.p_value, 4),
            "ci_95": f"[{round(self.ci_lower, 3)}, {round(self.ci_upper, 3)}]",
            "n_studies": self.n_studies,
            "i2": round(self.heterogeneity_i2, 1) if self.heterogeneity_i2 else None,
            "conclusion": self.get_conclusion_status().value
        }


@dataclass
class SensitivityReport:
    """敏感性分析报告"""
    # 全样本分析结果
    full_analysis: MetaAnalysisResult
    
    # 剔除估算数据后的分析结果
    sensitivity_analysis: Optional[MetaAnalysisResult]
    
    # 风险评估
    conclusion_flip: bool
    risk_level: RiskLevel
    
    # 详细信息
    alpha: float
    n_total: int
    n_estimated: int
    n_original: int
    
    # 建议文本
    warning_message: str
    recommendation: str
    
    # 对比数据
    effect_change_pct: Optional[float] = None  # 效应量变化百分比
    p_value_change: Optional[float] = None     # P值变化
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "full_analysis": self.full_analysis.to_dict(),
            "sensitivity_analysis": self.sensitivity_analysis.to_dict() if self.sensitivity_analysis else None,
            "risk_assessment": {
                "conclusion_flip": self.conclusion_flip,
                "risk_level": self.risk_level.value,
                "warning": self.warning_message
            },
            "study_counts": {
                "total": self.n_total,
                "estimated": self.n_estimated,
                "original": self.n_original
            },
            "changes": {
                "effect_change_pct": round(self.effect_change_pct, 2) if self.effect_change_pct else None,
                "p_value_change": round(self.p_value_change, 4) if self.p_value_change else None
            },
            "recommendation": self.recommendation
        }
    
    def generate_markdown_report(self) -> str:
        """生成 Markdown 格式的报告"""
        report = f"""## 敏感性分析报告 (Sensitivity Analysis Report)

### 研究纳入情况
| 类别 | 数量 |
|------|------|
| 总研究数 | {self.n_total} |
| 原始均值数据 | {self.n_original} |
| 估算数据 (Median转换) | {self.n_estimated} |
| 估算占比 | {self.n_estimated/self.n_total*100:.1f}% |

### Meta 分析结果对比

#### 全样本分析 (Full Analysis)
| 指标 | 数值 |
|------|------|
| 合并效应量 | {self.full_analysis.pooled_effect:.3f} |
| 标准误 | {self.full_analysis.pooled_se:.3f} |
| 95% CI | [{self.full_analysis.ci_lower:.3f}, {self.full_analysis.ci_upper:.3f}] |
| Z 值 | {self.full_analysis.z_score:.3f} |
| P 值 | {self.full_analysis.p_value:.4f} |
| 结论 | {self._format_conclusion(self.full_analysis)} |

"""
        if self.sensitivity_analysis:
            report += f"""#### 剔除估算数据后 (Sensitivity Analysis)
| 指标 | 数值 |
|------|------|
| 合并效应量 | {self.sensitivity_analysis.pooled_effect:.3f} |
| 标准误 | {self.sensitivity_analysis.pooled_se:.3f} |
| 95% CI | [{self.sensitivity_analysis.ci_lower:.3f}, {self.sensitivity_analysis.ci_upper:.3f}] |
| Z 值 | {self.sensitivity_analysis.z_score:.3f} |
| P 值 | {self.sensitivity_analysis.p_value:.4f} |
| 结论 | {self._format_conclusion(self.sensitivity_analysis)} |

### 变化幅度
| 指标 | 变化 |
|------|------|
| 效应量变化 | {self.effect_change_pct:+.1f}% |
| P值变化 | {self.p_value_change:+.4f} |
"""
        
        report += f"""
### 风险评估
**风险等级**: {self.risk_level.value}

**⚠️ 警告**: {self.warning_message}

### 建议
{self.recommendation}

---
*分析方法: 逆方差加权固定效应模型*
*显著性水平: α = {self.alpha}*
"""
        return report
    
    def _format_conclusion(self, result: MetaAnalysisResult) -> str:
        """格式化结论文本"""
        status = result.get_conclusion_status(self.alpha)
        if status == ConclusionStatus.SIGNIFICANT:
            return f"显著 (p={result.p_value:.4f})"
        elif status == ConclusionStatus.BORDERLINE:
            return f"边缘显著 (p={result.p_value:.4f})"
        else:
            return f"不显著 (p={result.p_value:.4f})"


class SensitivityAnalyzer:
    """
    敏感性分析引擎
    
    核心功能：
    1. 执行标准逆方差加权 Meta 分析
    2. 对比全样本 vs 剔除估算数据后的结果
    3. 检测结论翻转风险
    4. 生成投稿前检查报告
    
    使用示例：
        analyzer = SensitivityAnalyzer(alpha=0.05)
        
        studies = [
            {"id": "Study_A", "es": 1.2, "se": 0.5, "is_estimated": False},
            {"id": "Study_B", "es": 1.5, "se": 0.6, "is_estimated": True},
            {"id": "Study_C", "es": 2.1, "se": 0.8, "is_estimated": True}
        ]
        
        report = analyzer.perform_check(studies)
        print(report.generate_markdown_report())
    """
    
    def __init__(self, alpha: float = 0.05, model: str = "fixed"):
        """
        初始化分析器
        
        Args:
            alpha: 显著性水平，默认 0.05
            model: Meta 分析模型，"fixed" 或 "random"
        """
        self.alpha = alpha
        self.model = model
    
    def _meta_analysis(self, effects: np.ndarray, ses: np.ndarray) -> MetaAnalysisResult:
        """
        执行逆方差加权 Meta 分析
        
        公式：
        - 权重: w_i = 1 / SE_i²
        - 合并效应量: ES_pooled = Σ(w_i × ES_i) / Σw_i
        - 合并标准误: SE_pooled = 1/√(Σw_i)
        - Z 值: Z = ES_pooled / SE_pooled
        """
        # 检查输入
        if len(effects) == 0 or len(ses) == 0:
            raise ValueError("效应量和标准误数组不能为空")
        if np.any(ses <= 0):
            raise ValueError("标准误必须为正数")
        
        # 计算权重（逆方差）
        weights = 1 / (ses ** 2)
        
        # 合并效应量（加权平均）
        pooled_effect = np.sum(effects * weights) / np.sum(weights)
        
        # 合并标准误
        pooled_se = np.sqrt(1 / np.sum(weights))
        
        # Z 值和 P 值
        z_score = pooled_effect / pooled_se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        # 95% 置信区间
        ci_lower = pooled_effect - 1.96 * pooled_se
        ci_upper = pooled_effect + 1.96 * pooled_se
        
        # 计算 I² 异质性（简化计算）
        q_stat = np.sum(weights * (effects - pooled_effect) ** 2)
        df = len(effects) - 1
        i2 = max(0, (q_stat - df) / q_stat * 100) if q_stat > 0 else 0
        
        return MetaAnalysisResult(
            pooled_effect=pooled_effect,
            pooled_se=pooled_se,
            z_score=z_score,
            p_value=p_value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            n_studies=len(effects),
            heterogeneity_i2=i2
        )
    
    def perform_check(self, studies: List[Dict[str, Any]]) -> SensitivityReport:
        """
        执行敏感性检查
        
        Args:
            studies: 研究数据列表，每项包含：
                    - id: 研究标识
                    - es: 效应量 (effect size)
                    - se: 标准误 (standard error)
                    - is_estimated: 是否为估算数据（Median转换）
                    
        Returns:
            SensitivityReport: 敏感性分析报告
        """
        if not studies:
            raise ValueError("研究列表不能为空")
        
        # 提取数据
        all_effects = np.array([s['es'] for s in studies])
        all_ses = np.array([s['se'] for s in studies])
        
        # 1. 全样本分析
        full_result = self._meta_analysis(all_effects, all_ses)
        full_conclusion = full_result.get_conclusion_status(self.alpha)
        
        # 2. 剔除估算数据后的分析
        clean_studies = [s for s in studies if not s.get('is_estimated', False)]
        
        if len(clean_studies) == 0:
            # 没有原始数据，无法进行敏感性分析
            return SensitivityReport(
                full_analysis=full_result,
                sensitivity_analysis=None,
                conclusion_flip=True,  # 视为高风险
                risk_level=RiskLevel.CRITICAL,
                alpha=self.alpha,
                n_total=len(studies),
                n_estimated=len(studies),
                n_original=0,
                warning_message="⚠️ 所有数据均为估算数据，无法进行敏感性分析。结论极度不可靠！",
                recommendation="建议获取原始报告 Mean±SD 的文献，或改用非参数 Meta 分析方法。",
                effect_change_pct=None,
                p_value_change=None
            )
        
        if len(clean_studies) == len(studies):
            # 没有估算数据
            return SensitivityReport(
                full_analysis=full_result,
                sensitivity_analysis=full_result,
                conclusion_flip=False,
                risk_level=RiskLevel.LOW,
                alpha=self.alpha,
                n_total=len(studies),
                n_estimated=0,
                n_original=len(studies),
                warning_message="✅ 所有数据均为原始 Mean±SD，无估算数据。",
                recommendation="结论稳健，可正常投稿。",
                effect_change_pct=0.0,
                p_value_change=0.0
            )
        
        # 执行剔除估算数据后的分析
        clean_effects = np.array([s['es'] for s in clean_studies])
        clean_ses = np.array([s['se'] for s in clean_studies])
        sens_result = self._meta_analysis(clean_effects, clean_ses)
        sens_conclusion = sens_result.get_conclusion_status(self.alpha)
        
        # 3. 风险评估逻辑
        conclusion_flip = False
        risk_level = RiskLevel.LOW
        warning = ""
        recommendation = ""
        
        # 情况 A: 显著性逆转
        if (full_result.p_value < self.alpha) != (sens_result.p_value < self.alpha):
            conclusion_flip = True
            risk_level = RiskLevel.CRITICAL
            if full_result.p_value < self.alpha:
                warning = "⚠️ 结论翻转风险极高！剔除估算数据后，统计学显著性丢失（p > 0.05）。"
                recommendation = """
**强烈建议**：
1. 在讨论部分明确说明这一局限性
2. 结论表述需极度审慎，避免绝对化
3. 考虑补充检索原始报告 Mean±SD 的文献
4. 必要时声明该结论仅适用于报告 Mean±SD 的研究人群
"""
            else:
                warning = "⚠️ 发现异常：全样本不显著，但剔除估算数据后变得显著。"
                recommendation = "建议检查估算数据的方向和权重，可能存在异常值。"
        
        # 情况 B: 效应方向逆转
        elif np.sign(full_result.pooled_effect) != np.sign(sens_result.pooled_effect):
            conclusion_flip = True
            risk_level = RiskLevel.CRITICAL
            warning = "⚠️ 效应方向发生逆转！剔除估算数据后，效应方向完全相反。"
            recommendation = """
**紧急建议**：
1. 立即停止投稿，重新审查数据提取过程
2. 检查估算数据是否存在系统性偏差
3. 考虑重新设计 Meta 分析方案
"""
        
        # 情况 C: 边缘显著
        elif sens_conclusion == ConclusionStatus.BORDERLINE:
            risk_level = RiskLevel.HIGH
            warning = "⚠️ 剔除估算数据后，结论处于边缘显著状态（0.05 < p < 0.10）。"
            recommendation = """
**建议**：
1. 在讨论中说明结论的脆弱性
2. 建议进行更多原始数据研究以确认结论
3. 投稿时准备应对审稿人对此的质疑
"""
        
        # 情况 D: 数值变化较大但结论稳定
        else:
            effect_change = abs((sens_result.pooled_effect - full_result.pooled_effect) / full_result.pooled_effect * 100) if full_result.pooled_effect != 0 else 0
            p_change = abs(sens_result.p_value - full_result.p_value)
            
            if effect_change > 30:
                risk_level = RiskLevel.MODERATE
                warning = f"⚠️ 效应量变化较大（{effect_change:.1f}%），但结论方向保持一致。"
                recommendation = "建议在讨论中提及估算数据对效应量大小的影响。"
            else:
                warning = "✅ 敏感性测试通过，结论稳健。剔除估算数据后结论未发生实质性改变。"
                recommendation = "可正常投稿，建议常规提及数据来源情况。"
            
            # 计算变化百分比
            effect_change_pct = effect_change
            p_value_change = p_change
        
        # 计算变化（如果没有设置）
        if effect_change_pct is None:
            effect_change_pct = abs((sens_result.pooled_effect - full_result.pooled_effect) / full_result.pooled_effect * 100) if full_result.pooled_effect != 0 else 0
        if p_value_change is None:
            p_value_change = abs(sens_result.p_value - full_result.p_value)
        
        return SensitivityReport(
            full_analysis=full_result,
            sensitivity_analysis=sens_result,
            conclusion_flip=conclusion_flip,
            risk_level=risk_level,
            alpha=self.alpha,
            n_total=len(studies),
            n_estimated=len(studies) - len(clean_studies),
            n_original=len(clean_studies),
            warning_message=warning,
            recommendation=recommendation,
            effect_change_pct=effect_change_pct,
            p_value_change=p_value_change
        )
    
    def check_single_study_impact(self, studies: List[Dict[str, Any]], 
                                   target_id: str) -> Dict[str, Any]:
        """
        检查单个研究的影响（留一法）
        
        Args:
            studies: 所有研究数据
            target_id: 目标研究 ID
            
        Returns:
            该研究对总体结论的影响评估
        """
        # 全样本分析
        full_effects = np.array([s['es'] for s in studies])
        full_ses = np.array([s['se'] for s in studies])
        full_result = self._meta_analysis(full_effects, full_ses)
        
        # 剔除目标研究后的分析
        reduced_studies = [s for s in studies if s.get('id') != target_id]
        if len(reduced_studies) == 0:
            return {"error": "无法剔除唯一的研究"}
        
        reduced_effects = np.array([s['es'] for s in reduced_studies])
        reduced_ses = np.array([s['se'] for s in reduced_studies])
        reduced_result = self._meta_analysis(reduced_effects, reduced_ses)
        
        # 计算影响
        effect_change = abs((reduced_result.pooled_effect - full_result.pooled_effect) / full_result.pooled_effect * 100) if full_result.pooled_effect != 0 else 0
        
        return {
            "study_id": target_id,
            "impact_on_effect": round(effect_change, 2),
            "original_p": round(full_result.p_value, 4),
            "reduced_p": round(reduced_result.p_value, 4),
            "significance_changed": (full_result.p_value < self.alpha) != (reduced_result.p_value < self.alpha),
            "is_influential": effect_change > 20  # 影响超过20%视为高影响
        }


# 便捷函数接口
def perform_sensitivity_analysis(studies: List[Dict[str, Any]], 
                                  alpha: float = 0.05) -> SensitivityReport:
    """
    便捷函数：快速执行敏感性分析
    
    Example:
        >>> studies = [
        ...     {"id": "A", "es": 1.2, "se": 0.5, "is_estimated": False},
        ...     {"id": "B", "es": 1.5, "se": 0.6, "is_estimated": True},
        ...     {"id": "C", "es": 2.1, "se": 0.8, "is_estimated": True}
        ... ]
        >>> report = perform_sensitivity_analysis(studies)
        >>> print(report.risk_level)
    """
    analyzer = SensitivityAnalyzer(alpha=alpha)
    return analyzer.perform_check(studies)


def check_conclusion_robustness(original_p: float, 
                                 sensitivity_p: float, 
                                 alpha: float = 0.05) -> bool:
    """
    快速检查结论稳健性
    
    Returns:
        True if conclusion is robust, False if flipped
    """
    return (original_p < alpha) == (sensitivity_p < alpha)
