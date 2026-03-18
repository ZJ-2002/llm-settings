# Extreme Stress Testing 极限压力测试

> **版本**: v2.4.0  
> **分类**: P2 - 中等优先级  
> **功能**: STEP 8+ 极限压力模块，模拟顶刊审稿人最苛刻的逻辑攻击

---

## 模块定位

**问题**: review-checklist的专家视角攻击已覆盖基础检查，但缺乏针对特定主题的"极限"压力测试。

**目标**: 模拟Nature Reviews等顶刊审稿人的最苛刻质疑，提前暴露综述弱点。

---

## 核心功能

### 1. 专项压力测试框架

```python
# extreme_stress_testing.py

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class StressTestType(Enum):
    EVIDENCE_TRACEABILITY = "evidence_traceability"    # 证据溯源压力
    ATTRIBUTION_LOGIC = "attribution_logic"            # 归因逻辑压力
    METHODOLOGY_BLINDSPOT = "methodology_blindspot"    # 方法学盲区压力
    CLINICAL_GENERALIZATION = "clinical_generalization"  # 临床推广压力
    STATISTICAL_RIGOR = "statistical_rigor"            # 统计严谨性压力

@dataclass
class StressTestResult:
    """压力测试结果"""
    test_type: StressTestType
    question: str
    severity: str  # critical, high, medium, low
    current_status: str  # pass, partial, fail
    evidence_gaps: List[str]
    recommended_actions: List[str]

class ExtremeStressTester:
    """
    极限压力测试器
    
    模拟顶刊审稿人的苛刻质疑
    """
    
    def __init__(self, topic: str, focus_areas: Optional[List[str]] = None):
        self.topic = topic
        self.focus_areas = focus_areas or []
        self.test_results = []
    
    def run_full_stress_test(
        self,
        review_draft: Dict,
        evidence_synthesis: Dict
    ) -> Dict:
        """
        运行完整压力测试套件
        
        Returns:
            完整测试报告
        """
        all_results = []
        
        # 1. 证据溯源压力测试
        trace_results = self._test_evidence_traceability(
            review_draft, evidence_synthesis
        )
        all_results.extend(trace_results)
        
        # 2. 归因逻辑压力测试
        attr_results = self._test_attribution_logic(
            review_draft, evidence_synthesis
        )
        all_results.extend(attr_results)
        
        # 3. 方法学盲区压力测试
        blindspot_results = self._test_methodology_blindspots(
            review_draft, evidence_synthesis
        )
        all_results.extend(blindspot_results)
        
        # 4. 临床推广压力测试
        clinical_results = self._test_clinical_generalization(
            review_draft
        )
        all_results.extend(clinical_results)
        
        # 5. 统计严谨性压力测试
        stat_results = self._test_statistical_rigor(
            review_draft, evidence_synthesis
        )
        all_results.extend(stat_results)
        
        # 专项压力测试 (针对特定主题)
        if self.focus_areas:
            for area in self.focus_areas:
                specific_results = self._run_topic_specific_tests(
                    area, review_draft, evidence_synthesis
                )
                all_results.extend(specific_results)
        
        return {
            "topic": self.topic,
            "total_tests": len(all_results),
            "critical_failures": sum(1 for r in all_results if r.severity == "critical" and r.current_status == "fail"),
            "high_failures": sum(1 for r in all_results if r.severity == "high" and r.current_status == "fail"),
            "results": all_results,
            "action_items": self._generate_action_items(all_results),
            "readiness_score": self._calculate_readiness(all_results)
        }
    
    def _test_evidence_traceability(
        self,
        review_draft: Dict,
        evidence_synthesis: Dict
    ) -> List[StressTestResult]:
        """证据溯源压力测试"""
        results = []
        
        # 测试1: 核心结论的随访时间
        results.append(StressTestResult(
            test_type=StressTestType.EVIDENCE_TRACEABILITY,
            question="复发率结论的随访时间是否≥2年？",
            severity="critical",
            current_status=self._check_follow_up_duration(evidence_synthesis, min_months=24),
            evidence_gaps=["短期随访可能无法捕捉真实复发率"],
            recommended_actions=["明确声明随访时间限制", "检索长期随访研究"]
        ))
        
        # 测试2: 关键数据的原始出处
        results.append(StressTestResult(
            test_type=StressTestType.EVIDENCE_TRACEABILITY,
            question="所有关键数据能否追溯到具体文献的具体页码/表格？",
            severity="high",
            current_status=self._check_source_traceability(review_draft),
            evidence_gaps=["部分数据缺乏精确溯源"],
            recommended_actions=["补充完整的Evidence Audit Trail"]
        ))
        
        # 测试3: 灰色文献覆盖
        results.append(StressTestResult(
            test_type=StressTestType.EVIDENCE_TRACEABILITY,
            question="是否检索了会议摘要、注册试验等灰色文献？",
            severity="medium",
            current_status=self._check_grey_literature(evidence_synthesis),
            evidence_gaps=["可能存在发表偏倚"],
            recommended_actions=["补充ClinicalTrials.gov等来源检索"]
        ))
        
        return results
    
    def _test_attribution_logic(
        self,
        review_draft: Dict,
        evidence_synthesis: Dict
    ) -> List[StressTestResult]:
        """归因逻辑压力测试"""
        results = []
        
        # 测试1: 康复依从性归因
        results.append(StressTestResult(
            test_type=StressTestType.ATTRIBUTION_LOGIC,
            question="康复依从性差异是否源于'强制性住院康复'？",
            severity="high",
            current_status=self._check_rehabilitation_attribution(evidence_synthesis),
            evidence_gaps=["未区分住院vs门诊康复的差异"],
            recommended_actions=["分层分析康复模式的影响"]
        ))
        
        # 测试2: 术者经验混杂
        results.append(StressTestResult(
            test_type=StressTestType.ATTRIBUTION_LOGIC,
            question="技术疗效差异是否被术者经验混杂？",
            severity="critical",
            current_status=self._check_surgeon_experience_confounding(evidence_synthesis),
            evidence_gaps=["多数研究未报告术者手术量"],
            recommended_actions=["讨论术者经验对学习曲线的影响"]
        ))
        
        # 测试3: 疾病严重程度分层
        results.append(StressTestResult(
            test_type=StressTestType.ATTRIBUTION_LOGIC,
            question="疗效差异是否源于疾病严重程度分布不均？",
            severity="high",
            current_status=self._check_disease_severity_stratification(evidence_synthesis),
            evidence_gaps=["未按Modic改变、突出类型分层分析"],
            recommended_actions=["补充分层分析或声明限制"]
        ))
        
        return results
    
    def _test_methodology_blindspots(
        self,
        review_draft: Dict,
        evidence_synthesis: Dict
    ) -> List[StressTestResult]:
        """方法学盲区压力测试"""
        results = []
        
        # 测试1: 失访偏倚
        results.append(StressTestResult(
            test_type=StressTestType.METHODOLOGY_BLINDSPOT,
            question="失访偏倚对复发率统计的潜在冲击？",
            severity="critical",
            current_status=self._check_attrition_bias(evidence_synthesis),
            evidence_gaps=["多数研究ITT分析不完整"],
            recommended_actions=["评估失访率对结果的影响", "敏感性分析"]
        ))
        
        # 测试2: 测量偏倚
        results.append(StressTestResult(
            test_type=StressTestType.METHODOLOGY_BLINDSPOT,
            question="功能评分量表是否存在天花板/地板效应？",
            severity="medium",
            current_status=self._check_measurement_bias(evidence_synthesis),
            evidence_gaps=["未讨论量表的测量特性"],
            recommended_actions=["补充量表 psychometric properties 讨论"]
        ))
        
        # 测试3: 选择偏倚
        results.append(StressTestResult(
            test_type=StressTestType.METHODOLOGY_BLINDSPOT,
            question="单中心研究的选择偏倚如何影响外推性？",
            severity="high",
            current_status=self._check_selection_bias(evidence_synthesis),
            evidence_gaps=["单中心研究占比过高"],
            recommended_actions=["讨论单中心研究的局限性"]
        ))
        
        return results
    
    def _test_clinical_generalization(
        self,
        review_draft: Dict
    ) -> List[StressTestResult]:
        """临床推广压力测试"""
        results = []
        
        # 测试1: 真实世界适用性
        results.append(StressTestResult(
            test_type=StressTestType.CLINICAL_GENERALIZATION,
            question="试验中的严格入排标准是否限制了真实世界适用性？",
            severity="high",
            current_status=self._check_real_world_applicability(review_draft),
            evidence_gaps=["排除了合并症、高龄患者"],
            recommended_actions=["讨论外推性限制", "引用真实世界研究"]
        ))
        
        # 测试2: 成本效益
        results.append(StressTestResult(
            test_type=StressTestType.CLINICAL_GENERALIZATION,
            question="是否考虑了成本效益比？",
            severity="medium",
            current_status=self._check_cost_effectiveness(review_draft),
            evidence_gaps=["缺乏卫生经济学证据"],
            recommended_actions=["指出成本效益证据缺口"]
        ))
        
        return results
    
    def _test_statistical_rigor(
        self,
        review_draft: Dict,
        evidence_synthesis: Dict
    ) -> List[StressTestResult]:
        """统计严谨性压力测试"""
        results = []
        
        # 测试1: 多重比较
        results.append(StressTestResult(
            test_type=StressTestType.STATISTICAL_RIGOR,
            question="亚组分析和多重终点是否进行了多重比较校正？",
            severity="high",
            current_status=self._check_multiple_comparison(evidence_synthesis),
            evidence_gaps=["亚组分析可能为假阳性"],
            recommended_actions=["声明多重比较问题", "建议使用更严格显著性水平"]
        ))
        
        # 测试2: 异质性解释
        results.append(StressTestResult(
            test_type=StressTestType.STATISTICAL_RIGOR,
            question="I²>50%时是否充分探讨了异质性来源？",
            severity="critical",
            current_status=self._check_heterogeneity_exploration(evidence_synthesis),
            evidence_gaps=["异质性来源分析不充分"],
            recommended_actions=["使用Meta回归或亚组分析探讨异质性"]
        ))
        
        return results
    
    def _run_topic_specific_tests(
        self,
        focus_area: str,
        review_draft: Dict,
        evidence_synthesis: Dict
    ) -> List[StressTestResult]:
        """专项压力测试"""
        results = []
        
        if focus_area == "recurrence-and-compliance":
            # LDH复发率专项压力测试
            results.extend([
                StressTestResult(
                    test_type=StressTestType.EVIDENCE_TRACEABILITY,
                    question="[LDH专项] 复发定义在各研究中是否一致？",
                    severity="critical",
                    current_status=self._check_recurrence_definition_consistency(evidence_synthesis),
                    evidence_gaps=["复发定义不一致影响可比性"],
                    recommended_actions=["制作复发定义对比表", "分层分析"]
                ),
                StressTestResult(
                    test_type=StressTestType.ATTRIBUTION_LOGIC,
                    question="[LDH专项] 复发与再手术的区别是否清晰？",
                    severity="high",
                    current_status=self._check_recurrence_vs_reoperation(review_draft),
                    evidence_gaps=["部分研究混用两个概念"],
                    recommended_actions=["明确区分复发与再手术"]
                )
            ])
        
        elif focus_area == "surgical-technique-comparison":
            # 手术技术比较专项
            results.extend([
                StressTestResult(
                    test_type=StressTestType.ATTRIBUTION_LOGIC,
                    question="[手术专项] 技术差异是否被术者学习曲线混杂？",
                    severity="critical",
                    current_status=self._check_learning_curve_confounding(evidence_synthesis),
                    evidence_gaps=["新技术初期结果可能反映学习曲线"],
                    recommended_actions=["按术者经验分层", "讨论学习曲线影响"]
                )
            ])
        
        return results
```

