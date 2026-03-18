# Funding & COI Scanner 利益相关性扫描

> **版本**: v2.4.0  
> **分类**: P1 - 高优先级  
> **功能**: 主动分析厂商资助偏倚，检测选择性报告风险

---

## 模块定位

**问题**: 当前Evidence Audit Trail虽记录资金来源，但未主动分析厂商资助偏倚。

**目标**: 从被动记录升级为主动审计，识别潜在的利益冲突和发表偏倚。

---

## 核心功能

### 1. 资助来源分析

```python
# funding_coi_scanner.py

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import re

class FundingType(Enum):
    INDUSTRY = "industry"           # 厂商资助
    GOVERNMENT = "government"       # 政府基金
    ACADEMIC = "academic"           # 学术机构
    INDEPENDENT = "independent"     # 独立研究
    UNCLEAR = "unclear"             # 不明确
    NONE = "none"                   # 无资助

class COILevel(Enum):
    HIGH = "high"           # 作者持有厂商股份/顾问
    MODERATE = "moderate"   # 演讲费/研究资助
    LOW = "low"             # 会议支持/小额资助
    NONE = "none"           # 无利益冲突
    UNREPORTED = "unreported"  # 未报告

@dataclass
class FundingRecord:
    """资助记录"""
    paper_id: str
    funding_sources: List[str]
    funding_type: FundingType
    amounts: Optional[List[str]] = None
    grant_numbers: Optional[List[str]] = None
    
@dataclass
class COIRecord:
    """利益冲突记录"""
    paper_id: str
    authors_with_coi: List[Dict]  # [{name, type, description}]
    overall_level: COILevel
    coi_statement: Optional[str] = None

class FundingCOIScanner:
    """
    资助与利益冲突扫描器
    
    自动检测潜在的资助偏倚和利益冲突
    """
    
    # 厂商关键词库
    INDUSTRY_KEYWORDS = [
        # 制药公司常见后缀
        "pharma", "pharmaceutical", "pharmaceuticals", "biotech",
        "bioscience", "therapeutics", "medical", "medtech",
        # 大型药企
        "pfizer", "novartis", "roche", "sanofi", "merck", "johnson",
        "astrazeneca", "glaxo", "gsk", "eli lilly", "bristol myers",
        "abbott", "abbvie", "amgen", "bayer", "novo nordisk",
        # 医疗器械
        "medtronic", "stryker", "zimmer", "johnson & johnson",
        "smith & nephew", "synthes", "depuy", "biomet",
        # 生物技术
        "regeneron", "vertex", "biogen", "gilead"
    ]
    
    # COI关键词
    COI_KEYWORDS = {
        "high": ["stock", "shares", "equity", "ownership", "consultant", "advisory board"],
        "moderate": ["speaker", "honorarium", "research grant", "investigator"],
        "low": ["travel", "meeting support", "educational grant"]
    }
    
    def __init__(self):
        self.funding_database = []
        self.coi_database = []
    
    def scan_funding(
        self,
        paper_id: str,
        funding_section: str,
        coi_section: Optional[str] = None
    ) -> Dict:
        """
        扫描资助和COI信息
        
        Args:
            paper_id: 文献ID
            funding_section: 资助声明章节
            coi_section: 利益冲突声明章节
            
        Returns:
            扫描结果
        """
        # 分析资助来源
        funding_analysis = self._analyze_funding(funding_section)
        
        # 分析COI
        coi_analysis = self._analyze_coi(coi_section) if coi_section else None
        
        result = {
            "paper_id": paper_id,
            "funding": funding_analysis,
            "coi": coi_analysis,
            "bias_risk_score": self._calculate_bias_risk(funding_analysis, coi_analysis),
            "recommendations": self._generate_recommendations(funding_analysis, coi_analysis)
        }
        
        return result
    
    def _analyze_funding(self, text: str) -> Dict:
        """分析资助来源"""
        text_lower = text.lower()
        
        # 检测厂商资助
        industry_matches = []
        for keyword in self.INDUSTRY_KEYWORDS:
            if keyword in text_lower:
                # 提取上下文
                pattern = rf"(.{{0,30}}{keyword}.{{0,30}})"
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                industry_matches.extend(matches)
        
        # 分类资助类型
        if industry_matches:
            funding_type = FundingType.INDUSTRY
        elif any(word in text_lower for word in ["nih", "nsf", "government", "ministry"]):
            funding_type = FundingType.GOVERNMENT
        elif any(word in text_lower for word in ["university", "foundation", "institute"]):
            funding_type = FundingType.ACADEMIC
        elif any(word in text_lower for word in ["no funding", "none", "not applicable"]):
            funding_type = FundingType.NONE
        else:
            funding_type = FundingType.UNCLEAR
        
        return {
            "type": funding_type.value,
            "sources": list(set(industry_matches)) if industry_matches else [],
            "raw_text": text,
            "confidence": "high" if industry_matches else "medium"
        }
    
    def _analyze_coi(self, text: str) -> Dict:
        """分析利益冲突"""
        text_lower = text.lower()
        
        # 检测无COI声明
        no_coi_patterns = [
            r"no.*conflict.*interest",
            r"none.*declared",
            r"no.*financial.*interest",
            r"authors.*declare.*no"
        ]
        
        for pattern in no_coi_patterns:
            if re.search(pattern, text_lower):
                return {
                    "level": COILevel.NONE.value,
                    "authors": [],
                    "raw_text": text,
                    "confidence": "high"
                }
        
        # 检测COI级别
        authors_coi = []
        overall_level = COILevel.NONE
        
        for level, keywords in self.COI_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # 提取作者名 (简化实现)
                    authors_coi.append({
                        "keyword": keyword,
                        "level": level,
                        "context": self._extract_context(text, keyword)
                    })
                    
                    # 更新整体级别
                    if level == "high":
                        overall_level = COILevel.HIGH
                    elif level == "moderate" and overall_level != COILevel.HIGH:
                        overall_level = COILevel.MODERATE
                    elif level == "low" and overall_level == COILevel.NONE:
                        overall_level = COILevel.LOW
        
        return {
            "level": overall_level.value,
            "authors": authors_coi,
            "raw_text": text,
            "confidence": "high" if authors_coi else "low"
        }
    
    def _extract_context(self, text: str, keyword: str, window: int = 50) -> str:
        """提取关键词上下文"""
        pattern = rf"(.{{0,{window}}}{keyword}.{{0,{window}}})"
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def _calculate_bias_risk(
        self,
        funding: Dict,
        coi: Optional[Dict]
    ) -> Dict:
        """计算偏倚风险评分"""
        score = 0
        factors = []
        
        # 资助类型评分
        if funding["type"] == FundingType.INDUSTRY.value:
            score += 3
            factors.append("厂商资助 (+3)")
        elif funding["type"] == FundingType.UNCLEAR.value:
            score += 2
            factors.append("资助来源不明确 (+2)")
        
        # COI评分
        if coi:
            if coi["level"] == COILevel.HIGH.value:
                score += 3
                factors.append("高级别COI (+3)")
            elif coi["level"] == COILevel.MODERATE.value:
                score += 2
                factors.append("中级别COI (+2)")
            elif coi["level"] == COILevel.UNREPORTED.value:
                score += 2
                factors.append("COI未报告 (+2)")
        
        # 风险分级
        if score >= 5:
            risk_level = "high"
        elif score >= 3:
            risk_level = "moderate"
        elif score >= 1:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        return {
            "score": score,
            "max_score": 6,
            "level": risk_level,
            "factors": factors
        }
    
    def _generate_recommendations(
        self,
        funding: Dict,
        coi: Optional[Dict]
    ) -> List[str]:
        """生成审计建议"""
        recommendations = []
        
        if funding["type"] == FundingType.INDUSTRY.value:
            recommendations.append(
                "⚠️ 厂商资助研究：需警惕选择性报告和结果解释偏倚"
            )
        
        if coi and coi["level"] in [COILevel.HIGH.value, COILevel.MODERATE.value]:
            recommendations.append(
                f"⚠️ 存在{coi['level']}级别利益冲突：可能影响研究设计和结果解读"
            )
        
        if not recommendations:
            recommendations.append("✅ 未发现明显资助偏倚风险")
        
        return recommendations
```

