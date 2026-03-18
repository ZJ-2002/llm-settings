# Clinical Subgroup Probe 临床亚组探针

> **版本**: v2.4.0  
> **分类**: P1 - 高优先级  
> **功能**: 强制检索Methods章节，挖掘隐性变量，深度归因

---

## 模块定位

**问题**: Conflict Resolver 虽能识别研究间差异，但依赖AI主动性，缺乏强制性Methods章节检索。

**目标**: 将隐性变量挖掘从"可选"变为"强制"，确保不遗漏关键的方法学差异。

---

## 核心功能

### 1. 专科特异性探测协议

#### 脊柱外科探测协议 (LDH专用)

```yaml
# ldh_probe_protocol.yaml

domain: "lumbar_disc_herniation"
description: "腰椎间盘突出症手术研究隐性变量探测"

probe_categories:
  - category: "手术入路细节"
    priority: "P0"
    variables:
      - name: "approach_type"
        description: "手术入路类型"
        options: ["单侧", "双侧", "椎板间", "经椎间孔", "旁正中"]
        extraction_prompt: "提取手术入路的具体描述"
        
      - name: "decompression_scope"
        description: "减压范围"
        options: ["单纯髓核摘除", "有限减压", "广泛椎板切除", "全椎板切除"]
        
      - name: "visualization_method"
        description: "术中辅助"
        options: ["显微镜", "椎间孔镜", "裸眼", "放大镜", "导航辅助"]
        
      - name: "disc_removal_extent"
        description: "髓核摘除程度"
        options: ["Limited", "Aggressive", "Subtotal", "只摘除突出部分"]

  - category: "患者特异性因素"
    priority: "P1"
    variables:
      - name: "modic_changes"
        description: "Modic改变"
        options: ["Modic I", "Modic II", "Modic III", "无", "未报告"]
        
      - name: "disc_degeneration_grade"
        description: "椎间盘退变分级"
        options: ["Pfirrmann I", "II", "III", "IV", "V", "未分级"]
        
      - name: "herniation_type"
        description: "突出类型"
        options: ["包容型", "非包容型", "游离型", "钙化型"]

  - category: "康复与随访"
    priority: "P1"
    variables:
      - name: "rehabilitation_protocol"
        description: "康复方案"
        options: ["术后1周负重", "术后4周负重", "术后8周负重", "渐进式", "未标准化"]
        
      - name: "follow_up_schedule"
        description: "随访频率"
        pattern: "提取随访时间点: 术后X周/月/年"

  - category: "术者因素"
    priority: "P2"
    variables:
      - name: "surgeon_volume"
        description: "术者年度手术量"
        threshold: ">50例/年 为高容量"
        
      - name: "learning_curve_phase"
        description: "学习曲线阶段"
        options: ["初期(<50例)", "中期(50-200例)", "成熟期(>200例)"]

extraction_rules:
  - 如果文献未报告某项变量，标记为"未报告"而非忽略
  - 对于连续变量，提取具体数值而非仅分类
  - 注意提取"排除标准"中可能影响外推性的条目
```

#### 通用探测框架

