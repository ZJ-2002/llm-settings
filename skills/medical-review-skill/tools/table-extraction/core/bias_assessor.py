#!/usr/bin/env python3
"""
Cochrane RoB 2.0 自动化偏倚风险评估模块 (Bias Assessor) - v1.0

基于 Cochrane Risk of Bias 2.0 工具自动化评估五个核心领域：
- D1: 随机化过程
- D2: 偏离既定干预
- D3: 缺失结局数据
- D4: 结局测量
- D5: 选择性报告结果

针对脊柱外科（LDH）领域优化：
- 失访率红线阈值（10%/20%）
- 手术盲法不可行时的特殊处理
- 客观 vs 主观指标的风险差异化评估

作者：AI Assistant (基于专业评审反馈)
版本：v1.0 (2026-03-13)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class RiskLevel(Enum):
    """偏倚风险等级"""
    LOW = "Low Risk"
    SOME_CONCERNS = "Some Concerns"
    HIGH = "High Risk"
    
    def __repr__(self):
        emoji_map = {
            RiskLevel.LOW: "🟢",
            RiskLevel.SOME_CONCERNS: "🟡",
            RiskLevel.HIGH: "🔴"
        }
        return f"{emoji_map.get(self, '⚪')} {self.value}"


class Domain(Enum):
    """RoB 2.0 五个核心领域"""
    D1_RANDOMIZATION = "D1_Randomization"
    D2_DEVIATIONS = "D2_Deviations"
    D3_MISSING_DATA = "D3_MissingData"
    D4_MEASUREMENT = "D4_Measurement"
    D5_SELECTIVE_REPORTING = "D5_SelectiveReporting"


@dataclass
class BiasJudgment:
    """单个领域的偏倚判断"""
    domain: Domain
    risk_level: RiskLevel
    reason: str
    evidence_anchor: str  # 对应原文的硬锚点数据
    confidence: float = 1.0  # 判断置信度
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'domain': self.domain.value,
            'risk_level': self.risk_level.value,
            'reason': self.reason,
            'evidence_anchor': self.evidence_anchor,
            'confidence': self.confidence
        }


@dataclass
class RoBAssessment:
    """完整的 RoB 2.0 评估结果"""
    study_id: str
    overall_risk: RiskLevel
    domain_judgments: Dict[Domain, BiasJudgment] = field(default_factory=dict)
    summary_reason: str = ""
    
    def get_domain(self, domain: Domain) -> Optional[BiasJudgment]:
        return self.domain_judgments.get(domain)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'study_id': self.study_id,
            'overall_risk': self.overall_risk.value,
            'summary_reason': self.summary_reason,
            'domains': {
                d.value: j.to_dict() 
                for d, j in self.domain_judgments.items()
            }
        }


class BiasAssessor:
    """
    基于 Cochrane RoB 2.0 的自动化偏倚风险评估模块
    
    特别针对脊柱外科（LDH）领域优化：
    - 微创转开放手术的偏离检测
    - 主观指标（VAS/ODI）在非盲法研究中的风险权重
    - 影像学科研（MRI/CT）的客观指标优势
    """
    
    # 脊柱外科失访率红线阈值
    ATTRITION_THRESHOLDS = {
        'concerns': 0.10,  # 10% 触发 Some Concerns
        'critical': 0.20   # 20% 触发 High Risk
    }
    
    # 基线不平衡阈值
    BASELINE_IMBALANCE_THRESHOLDS = {
        'age': 15,      # 年龄差异 > 15岁
        'bmi': 10,      # BMI 差异 > 10
        'vas': 2.0,     # VAS 差异 > 2分
    }
    
    # 指标主客观分类（用于 D4 评估）
    SUBJECTIVE_OUTCOMES = [
        'VAS', 'ODI', 'JOA', 'SF36', 'NRS',
        'BACK_PAIN', 'LEG_PAIN', 'SATISFACTION'
    ]
    
    OBJECTIVE_OUTCOMES = [
        'CANAL_AREA', 'DISC_HEIGHT', 'RANGE_OF_MOTION',
        'FUSION_RATE', 'REOPERATION', 'COMPLICATION'
    ]
    
    def __init__(self, specialty: str = "LDH"):
        self.specialty = specialty
        self.attrition_thresholds = self.ATTRITION_THRESHOLDS.copy()
        self.baseline_thresholds = self.BASELINE_IMBALANCE_THRESHOLDS.copy()
    
    def assess(
        self, 
        study_id: str,
        study_metadata: Dict[str, Any], 
        extracted_data: Dict[str, Any]
    ) -> RoBAssessment:
        """
        执行完整的 RoB 2.0 评估
        
        Args:
            study_id: 研究标识
            study_metadata: 研究元数据（设计、盲法、注册等）
            extracted_data: 提取的数据（基线、随访、样本量等）
        
        Returns:
            RoBAssessment: 完整评估结果
        """
        domain_judgments = {}
        
        # D1: 随机化过程评估
        domain_judgments[Domain.D1_RANDOMIZATION] = self._assess_randomization(
            study_metadata, extracted_data
        )
        
        # D2: 偏离既定干预评估
        domain_judgments[Domain.D2_DEVIATIONS] = self._assess_deviations(
            study_metadata, extracted_data
        )
        
        # D3: 缺失结局数据评估
        domain_judgments[Domain.D3_MISSING_DATA] = self._assess_missing_data(
            study_metadata, extracted_data
        )
        
        # D4: 结局测量评估
        domain_judgments[Domain.D4_MEASUREMENT] = self._assess_measurement(
            study_metadata, extracted_data
        )
        
        # D5: 选择性报告评估
        domain_judgments[Domain.D5_SELECTIVE_REPORTING] = self._assess_selective_reporting(
            study_metadata, extracted_data
        )
        
        # 计算总体风险
        overall_risk = self._calculate_overall_risk(domain_judgments)
        
        # 生成总结理由
        summary = self._generate_summary(study_id, domain_judgments, overall_risk)
        
        return RoBAssessment(
            study_id=study_id,
            overall_risk=overall_risk,
            domain_judgments=domain_judgments,
            summary_reason=summary
        )
    
    def _assess_randomization(
        self, 
        metadata: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> BiasJudgment:
        """
        D1: 随机化过程评估
        
        评估要点：
        1. 随机序列生成是否充分
        2. 分配隐藏是否充分
        3. 基线平衡性
        """
        evidence_parts = []
        
        # 检查基线不平衡
        baseline_data = data.get('baseline', {})
        imbalances = []
        
        for param, threshold in self.baseline_thresholds.items():
            if param in baseline_data:
                diff = baseline_data[param].get('difference', 0)
                if abs(diff) > threshold:
                    imbalances.append(f"{param.upper()}差异{diff:.1f}")
        
        # 判断风险等级
        if imbalances:
            risk = RiskLevel.SOME_CONCERNS
            reason = f"检测到基线不平衡: {', '.join(imbalances)}"
            evidence_parts.append(f"基线数据: {baseline_data}")
        else:
            # 检查随机化方法
            randomization = metadata.get('randomization_method', '').upper()
            allocation = metadata.get('allocation_concealment', '').upper()
            
            if any(m in randomization for m in ['COMPUTER', 'RANDOM', 'BLOCK']):
                if any(m in allocation for m in ['CENTRAL', 'PHARMACY', 'SEQUENTIAL']):
                    risk = RiskLevel.LOW
                    reason = "适当的随机序列生成和分配隐藏"
                else:
                    risk = RiskLevel.SOME_CONCERNS
                    reason = "随机化方法适当，但分配隐藏不明确"
            else:
                risk = RiskLevel.SOME_CONCERNS
                reason = "随机化方法描述不充分"
        
        return BiasJudgment(
            domain=Domain.D1_RANDOMIZATION,
            risk_level=risk,
            reason=reason,
            evidence_anchor="; ".join(evidence_parts) if evidence_parts else "Methods section"
        )
    
    def _assess_deviations(
        self, 
        metadata: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> BiasJudgment:
        """
        D2: 偏离既定干预评估
        
        脊柱外科特殊考量：
        - 微创转开放手术的转换率
        - 意向性治疗分析（ITT）执行情况
        """
        evidence_parts = []
        
        # 检查 ITT 分析
        itt_analysis = metadata.get('itt_analysis', False)
        
        # 检查转换率（如 PELD 转开放）
        conversion_rate = data.get('conversion_rate', 0)
        
        if itt_analysis:
            if conversion_rate > 0.10:  # 转换率 > 10%
                risk = RiskLevel.SOME_CONCERNS
                reason = f"ITT分析执行，但转换率较高({conversion_rate:.1%})"
            else:
                risk = RiskLevel.LOW
                reason = "适当的ITT分析执行"
        else:
            # 没有 ITT 分析
            per_protocol_n = data.get('per_protocol_n', 0)
            randomized_n = data.get('randomized_n', 1)
            dropout_rate = 1 - (per_protocol_n / randomized_n) if randomized_n > 0 else 0
            
            if dropout_rate > 0.10:
                risk = RiskLevel.HIGH
                reason = f"无ITT分析且脱落率较高({dropout_rate:.1%})"
            else:
                risk = RiskLevel.SOME_CONCERNS
                reason = "无ITT分析，但脱落率较低"
        
        evidence_parts.append(f"ITT: {itt_analysis}, Conversion: {conversion_rate:.1%}")
        
        return BiasJudgment(
            domain=Domain.D2_DEVIATIONS,
            risk_level=risk,
            reason=reason,
            evidence_anchor="; ".join(evidence_parts)
        )
    
    def _assess_missing_data(
        self, 
        metadata: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> BiasJudgment:
        """
        D3: 缺失结局数据评估
        
        基于失访率计算：
        - < 10%: Low Risk
        - 10-20%: Some Concerns
        - > 20%: High Risk
        """
        evidence_parts = []
        
        # 获取样本量信息
        n_randomized = data.get('n_randomized', 0)
        n_completed = data.get('n_completed', 0)
        
        if n_randomized > 0 and n_completed > 0:
            attrition_rate = (n_randomized - n_completed) / n_randomized
            evidence_parts.append(f"n_randomized={n_randomized}, n_completed={n_completed}")
            
            if attrition_rate > self.attrition_thresholds['critical']:
                risk = RiskLevel.HIGH
                reason = f"失访率过高 ({attrition_rate:.1%} > 20%)"
            elif attrition_rate > self.attrition_thresholds['concerns']:
                risk = RiskLevel.SOME_CONCERNS
                reason = f"检测到显著失访 ({attrition_rate:.1%} > 10%)"
            else:
                risk = RiskLevel.LOW
                reason = f"失访率在可接受范围内 ({attrition_rate:.1%})"
        else:
            # 无法计算失访率
            risk = RiskLevel.SOME_CONCERNS
            reason = "样本量信息不完整，无法评估失访率"
            attrition_rate = None
        
        return BiasJudgment(
            domain=Domain.D3_MISSING_DATA,
            risk_level=risk,
            reason=reason,
            evidence_anchor=f"Attrition: {attrition_rate:.1%}" if attrition_rate else "Missing data"
        )
    
    def _assess_measurement(
        self, 
        metadata: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> BiasJudgment:
        """
        D4: 结局测量评估
        
        脊柱外科特殊逻辑：
        - 手术无法对术者致盲
        - 主观指标（VAS/ODI）在非盲法研究中风险更高
        - 客观指标（影像、再手术）风险较低
        """
        evidence_parts = []
        
        # 检查盲法
        is_blinded = metadata.get('is_double_blinded', False)
        is_patient_blinded = metadata.get('is_patient_blinded', False)
        is_assessor_blinded = metadata.get('is_assessor_blinded', False)
        
        # 获取结局指标类型
        outcomes = data.get('outcomes', [])
        has_subjective = any(o.upper() in self.SUBJECTIVE_OUTCOMES for o in outcomes)
        has_objective = any(o.upper() in self.OBJECTIVE_OUTCOMES for o in outcomes)
        
        # 脊柱外科决策树
        if is_blinded:
            # 双盲研究
            risk = RiskLevel.LOW
            reason = "双盲设计，测量偏倚风险低"
        elif has_objective and not has_subjective:
            # 纯客观指标（如影像、再手术率）
            risk = RiskLevel.LOW
            reason = "客观结局指标，盲法非必需"
        elif has_subjective:
            # 包含主观指标
            if is_assessor_blinded:
                risk = RiskLevel.SOME_CONCERNS
                reason = "评估者盲法执行，但患者知晓分组（主观指标存在霍桑效应风险）"
            else:
                risk = RiskLevel.SOME_CONCERNS
                reason = "非盲法研究且采用VAS/ODI等主观指标，存在测量偏倚"
            
            # LDH 特殊说明
            if 'VAS' in [o.upper() for o in outcomes]:
                reason += "；PELD患者可能因技术期望效应高估疗效"
        else:
            risk = RiskLevel.SOME_CONCERNS
            reason = "盲法状态不明确"
        
        evidence_parts.append(f"Blinded: {is_blinded}, Outcomes: {outcomes}")
        
        return BiasJudgment(
            domain=Domain.D4_MEASUREMENT,
            risk_level=risk,
            reason=reason,
            evidence_anchor="; ".join(evidence_parts)
        )
    
    def _assess_selective_reporting(
        self, 
        metadata: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> BiasJudgment:
        """
        D5: 选择性报告结果评估
        
        评估要点：
        1. 是否预注册（ClinicalTrials.gov, ChiCTR）
        2. 注册与发表的一致性
        3. 主要结局报告完整性
        """
        evidence_parts = []
        
        # 检查预注册
        registry_number = metadata.get('registry_number', '')
        is_registered = bool(registry_number)
        
        # 检查注册-发表一致性
        protocol_match = metadata.get('protocol_match', None)
        
        if is_registered:
            if protocol_match is True:
                risk = RiskLevel.LOW
                reason = f"已预注册 ({registry_number})，方案与发表一致"
            elif protocol_match is False:
                risk = RiskLevel.HIGH
                reason = f"已预注册 ({registry_number})，但主要结局与注册方案不符"
            else:
                risk = RiskLevel.SOME_CONCERNS
                reason = f"已预注册 ({registry_number})，但无法验证方案一致性"
        else:
            # 未注册
            risk = RiskLevel.SOME_CONCERNS
            reason = "缺乏预注册信息，无法排除选择性报告风险"
        
        evidence_parts.append(f"Registry: {registry_number}, Match: {protocol_match}")
        
        return BiasJudgment(
            domain=Domain.D5_SELECTIVE_REPORTING,
            risk_level=risk,
            reason=reason,
            evidence_anchor="; ".join(evidence_parts)
        )
    
    def _calculate_overall_risk(
        self, 
        judgments: Dict[Domain, BiasJudgment]
    ) -> RiskLevel:
        """
        计算总体偏倚风险
        
        RoB 2.0 规则：
        - 任何领域 High -> 总体 High
        - 任何领域 Some Concerns -> 总体 Some Concerns
        - 全部 Low -> 总体 Low
        """
        risk_levels = [j.risk_level for j in judgments.values()]
        
        if RiskLevel.HIGH in risk_levels:
            return RiskLevel.HIGH
        elif RiskLevel.SOME_CONCERNS in risk_levels:
            return RiskLevel.SOME_CONCERNS
        else:
            return RiskLevel.LOW
    
    def _generate_summary(
        self,
        study_id: str,
        judgments: Dict[Domain, BiasJudgment],
        overall: RiskLevel
    ) -> str:
        """生成评估总结"""
        high_domains = [d.value for d, j in judgments.items() if j.risk_level == RiskLevel.HIGH]
        concern_domains = [d.value for d, j in judgments.items() if j.risk_level == RiskLevel.SOME_CONCERNS]
        
        parts = [f"Study {study_id}: Overall {overall.value}"]
        
        if high_domains:
            parts.append(f"High risk in: {', '.join(high_domains)}")
        if concern_domains:
            parts.append(f"Concerns in: {', '.join(concern_domains)}")
        
        return "; ".join(parts)
    
    def generate_grade_rating(self, assessment: RoBAssessment) -> str:
        """
        根据 RoB 评估生成 GRADE 评级建议
        
        降级规则：
        - High Risk -> 降1级
        - Multiple Some Concerns -> 降1级
        """
        downgrade = 0
        high_count = sum(1 for j in assessment.domain_judgments.values() if j.risk_level == RiskLevel.HIGH)
        concern_count = sum(1 for j in assessment.domain_judgments.values() if j.risk_level == RiskLevel.SOME_CONCERNS)
        
        if high_count >= 1:
            downgrade += 1
        if concern_count >= 2:
            downgrade += 1
        
        ratings = ["⊕⊕⊕⊕", "⊕⊕⊕◯", "⊕⊕◯◯", "⊕◯◯◯", "◯◯◯◯"]
        index = min(downgrade, len(ratings) - 1)
        
        return ratings[index]
    
    def generate_grade_rating_with_imprecision(
        self, 
        assessment: RoBAssessment, 
        extracted_data: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        生成 GRADE 评级（增强版），综合考虑偏倚风险与数据精确性
        
        v2.6.0 增强：新增基于数据估算的不精确性评估
        
        当原始数据未报告 Mean±SD，而是通过 MedianToMeanConverter 估算时，
        由于估算过程本身存在假设（如假设分布对称或服从正态分布），
        这会增加结果的不确定性。根据 GRADE 指南，这种情况应在
        "不精确性（Imprecision）" 领域进行降级。
        
        Args:
            assessment: RoB 2.0 评估结果
            extracted_data: 包含以下关键字段：
                - estimated_data_ratio: 估算数据占比 (0-1)
                - n_estimated: 估算数据的研究数
                - n_original: 原始 Mean±SD 的研究数
                - core_outcomes: 核心结局指标列表
                - has_median_conversion: 是否使用了中位数转换
        
        Returns:
            Tuple[str, str]: (GRADE 评级, 降级理由说明)
            
        Example:
            >>> grade, reason = assessor.generate_grade_rating_with_imprecision(
            ...     assessment, 
            ...     {'estimated_data_ratio': 0.6, 'n_estimated': 3, 'n_original': 2}
            ... )
            >>> print(f"GRADE: {grade}, Reason: {reason}")
            GRADE: ⊕⊕◯◯, Reason: 偏倚风险降级 + 不精确性降级（估算占比60%）
        """
        downgrade = 0
        downgrade_reasons = []
        
        # 1. 基于 RoB 2.0 的降级（原有逻辑）
        high_count = sum(1 for j in assessment.domain_judgments.values() 
                        if j.risk_level == RiskLevel.HIGH)
        concern_count = sum(1 for j in assessment.domain_judgments.values() 
                           if j.risk_level == RiskLevel.SOME_CONCERNS)
        
        if high_count >= 1:
            downgrade += 1
            high_domains = [d.value for d, j in assessment.domain_judgments.items() 
                          if j.risk_level == RiskLevel.HIGH]
            downgrade_reasons.append(f"偏倚风险({', '.join(high_domains)})")
            
        if concern_count >= 2:
            downgrade += 1
            downgrade_reasons.append("多项担忧")
        
        # 2. 新增：不精确性 (Imprecision) 评估
        # 如果核心指标中超过 50% 的数据点是估算的，则触发降级
        estimated_ratio = extracted_data.get('estimated_data_ratio', 0)
        n_estimated = extracted_data.get('n_estimated', 0)
        n_total = extracted_data.get('n_estimated', 0) + extracted_data.get('n_original', 0)
        
        # 动态阈值：根据总样本量调整
        # 小样本研究（n<5）时，30% 估算即触发降级
        # 大样本研究（n>=10）时，50% 估算触发降级
        if n_total < 5:
            imprecision_threshold = 0.30
        elif n_total < 10:
            imprecision_threshold = 0.40
        else:
            imprecision_threshold = 0.50
        
        if estimated_ratio > imprecision_threshold:
            # 数据点高度依赖估算公式，证据强度下降一级
            downgrade += 1
            downgrade_reasons.append(
                f"不精确性（估算占比{estimated_ratio*100:.0f}% > {imprecision_threshold*100:.0f}%阈值）"
            )
            
            # 更新评估总结，添加不精确性说明
            assessment.summary_reason += (
                f" | 因{n_estimated}/{n_total}项研究数据由 Median(IQR) 估算"
                f"（占比{estimated_ratio*100:.0f}%），根据 GRADE 不精确性标准降级"
            )
        
        # 3. 额外：样本量不足的不精确性（经典 GRADE）
        total_sample_size = extracted_data.get('total_sample_size', 0)
        if total_sample_size > 0 and total_sample_size < 100:
            # 小样本额外警告（但不重复降级）
            if estimated_ratio <= imprecision_threshold:
                downgrade_reasons.append(f"注意：总样本量较小(n={total_sample_size})")
        
        # 映射到 GRADE 符号
        ratings = ["⊕⊕⊕⊕", "⊕⊕⊕◯", "⊕⊕◯◯", "⊕◯◯◯", "◯◯◯◯"]
        final_grade = ratings[min(downgrade, len(ratings) - 1)]
        
        # 生成降级理由文本
        if downgrade_reasons:
            reason_text = "降级因素: " + "; ".join(downgrade_reasons)
        else:
            reason_text = "无降级因素"
        
        return final_grade, reason_text
    
    def assess_imprecision_only(
        self, 
        estimated_ratio: float,
        n_estimated: int,
        n_total: int,
        outcome_name: str = ""
    ) -> BiasJudgment:
        """
        单独评估不精确性（用于详细的 GRADE 逐 outcome 评估）
        
        Args:
            estimated_ratio: 估算数据占比 (0-1)
            n_estimated: 估算数据的研究数
            n_total: 总研究数
            outcome_name: 结局指标名称（可选）
        
        Returns:
            BiasJudgment: 不精确性判断结果
        """
        # 动态阈值
        if n_total < 5:
            threshold = 0.30
        elif n_total < 10:
            threshold = 0.40
        else:
            threshold = 0.50
        
        outcome_str = f" [{outcome_name}]" if outcome_name else ""
        
        if estimated_ratio > threshold:
            return BiasJudgment(
                domain=Domain.D3_MISSING_DATA,  # 复用 D3 作为数据质量领域
                risk_level=RiskLevel.HIGH,
                reason=(
                    f"{outcome_str} 数据高度依赖估算({n_estimated}/{n_total}, "
                    f"{estimated_ratio*100:.0f}% > {threshold*100:.0f}%阈值)，"
                    f"根据 GRADE 不精确性标准降级"
                ),
                evidence_anchor=f"Estimated: {n_estimated}/{n_total} ({estimated_ratio*100:.1f}%)",
                confidence=0.9
            )
        elif estimated_ratio > threshold * 0.5:
            return BiasJudgment(
                domain=Domain.D3_MISSING_DATA,
                risk_level=RiskLevel.SOME_CONCERNS,
                reason=(
                    f"{outcome_str} 部分数据为估算({n_estimated}/{n_total}, "
                    f"{estimated_ratio*100:.0f}%)，存在一定不精确性"
                ),
                evidence_anchor=f"Estimated: {n_estimated}/{n_total} ({estimated_ratio*100:.1f}%)",
                confidence=0.7
            )
        else:
            return BiasJudgment(
                domain=Domain.D3_MISSING_DATA,
                risk_level=RiskLevel.LOW,
                reason=(
                    f"{outcome_str} 绝大多数数据为原始 Mean±SD"
                    f"({n_total-n_estimated}/{n_total})，精确性良好"
                ),
                evidence_anchor=f"Original: {n_total-n_estimated}/{n_total}",
                confidence=0.95
            )


