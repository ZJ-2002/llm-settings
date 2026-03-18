# Anomalous Findings Detector 非预期发现探测器

> **版本**: v2.4.0  
> **分类**: P2 - 中等优先级  
> **功能**: 识别"奇怪的旁证"、作者未能解释的次要结局、潜在的科学线索

---

## 模块定位

**问题**: AI倾向于寻找支持PICO的"标准答案"，可能错失重要的非预期发现。

**目标**: 像经验丰富的研究者一样，识别"奇怪"的数据点和未解之谜。

---

## 核心功能

### 1. 非预期发现扫描

```python
# anomalous_findings_detector.py

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import re

class AnomalyType(Enum):
    UNEXPECTED_SECONDARY_OUTCOME = "unexpected_secondary"  # 非预期次要结局
    UNEXPLAINED_SIDE_EFFECT = "unexplained_side_effect"    # 未解释的副作用
    CONTRADICTORY_SUBGROUP = "contradictory_subgroup"      # 矛盾亚组结果
    OUTLIER_STUDY = "outlier_study"                        # 离群研究
    PARADOXICAL_FINDING = "paradoxical"                    # 悖论性发现
    UNEXPECTED_CORRELATION = "unexpected_correlation"      # 非预期相关性

@dataclass
class AnomalousFinding:
    """非预期发现数据结构"""
    id: str
    type: AnomalyType
    description: str
    source_paper: str
    context: str
    potential_significance: str
    confidence: float  # 0-1
    related_mechanism: Optional[str] = None
    suggested_follow_up: Optional[str] = None

class AnomalousFindingsDetector:
    """
    非预期发现探测器
    
    识别文献中潜在的突破性线索
    """
    
    # 异常信号关键词
    ANOMALY_SIGNALS = {
        "unexpected": [
            "unexpectedly", "surprisingly", "unexpected finding",
            "contrary to our hypothesis", "not anticipated",
            "unanticipated", "paradoxically"
        ],
        "unexplained": [
            "mechanism remains unclear", "the reason is unknown",
            "we cannot explain", "remains to be elucidated",
            "further investigation is needed"
        ],
        "side_effect": [
            "adverse event", "side effect", "toxicity",
            "unexpected reaction", "unintended consequence"
        ]
    }
    
    def __init__(self):
        self.findings_database = []
    
    def scan_paper(
        self,
        paper_id: str,
        results_text: str,
        discussion_text: Optional[str] = None,
        tables_data: Optional[List[Dict]] = None
    ) -> List[AnomalousFinding]:
        """
        扫描单篇文献的非预期发现
        
        Args:
            paper_id: 文献ID
            results_text: Results章节文本
            discussion_text: Discussion章节文本
            tables_data: 表格数据
            
        Returns:
            发现的异常列表
        """
        findings = []
        
        # 扫描1: 文本中的异常信号
        text_findings = self._scan_text_for_signals(
            paper_id, results_text, discussion_text
        )
        findings.extend(text_findings)
        
        # 扫描2: 表格中的离群值
        if tables_data:
            table_findings = self._scan_tables_for_outliers(
                paper_id, tables_data
            )
            findings.extend(table_findings)
        
        # 扫描3: 亚组分析中的矛盾结果
        if discussion_text:
            subgroup_findings = self._scan_for_contradictory_subgroups(
                paper_id, results_text, discussion_text
            )
            findings.extend(subgroup_findings)
        
        return findings
    
    def _scan_text_for_signals(
        self,
        paper_id: str,
        results_text: str,
        discussion_text: Optional[str]
    ) -> List[AnomalousFinding]:
        """扫描文本中的异常信号"""
        findings = []
        combined_text = (results_text + " " + (discussion_text or "")).lower()
        
        # 检测非预期发现信号
        for signal_type, keywords in self.ANOMALY_SIGNALS.items():
            for keyword in keywords:
                if keyword in combined_text:
                    # 提取上下文
                    context = self._extract_context(combined_text, keyword)
                    
                    finding = AnomalousFinding(
                        id=f"{paper_id}_anomaly_{len(findings)}",
                        type=self._map_signal_to_type(signal_type),
                        description=f"检测到'{keyword}'信号",
                        source_paper=paper_id,
                        context=context,
                        potential_significance=self._infer_significance(signal_type, context),
                        confidence=0.7
                    )
                    findings.append(finding)
        
        return findings
    
    def _scan_tables_for_outliers(
        self,
        paper_id: str,
        tables_data: List[Dict]
    ) -> List[AnomalousFinding]:
        """扫描表格中的离群值"""
        findings = []
        
        for table in tables_data:
            # 检测异常大的效应量
            if "effect_sizes" in table:
                effect_sizes = table["effect_sizes"]
                mean_es = sum(effect_sizes) / len(effect_sizes)
                std_es = (sum((x - mean_es) ** 2 for x in effect_sizes) / len(effect_sizes)) ** 0.5
                
                for i, es in enumerate(effect_sizes):
                    z_score = abs(es - mean_es) / (std_es or 1)
                    if z_score > 2.5:  # 超过2.5个标准差
                        finding = AnomalousFinding(
                            id=f"{paper_id}_outlier_{i}",
                            type=AnomalyType.OUTLIER_STUDY,
                            description=f"离群效应量 (Z={z_score:.2f})",
                            source_paper=paper_id,
                            context=f"Effect size: {es}, Mean: {mean_es:.2f}",
                            potential_significance="可能存在独特的患者特征或干预方案差异",
                            confidence=min(z_score / 3, 0.95)
                        )
                        findings.append(finding)
        
        return findings
    
    def _scan_for_contradictory_subgroups(
        self,
        paper_id: str,
        results_text: str,
        discussion_text: str
    ) -> List[AnomalousFinding]:
        """扫描矛盾亚组结果"""
        findings = []
        
        # 检测亚组分析中的矛盾信号
        subgroup_patterns = [
            r"subgroup analysis.*showed.*different",
            r"interaction.*significant",
            r"effect.*modified by"
        ]
        
        for pattern in subgroup_patterns:
            matches = re.findall(pattern, results_text.lower())
            if matches:
                context = self._extract_context(results_text, matches[0])
                
                finding = AnomalousFinding(
                    id=f"{paper_id}_subgroup_{len(findings)}",
                    type=AnomalyType.CONTRADICTORY_SUBGROUP,
                    description="亚组分析显示效应修饰",
                    source_paper=paper_id,
                    context=context,
                    potential_significance="可能存在重要的效应修饰因子",
                    confidence=0.75,
                    suggested_follow_up="建议开展专门研究验证该亚组效应"
                )
                findings.append(finding)
        
        return findings
    
    def _extract_context(self, text: str, keyword: str, window: int = 150) -> str:
        """提取关键词上下文"""
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        return text[start:end]
    
    def _map_signal_to_type(self, signal_type: str) -> AnomalyType:
        """映射信号类型到异常类型"""
        mapping = {
            "unexpected": AnomalyType.UNEXPECTED_SECONDARY_OUTCOME,
            "unexplained": AnomalyType.PARADOXICAL_FINDING,
            "side_effect": AnomalyType.UNEXPLAINED_SIDE_EFFECT
        }
        return mapping.get(signal_type, AnomalyType.UNEXPECTED_SECONDARY_OUTCOME)
    
    def _infer_significance(self, signal_type: str, context: str) -> str:
        """推断潜在科学意义"""
        significances = {
            "unexpected": "可能暗示未被发现的作用机制",
            "unexplained": "可能涉及跨学科关联",
            "side_effect": "可能提示药物代谢或脱靶效应"
        }
        return significances.get(signal_type, "需要进一步研究")
```