```python
# clinical_subgroup_probe.py

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import re

class ProbePriority(Enum):
    P0 = "critical"      # 必须提取
    P1 = "important"     # 强烈建议提取
    P2 = "recommended"   # 建议提取

@dataclass
class ProbeVariable:
    """探测变量定义"""
    name: str
    description: str
    category: str
    priority: ProbePriority
    extraction_method: str          # "keyword", "regex", "llm_extract"
    options: Optional[List[str]] = None
    regex_pattern: Optional[str] = None
    validation_rules: Optional[List[str]] = None

class ClinicalSubgroupProbe:
    """
    临床亚组探针核心类
    
    强制检索Methods章节，挖掘隐性变量
    """
    
    def __init__(self, domain: str = "general"):
        self.domain = domain
        self.probe_protocol = self._load_protocol(domain)
        self.extraction_results = {}
    
    def _load_protocol(self, domain: str) -> Dict:
        """加载专科特异性探测协议"""
        protocols = {
            "spine_surgery": self._spine_surgery_protocol(),
            "orthopedics": self._orthopedics_protocol(),
            "oncology": self._oncology_protocol(),
            "cardiology": self._cardiology_protocol(),
            "general": self._general_protocol()
        }
        return protocols.get(domain, protocols["general"])
    
    def _spine_surgery_protocol(self) -> Dict:
        """脊柱外科探测协议"""
        return {
            "domain": "spine_surgery",
            "categories": [
                {
                    "name": "手术技术细节",
                    "variables": [
                        ProbeVariable(
                            name="approach_type",
                            description="手术入路类型",
                            category="surgical_technique",
                            priority=ProbePriority.P0,
                            extraction_method="keyword",
                            options=[" posterior", "transforaminal", "interlaminar", 
                                     "bilateral", "unilateral"]
                        ),
                        ProbeVariable(
                            name="decompression_extent",
                            description="减压范围",
                            category="surgical_technique",
                            priority=ProbePriority.P0,
                            extraction_method="regex",
                            regex_pattern=r"(limited|partial|total|complete)\s+(decompression|laminectomy|discectomy)"
                        ),
                        ProbeVariable(
                            name="visualization",
                            description="术中可视化",
                            category="surgical_technique",
                            priority=ProbePriority.P1,
                            extraction_method="keyword",
                            options=["microscope", "endoscope", "loupe", "naked eye", "navigation"]
                        ),
                        ProbeVariable(
                            name="surgeon_experience",
                            description="术者经验",
                            category="operator_factor",
                            priority=ProbePriority.P1,
                            extraction_method="regex",
                            regex_pattern=r"(\d+)\s*(cases|procedures|surgeries)\s*(per year|annually)?"
                        )
                    ]
                }
            ]
        }
    
    def probe_methods_section(
        self,
        paper_id: str,
        methods_text: str,
        strict_mode: bool = True
    ) -> Dict:
        """
        探测Methods章节
        
        Args:
            paper_id: 文献唯一标识
            methods_text: Methods章节全文
            strict_mode: 严格模式 (未报告变量标记为"未报告")
            
        Returns:
            探测结果
        """
        results = {
            "paper_id": paper_id,
            "domain": self.domain,
            "extraction_date": "2026-03-12",
            "categories": {}
        }
        
        for category in self.probe_protocol["categories"]:
            cat_name = category["name"]
            results["categories"][cat_name] = {
                "variables": {},
                "coverage_rate": 0.0
            }
            
            reported_count = 0
            total_count = len(category["variables"])
            
            for variable in category["variables"]:
                value = self._extract_variable(variable, methods_text)
                
                if value or strict_mode:
                    results["categories"][cat_name]["variables"][variable.name] = {
                        "value": value if value else "未报告",
                        "description": variable.description,
                        "priority": variable.priority.value
                    }
                    
                    if value:
                        reported_count += 1
            
            # 计算覆盖率
            results["categories"][cat_name]["coverage_rate"] = reported_count / total_count
        
        return results
    
    def _extract_variable(
        self,
        variable: ProbeVariable,
        text: str
    ) -> Optional[str]:
        """提取单个变量"""
        
        if variable.extraction_method == "keyword":
            # 关键词匹配
            for option in variable.options or []:
                if option.lower() in text.lower():
                    return option
                    
        elif variable.extraction_method == "regex":
            # 正则表达式匹配
            if variable.regex_pattern:
                match = re.search(variable.regex_pattern, text, re.IGNORECASE)
                if match:
                    return match.group(0)
                    
        elif variable.extraction_method == "llm_extract":
            # LLM提取 (复杂变量)
            return self._llm_extract(variable, text)
        
        return None
    
    def _llm_extract(self, variable: ProbeVariable, text: str) -> Optional[str]:
        """使用LLM提取复杂变量"""
        # 实际实现需要调用LLM
        # 这里提供框架
        prompt = f"""
        从以下Methods章节中提取"{variable.description}"的信息:
        
        {text[:2000]}
        
        只返回提取到的值，如果没有找到则返回"未找到"。
        """
        # 返回 LLM(prompt)
        return None  # 占位
    
    def compare_studies(
        self,
        study_results: List[Dict]
    ) -> Dict:
        """
        比较多个研究的探测结果
        
        输出Conflict Resolver可用的差异分析
        """
        comparison = {
            "n_studies": len(study_results),
            "common_variables": {},
            "heterogeneous_variables": {},
            "unreported_variables": {}
        }
        
        # 收集所有变量
        all_variables = set()
        for study in study_results:
            for cat_name, cat_data in study["categories"].items():
                all_variables.update(cat_data["variables"].keys())
        
        # 分析每个变量
        for var_name in all_variables:
            values = []
            unreported_count = 0
            
            for study in study_results:
                found = False
                for cat_data in study["categories"].values():
                    if var_name in cat_data["variables"]:
                        value = cat_data["variables"][var_name]["value"]
                        if value != "未报告":
                            values.append({
                                "study": study["paper_id"],
                                "value": value
                            })
                        else:
                            unreported_count += 1
                        found = True
                        break
                
                if not found:
                    unreported_count += 1
            
            # 判断异质性
            unique_values = set(v["value"] for v in values)
            
            if len(unique_values) <= 1 and unreported_count == 0:
                # 所有研究报告一致
                comparison["common_variables"][var_name] = {
                    "value": list(unique_values)[0] if unique_values else None,
                    "n_studies": len(values)
                }
            elif unreported_count > len(study_results) * 0.5:
                # 超过50%未报告
                comparison["unreported_variables"][var_name] = {
                    "reported": len(values),
                    "unreported": unreported_count
                }
            else:
                # 存在异质性
                comparison["heterogeneous_variables"][var_name] = {
                    "values": values,
                    "unique_values": list(unique_values),
                    "unreported": unreported_count
                }
        
        return comparison
```