# ==================== 测试用例 ====================

def test_ldh_rct_assessment():
    """测试 LDH RCT 评估"""
    print("\n" + "="*60)
    print("Test: LDH RCT 偏倚风险评估")
    print("="*60)
    
    assessor = BiasAssessor(specialty="LDH")
    
    # 模拟一个高质量 RCT
    metadata = {
        'randomization_method': 'computer-generated',
        'allocation_concealment': 'central pharmacy',
        'is_double_blinded': False,
        'is_assessor_blinded': True,
        'itt_analysis': True,
        'registry_number': 'NCT01234567',
        'protocol_match': True
    }
    
    data = {
        'baseline': {'age': {'difference': 3.2}},  # 年龄差异 3.2岁
        'n_randomized': 240,
        'n_completed': 218,
        'conversion_rate': 0.05,
        'outcomes': ['VAS', 'ODI', 'FUSION_RATE']
    }
    
    assessment = assessor.assess("Smith_2023_PELD", metadata, data)
    
    print(f"\n研究: {assessment.study_id}")
    print(f"总体风险: {assessment.overall_risk}")
    print(f"\n各领域评估:")
    for domain, judgment in assessment.domain_judgments.items():
        print(f"  {domain.value:25s}: {judgment.risk_level.value}")
        print(f"    理由: {judgment.reason}")
    
    print(f"\n建议 GRADE 评级: {assessor.generate_grade_rating(assessment)}")
    
    print("\n✅ LDH RCT 评估测试通过")