---

### 2. 跨研究异常模式检测

```python
    def detect_cross_study_patterns(
        self,
        all_findings: List[AnomalousFinding]
    ) -> Dict:
        """
        检测跨研究的异常模式
        
        识别:
        - 多个研究共同报告的非预期发现
        - 可能指向新的研究方向
        """
        # 按类型分组
        by_type = {}
        for finding in all_findings:
            t = finding.type.value
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(finding)
        
        # 检测重复出现的异常
        recurring_patterns = []
        for anomaly_type, findings in by_type.items():
            if len(findings) >= 3:  # 至少3个研究报告类似异常
                recurring_patterns.append({
                    "type": anomaly_type,
                    "count": len(findings),
                    "papers": [f.source_paper for f in findings],
                    "common_description": self._find_common_theme(findings),
                    "potential_breakthrough": "多个独立研究观察到类似现象，可能指向重要的新机制"
                })
        
        return {
            "total_findings": len(all_findings),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "recurring_patterns": recurring_patterns,
            "breakthrough_candidates": [p for p in recurring_patterns if p["count"] >= 5]
        }
    
    def _find_common_theme(self, findings: List[AnomalousFinding]) -> str:
        """查找共同主题 (简化实现)"""
        # 提取关键词交集
        all_words = set()
        for f in findings:
            words = set(f.context.lower().split())
            if not all_words:
                all_words = words
            else:
                all_words &= words
        
        return " ".join(list(all_words)[:5]) if all_words else "未识别共同主题"
```