---

### 2. 与 Conflict Resolver 集成

```python
# conflict_resolver_integration.py

class ConflictResolverWithProbe:
    """
    集成 Clinical Subgroup Probe 的 Conflict Resolver
    """
    
    def __init__(self, probe: ClinicalSubgroupProbe):
        self.probe = probe
    
    def resolve_conflict(
        self,
        study_a: Dict,
        study_b: Dict,
        outcome_difference: str
    ) -> Dict:
        """
        解析研究间冲突
        
        增强版: 自动探测隐性变量差异
        """
        # 基础Conflict Resolver分析
        base_analysis = self._base_conflict_analysis(study_a, study_b)
        
        # 使用Probe探测隐性变量
        probe_results_a = self.probe.probe_methods_section(
            study_a["id"],
            study_a["methods_text"]
        )
        probe_results_b = self.probe.probe_methods_section(
            study_b["id"],
            study_b["methods_text"]
        )
        
        # 比较探测结果
        comparison = self.probe.compare_studies([probe_results_a, probe_results_b])
        
        # 生成增强版Conflict Resolver报告
        enhanced_report = {
            **base_analysis,
            "subgroup_probe_analysis": {
                "heterogeneous_factors": comparison["heterogeneous_variables"],
                "unreported_factors": comparison["unreported_variables"],
                "key_confounders": self._identify_key_confounders(
                    comparison["heterogeneous_variables"],
                    outcome_difference
                )
            }
        }
        
        return enhanced_report
    
    def _identify_key_confounders(
        self,
        heterogeneous_vars: Dict,
        outcome: str
    ) -> List[Dict]:
        """识别关键混杂因素"""
        key_confounders = []
        
        # 根据结局类型判断关键混杂因素
        confounder_weights = {
            # 手术结局相关的关键混杂因素
            "surgical_outcome": ["surgeon_experience", "visualization", "decompression_extent"],
            "functional_outcome": ["rehabilitation_protocol", "follow_up_schedule"],
            "radiographic_outcome": ["disc_degeneration_grade", "modic_changes"]
        }
        
        for var_name, var_data in heterogeneous_vars.items():
            weight = 0
            for outcome_type, important_vars in confounder_weights.items():
                if var_name in important_vars:
                    weight += 1
            
            if weight > 0:
                key_confounders.append({
                    "variable": var_name,
                    "weight": weight,
                    "values": var_data["values"],
                    "interpretation": f"该变量可能是{outcome}差异的重要原因"
                })
        
        return sorted(key_confounders, key=lambda x: x["weight"], reverse=True)
```

---

## 使用示例

### 示例1: 脊柱外科研究探测

```python
from clinical_subgroup_probe import ClinicalSubgroupProbe

# 初始化脊柱外科探针
probe = ClinicalSubgroupProbe(domain="spine_surgery")

# 探测单个研究的Methods章节
methods_text = """
Methods:
All surgeries were performed by a single senior surgeon with >100 cases per year.
A unilateral transforaminal approach was used under microscopic visualization.
Limited discectomy was performed, removing only the herniated fragment.
...
"""

results = probe.probe_methods_section(
    paper_id="Smith2023_LDH",
    methods_text=methods_text,
    strict_mode=True
)

print(f"提取变量数: {len(results['categories'])}")
print(f"覆盖率: {results['categories']['手术技术细节']['coverage_rate']:.2%}")
```

### 示例2: 多研究比较

```python
# 探测多个研究
studies = [
    {"id": "Smith2023", "methods_text": "..."},
    {"id": "Wang2024", "methods_text": "..."},
]

study_results = []
for study in studies:
    result = probe.probe_methods_section(study["id"], study["methods_text"])
    study_results.append(result)

# 比较研究差异
comparison = probe.compare_studies(study_results)

print("异质性变量:")
for var, data in comparison["heterogeneous_variables"].items():
    print(f"  - {var}: {data['unique_values']}")
```

---

## 协议扩展指南

### 添加新专科协议

```python
def _new_specialty_protocol(self) -> Dict:
    return {
        "domain": "new_specialty",
        "categories": [
            {
                "name": "专科特异性变量类别",
                "variables": [
                    ProbeVariable(
                        name="variable_name",
                        description="变量描述",
                        category="category_name",
                        priority=ProbePriority.P0,
                        extraction_method="keyword",
                        options=["option1", "option2"]
                    )
                ]
            }
        ]
    }
```

---

## 实现状态

- [x] 脊柱外科探测协议 (LDH)
- [x] 通用探测框架
- [x] 多研究比较功能
- [x] Conflict Resolver 集成
- [ ] 肿瘤科探测协议 (v2.4.1)
- [ ] 心血管科探测协议 (v2.4.1)
- [ ] 自动LLM提取增强 (v2.5.0)

---

*创建日期: 2026-03-12*  
*版本: v2.4.0*