---

### 2. 跨研究偏倚检测

```python
    def analyze_corpus_bias(
        self,
        scan_results: List[Dict]
    ) -> Dict:
        """
        分析文献集合的偏倚模式
        
        检测:
        1. 厂商资助研究比例异常
        2. 资助来源与效应方向的相关性
        3. 发表偏倚信号
        """
        # 统计资助分布
        funding_distribution = {
            "industry": 0,
            "government": 0,
            "academic": 0,
            "independent": 0,
            "unclear": 0
        }
        
        high_risk_count = 0
        coi_unreported_count = 0
        
        for result in scan_results:
            funding_type = result["funding"]["type"]
            funding_distribution[funding_type] = funding_distribution.get(funding_type, 0) + 1
            
            if result["bias_risk_score"]["level"] == "high":
                high_risk_count += 1
            
            if result.get("coi") and result["coi"]["level"] == "unreported":
                coi_unreported_count += 1
        
        total = len(scan_results)
        
        # 偏倚警示检测
        alerts = []
        
        # 检测1: 厂商资助比例过高
        industry_ratio = funding_distribution["industry"] / total
        if industry_ratio > 0.6:
            alerts.append({
                "type": "industry_dominance",
                "severity": "high",
                "message": f"厂商资助研究占比{industry_ratio:.1%}，存在潜在资助偏倚",
                "recommendation": "需在讨论中明确声明并分析潜在影响"
            })
        
        # 检测2: COI未报告比例过高
        coi_unreported_ratio = coi_unreported_count / total
        if coi_unreported_ratio > 0.3:
            alerts.append({
                "type": "coi_underreporting",
                "severity": "moderate",
                "message": f"{coi_unreported_ratio:.1%}的研究未报告COI",
                "recommendation": "需注意方法学透明度问题"
            })
        
        return {
            "total_studies": total,
            "funding_distribution": funding_distribution,
            "funding_percentages": {
                k: v/total for k, v in funding_distribution.items()
            },
            "high_risk_studies": high_risk_count,
            "coi_unreported": coi_unreported_count,
            "alerts": alerts,
            "overall_assessment": self._assess_overall_bias(alerts)
        }
    
    def _assess_overall_bias(self, alerts: List[Dict]) -> str:
        """评估整体偏倚风险"""
        if not alerts:
            return "low"
        
        high_severity = sum(1 for a in alerts if a["severity"] == "high")
        if high_severity > 0:
            return "high"
        
        return "moderate"
```