---

### 2. 辅助检查方法

```python
    # 以下是辅助检查方法 (简化实现框架)
    
    def _check_follow_up_duration(self, evidence: Dict, min_months: int) -> str:
        """检查随访时间"""
        # 实际实现需要分析证据综合数据
        return "partial"  # 占位
    
    def _check_source_traceability(self, draft: Dict) -> str:
        """检查溯源完整性"""
        return "partial"
    
    def _check_grey_literature(self, evidence: Dict) -> str:
        """检查灰色文献覆盖"""
        return "fail"
    
    def _check_rehabilitation_attribution(self, evidence: Dict) -> str:
        """检查康复归因"""
        return "partial"
    
    def _check_surgeon_experience_confounding(self, evidence: Dict) -> str:
        """检查术者经验混杂"""
        return "fail"
    
    def _check_disease_severity_stratification(self, evidence: Dict) -> str:
        """检查疾病严重程度分层"""
        return "partial"
    
    def _check_attrition_bias(self, evidence: Dict) -> str:
        """检查失访偏倚"""
        return "fail"
    
    def _check_measurement_bias(self, evidence: Dict) -> str:
        """检查测量偏倚"""
        return "partial"
    
    def _check_selection_bias(self, evidence: Dict) -> str:
        """检查选择偏倚"""
        return "fail"
    
    def _check_real_world_applicability(self, draft: Dict) -> str:
        """检查真实世界适用性"""
        return "partial"
    
    def _check_cost_effectiveness(self, draft: Dict) -> str:
        """检查成本效益"""
        return "fail"
    
    def _check_multiple_comparison(self, evidence: Dict) -> str:
        """检查多重比较"""
        return "partial"
    
    def _check_heterogeneity_exploration(self, evidence: Dict) -> str:
        """检查异质性探讨"""
        return "fail"
    
    def _check_recurrence_definition_consistency(self, evidence: Dict) -> str:
        """[LDH专项] 检查复发定义一致性"""
        return "fail"
    
    def _check_recurrence_vs_reoperation(self, draft: Dict) -> str:
        """[LDH专项] 检查复发vs再手术"""
        return "partial"
    
    def _check_learning_curve_confounding(self, evidence: Dict) -> str:
        """[手术专项] 检查学习曲线混杂"""
        return "fail"
```