def test_high_risk_scenario():
    """测试高风险场景"""
    print("\n" + "="*60)
    print("Test: 高风险场景（高失访率）")
    print("="*60)
    
    assessor = BiasAssessor(specialty="LDH")
    
    # 高失访率研究
    metadata = {
        'randomization_method': 'unclear',
        'is_double_blinded': False,
        'itt_analysis': False
    }
    
    data = {
        'baseline': {'age': {'difference': 18.5}},  # 严重基线不平衡
        'n_randomized': 100,
        'n_completed': 75,  # 25% 失访
        'outcomes': ['VAS']
    }
    
    assessment = assessor.assess("LowQuality_2023", metadata, data)
    
    print(f"\n研究: {assessment.study_id}")
    print(f"总体风险: {assessment.overall_risk}")
    
    # 验证高风险
    assert assessment.overall_risk == RiskLevel.HIGH
    assert assessment.domain_judgments[Domain.D3_MISSING_DATA].risk_level == RiskLevel.HIGH
    
    print(f"\n建议 GRADE 评级: {assessor.generate_grade_rating(assessment)}")
    
    print("\n✅ 高风险场景测试通过")


def test_objective_outcomes():
    """测试客观指标场景"""
    print("\n" + "="*60)
    print("Test: 纯客观指标场景（影像学研究）")
    print("="*60)
    
    assessor = BiasAssessor(specialty="LDH")
    
    # 影像学研究（客观指标）
    metadata = {
        'randomization_method': 'random number table',
        'allocation_concealment': 'sealed envelopes',
        'is_double_blinded': False,  # 无法盲法
    }
    
    data = {
        'baseline': {},
        'n_randomized': 60,
        'n_completed': 58,
        'outcomes': ['CANAL_AREA', 'DISC_HEIGHT']  # 纯客观指标
    }
    
    assessment = assessor.assess("Imaging_2023", metadata, data)
    
    print(f"\n研究: {assessment.study_id}")
    print(f"总体风险: {assessment.overall_risk}")
    
    # 客观指标应降低 D4 风险
    d4_judgment = assessment.domain_judgments[Domain.D4_MEASUREMENT]
    print(f"D4 测量偏倚: {d4_judgment.risk_level.value}")
    print(f"理由: {d4_judgment.reason}")
    
    print("\n✅ 客观指标场景测试通过")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("Cochrane RoB 2.0 Bias Assessor v1.0 - 测试套件")
    print("="*70)
    print("评估领域：D1随机化 | D2偏离 | D3缺失数据 | D4测量 | D5选择性报告")
    print("="*70)
    
    test_ldh_rct_assessment()
    test_high_risk_scenario()
    test_objective_outcomes()
    
    print("\n" + "="*70)
    print("所有测试通过！")
    print("="*70)