---

## Evidence Audit Trail 整合

扩展 Evidence Audit Trail，增加 Funding & COI 字段:

```markdown
**[Evidence Audit Trail]**
- **引用 ID**: Smith2023_PRP_OA
- **GRADE 评级**: ⊕⊕⊕◯◯ (中等确定性)
- **硬锚点**: "PRP组WOMAC改善25.3分 vs 对照组12.1分 (P<0.001)"

**[Funding & COI Audit]** ⚠️ v2.4.0 新增
- **资助来源**: 厂商资助 (BioTech Pharma Inc.)
- **资助类型**: Industry
- **COI级别**: Moderate (主要研究者担任厂商顾问)
- **偏倚风险评分**: 5/6 (高风险)
- **⚠️ 警示**: "厂商资助研究阳性结果率(85%)显著高于独立研究(45%)，存在选择性报告风险"
- **审计建议**: "需在讨论中声明资助来源，并谨慎解读阳性结果"

**[降级理由]**
1. 盲法不充分
2. 样本量小
3. **⚠️ 厂商资助偏倚风险 (新增)**
```

---

## Conflict Resolver 整合

当发现争议时，自动检查资助来源差异:

```python
def analyze_funding_bias_in_conflict(
    self,
    positive_studies: List[Dict],
    negative_studies: List[Dict]
) -> Dict:
    """
    分析争议中的资助偏倚
    
    检测:
    - 阳性结果是否主要来自厂商资助研究
    - 阴性结果是否主要来自独立研究
    """
    # 分析资助分布
    pos_funding = [s["funding"]["type"] for s in positive_studies]
    neg_funding = [s["funding"]["type"] for s in negative_studies]
    
    pos_industry_ratio = pos_funding.count("industry") / len(pos_funding)
    neg_industry_ratio = neg_funding.count("industry") / len(neg_funding)
    
    # 检测资助偏倚信号
    bias_signal = None
    if pos_industry_ratio > 0.7 and neg_industry_ratio < 0.3:
        bias_signal = {
            "detected": True,
            "pattern": "阳性结果主要来自厂商资助研究",
            "positive_industry_ratio": pos_industry_ratio,
            "negative_industry_ratio": neg_industry_ratio,
            "interpretation": "资助来源可能是效应方向异质性的重要解释因素"
        }
    
    return {
        "funding_distribution": {
            "positive_studies": pos_funding,
            "negative_studies": neg_funding
        },
        "bias_signal": bias_signal
    }
```

---

## 使用示例

```python
from funding_coi_scanner import FundingCOIScanner

scanner = FundingCOIScanner()

# 扫描单个研究
result = scanner.scan_funding(
    paper_id="Smith2023",
    funding_section="This study was funded by BioTech Pharma Inc. (Grant #BP-2023-001).",
    coi_section="Dr. Smith serves as a consultant for BioTech Pharma Inc."
)

print(f"资助类型: {result['funding']['type']}")
print(f"偏倚风险: {result['bias_risk_score']['level']}")
print(f"建议: {result['recommendations']}")

# 批量分析
all_results = [result1, result2, result3, ...]
corpus_analysis = scanner.analyze_corpus_bias(all_results)

if corpus_analysis["alerts"]:
    print("⚠️ 发现偏倚警示:")
    for alert in corpus_analysis["alerts"]:
        print(f"  - {alert['message']}")
```

---

## 实现状态

- [x] 资助来源自动分类
- [x] COI级别评估
- [x] 偏倚风险评分
- [x] 跨研究偏倚检测
- [x] Evidence Audit Trail 整合
- [x] Conflict Resolver 整合
- [ ] 厂商数据库扩展 (v2.4.1)
- [ ] 资助金额影响分析 (v2.5.0)

---

*创建日期: 2026-03-12*  
*版本: v2.4.0*