---

### 3. 与综述撰写集成

```python
    def generate_discussion_inserts(
        self,
        findings: List[AnomalousFinding]
    ) -> List[Dict]:
        """
        生成讨论章节插入内容
        
        将非预期发现转化为综述中的科学洞察
        """
        inserts = []
        
        # 高置信度发现 (confidence > 0.8)
        high_confidence = [f for f in findings if f.confidence > 0.8]
        
        if high_confidence:
            # 生成"Limitations and Future Directions"段落
            text = "值得注意的是，多项研究报告了超出主要假设的非预期发现："
            
            for i, finding in enumerate(high_confidence[:3], 1):
                text += f"\n{i}. {finding.description} ({finding.source_paper})"
                if finding.potential_significance:
                    text += f"，这可能{finding.potential_significance}。"
            
            text += "\n\n这些发现提示该领域可能存在尚未被充分认识的机制，值得未来研究深入探索。"
            
            inserts.append({
                "section": "Outlook",
                "subsection": "Unexpected Findings",
                "content": text,
                "priority": "high"
            })
        
        # 突破性候选
        cross_study = self.detect_cross_study_patterns(findings)
        for candidate in cross_study.get("breakthrough_candidates", []):
            text = f"\n\n**潜在的突破性线索**: 多项独立研究({', '.join(candidate['papers'][:3])}等)"
            text += f"均报告了{candidate['common_description']}。"
            text += "这一重复出现的模式可能指向重要的新机制，建议开展专门的验证研究。"
            
            inserts.append({
                "section": "Outlook",
                "subsection": "Breakthrough Opportunities",
                "content": text,
                "priority": "very_high"
            })
        
        return inserts
```

---

## Evidence Audit Trail 整合

```markdown
**[Anomalous Finding Detected]** ⚠️ v2.4.0 新增
- **发现类型**: Unexpected Secondary Outcome
- **描述**: "治疗组出现非预期的认知功能改善"
- **来源**: Wang2024_Cognitive_OA
- **上下文**: "Although not a primary endpoint, we observed significant improvement in cognitive function (MMSE +3.2 points, P=0.012)"
- **潜在意义**: "可能暗示该治疗对神经退行性变有保护作用"
- **置信度**: 0.82 (高)
- **建议后续**: "建议开展专门研究验证该发现"
- **AI判断**: 🔬 **潜在突破性线索** - 该发现与主流认知不符，可能开启新的研究方向
```

---

## 使用示例

```python
from anomalous_findings_detector import AnomalousFindingsDetector

detector = AnomalousFindingsDetector()

# 扫描单篇文献
findings = detector.scan_paper(
    paper_id="Wang2024",
    results_text="...",
    discussion_text="...",
    tables_data=[...]
)

for finding in findings:
    print(f"🚨 {finding.type.value}: {finding.description}")
    print(f"   潜在意义: {finding.potential_significance}")
    print(f"   置信度: {finding.confidence:.2f}")

# 批量分析
all_findings = []
for paper in papers:
    findings = detector.scan_paper(**paper)
    all_findings.extend(findings)

# 检测跨研究模式
patterns = detector.detect_cross_study_patterns(all_findings)
if patterns["breakthrough_candidates"]:
    print("🔬 发现潜在突破性线索:")
    for candidate in patterns["breakthrough_candidates"]:
        print(f"  - {candidate['common_description']}")

# 生成讨论插入内容
inserts = detector.generate_discussion_inserts(all_findings)
```

---

## 实现状态

- [x] 文本异常信号扫描
- [x] 表格离群值检测
- [x] 矛盾亚组结果识别
- [x] 跨研究模式检测
- [x] 讨论章节插入生成
- [x] Evidence Audit Trail 整合
- [ ] LLM增强的语义理解 (v2.5.0)
- [ ] 跨学科联想检测 (v2.5.0)

---

*创建日期: 2026-03-12*  
*版本: v2.4.0*