---

### 3. 报告生成

```python
    def _generate_action_items(self, results: List[StressTestResult]) -> List[Dict]:
        """生成行动项"""
        actions = []
        
        critical_failures = [r for r in results if r.severity == "critical" and r.current_status == "fail"]
        high_failures = [r for r in results if r.severity == "high" and r.current_status == "fail"]
        
        for failure in critical_failures:
            actions.append({
                "priority": "CRITICAL",
                "issue": failure.question,
                "actions": failure.recommended_actions,
                "deadline": "before_submission"
            })
        
        for failure in high_failures:
            actions.append({
                "priority": "HIGH",
                "issue": failure.question,
                "actions": failure.recommended_actions,
                "deadline": "before_submission"
            })
        
        return actions
    
    def _calculate_readiness(self, results: List[StressTestResult]) -> Dict:
        """计算投稿准备度"""
        total = len(results)
        passed = sum(1 for r in results if r.current_status == "pass")
        partial = sum(1 for r in results if r.current_status == "partial")
        failed = sum(1 for r in results if r.current_status == "fail")
        
        # 加权得分
        score = (passed * 1.0 + partial * 0.5 + failed * 0.0) / total * 100
        
        readiness_level = "not_ready"
        if score >= 90:
            readiness_level = "ready_for_top_journal"
        elif score >= 75:
            readiness_level = "ready_with_minor_revisions"
        elif score >= 60:
            readiness_level = "needs_major_revisions"
        
        return {
            "score": round(score, 1),
            "level": readiness_level,
            "breakdown": {
                "passed": passed,
                "partial": partial,
                "failed": failed
            }
        }
    
    def generate_report(self, test_report: Dict) -> str:
        """生成压力测试报告"""
        report = f"""
# 极限压力测试报告

## 概览
- **测试主题**: {test_report['topic']}
- **测试总数**: {test_report['total_tests']}
- **准备度评分**: {test_report['readiness_score']['score']}/100
- **准备度等级**: {test_report['readiness_score']['level']}

## 关键失败项
"""
        
        critical = [r for r in test_report['results'] if r.severity == "critical" and r.current_status == "fail"]
        if critical:
            report += "\n### 🔴 Critical Issues\n"
            for item in critical:
                report += f"- **{item.question}**\n"
                report += f"  - 证据缺口: {', '.join(item.evidence_gaps)}\n"
                report += f"  - 建议: {', '.join(item.recommended_actions)}\n"
        
        high = [r for r in test_report['results'] if r.severity == "high" and r.current_status == "fail"]
        if high:
            report += "\n### 🟠 High Priority Issues\n"
            for item in high:
                report += f"- **{item.question}**\n"
        
        report += "\n## 行动清单\n"
        for action in test_report['action_items']:
            report += f"- [{action['priority']}] {action['issue']}\n"
        
        return report
```

---

## 使用示例

```python
from extreme_stress_testing import ExtremeStressTester

# 初始化压力测试器 (LDH主题，重点关注复发率和依从性)
tester = ExtremeStressTester(
    topic="Lumbar Disc Herniation Surgical Management",
    focus_areas=["recurrence-and-compliance", "surgical-technique-comparison"]
)

# 运行完整压力测试
review_draft = {...}  # 综述草稿
evidence_synthesis = {...}  # 证据综合数据

report = tester.run_full_stress_test(review_draft, evidence_synthesis)

# 查看结果
print(f"准备度评分: {report['readiness_score']['score']}/100")
print(f"关键失败: {report['critical_failures']}项")
print(f"高优先级失败: {report['high_failures']}项")

# 生成详细报告
full_report = tester.generate_report(report)
print(full_report)

# 处理行动项
for action in report['action_items']:
    print(f"[{action['priority']}] {action['issue']}")
    for step in action['actions']:
        print(f"  - {step}")
```

---

## 与 Review Checklist 的整合

```markdown
# STEP 8+ 极限压力测试

在标准review-checklist通过后，执行专项压力测试:

```bash
/medical-review-skill review-checklist --mode "extreme-stress" \
  --topic "Lumbar Disc Herniation" \
  --focus "recurrence-and-compliance,surgical-technique"
```

**通过标准**:
- 准备度评分 ≥ 75分
- Critical失败项 = 0
- 所有High优先级失败项有应对计划
```

---

## 实现状态

- [x] 证据溯源压力测试
- [x] 归因逻辑压力测试
- [x] 方法学盲区压力测试
- [x] 临床推广压力测试
- [x] 统计严谨性压力测试
- [x] 专项压力测试框架
- [x] 准备度评分系统
- [ ] 自动化检查实现 (v2.5.0)
- [ ] 更多专科专项测试 (v2.4.1)

---

*创建日期: 2026-03-12*  
*版本: v2.4.0*