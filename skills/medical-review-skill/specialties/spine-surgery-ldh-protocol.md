# Spine Surgery LDH Protocol 脊柱外科LDH专用协议

> **版本**: v2.4.0  
> **分类**: P3 - 专科特异性  
> **功能**: 针对腰椎间盘突出症的专科特异性探测和熔断规则

---

## 协议定位

**用户背景**: 脊柱外科首席医师，关注LDH（腰椎间盘突出）领域优化

**目标**: 为LDH研究提供专科特异性的隐性变量挖掘和质量控制

---

## 1. LDH隐性变量探测协议

### 1.1 强制探测维度

```yaml
# ldh_mandatory_probes.yaml

protocol_name: "LDH Surgical Outcomes Assessment"
version: "2.4.0"
domain: "lumbar_disc_herniation"

probe_categories:
  surgical_technique:
    priority: P0
    description: "手术技术细节 - 影响疗效的核心因素"
    variables:
      - name: approach_type
        question: "手术入路类型"
        options:
          - value: "posterolateral"
            description: "后外侧入路 (最常用)"
          - value: "transforaminal"
            description: "经椎间孔入路"
          - value: "interlaminar"
            description: "椎板间入路"
          - value: "bilateral"
            description: "双侧入路"
          - value: "unilateral"
            description: "单侧入路"
        extraction_prompt: "检索Methods中'approach','access','route'等关键词"
        
      - name: decompression_scope
        question: "减压范围"
        options:
          - value: "limited_discectomy"
            description: "单纯髓核摘除 (只取突出部分)"
          - value: "subtotal_discectomy"
            description: "次全髓核摘除"
          - value: "aggressive_discectomy"
            description: "广泛髓核摘除"
          - value: "laminectomy"
            description: "椎板切除"
        clinical_impact: "减压范围与复发率密切相关"
        
      - name: visualization
        question: "术中可视化辅助"
        options:
          - value: "microscope"
            description: "显微镜"
            quality_score: 3
          - value: "endoscope"
            description: "椎间孔镜/内窥镜"
            quality_score: 3
          - value: "loupe"
            description: "手术放大镜"
            quality_score: 2
          - value: "naked_eye"
            description: "裸眼"
            quality_score: 1
            warning: "裸眼手术在现代LDH手术中已不推荐"
            
      - name: annular_preservation
        question: "纤维环保留程度"
        options:
          - value: "intact"
            description: "完整保留 (只切开小口取髓核)"
          - value: "partial_repair"
            description: "部分切除+修复"
          - value: "wide_opening"
            description: "广泛切开"
        clinical_significance: "与术后脊柱稳定性相关"

  patient_phenotyping:
    priority: P1
    description: "患者表型特征 - 影响预后的重要因素"
    variables:
      - name: modic_changes
        question: "Modic改变"
        options:
          - value: "modic_I"
            description: "Modic I型 (水肿型)"
            prognosis: "炎症活跃，可能对保守治疗反应好"
          - value: "modic_II"
            description: "Modic II型 (脂肪型)"
            prognosis: "退变稳定，手术效果可能一般"
          - value: "modic_III"
            description: "Modic III型 (硬化型)"
          - value: "none"
            description: "无Modic改变"
          - value: "not_reported"
            description: "未报告"
        importance: "高 - Modic改变与术后腰痛残留密切相关"
        
      - name: disc_degeneration_grade
        question: "椎间盘退变分级 (Pfirrmann)"
        options: ["I", "II", "III", "IV", "V", "not_graded"]
        
      - name: herniation_type
        question: "椎间盘突出类型"
        options:
          - value: "contained"
            description: "包容型"
          - value: "non_contained"
            description: "非包容型"
          - value: "sequestrated"
            description: "游离型"
          - value: "calcified"
            description: "钙化型"
        surgical_implication: "游离型和钙化型手术难度更大"
        
      - name: symptom_duration
        question: "症状持续时间"
        unit: "months"
        thresholds:
          acute: "< 3 months"
          subacute: "3-12 months"
          chronic: "> 12 months"
        prognostic_significance: "慢性症状(>12月)预后较差"

  rehabilitation:
    priority: P1
    description: "康复方案 - 影响功能恢复"
    variables:
      - name: rehabilitation_protocol
        question: "术后康复方案"
        options:
          - value: "early_mobilization"
            description: "早期活动 (术后24-48h下床)"
          - value: "delayed_mobilization"
            description: "延迟活动 (术后1-2周)"
          - value: "structured_PT"
            description: "结构化物理治疗"
          - value: "self_directed"
            description: "自主康复"
            warning: "缺乏标准化可能影响结果可比性"
            
      - name: return_to_work_timeline
        question: "返回工作时间"
        options:
          - value: "<4weeks"
          - value: "4-8weeks"
          - value: "8-12weeks"
          - value: ">12weeks"

  surgeon_factors:
    priority: P2
    description: "术者因素 - 影响技术效果"
    variables:
      - name: surgeon_volume
        question: "术者年度LDH手术量"
        unit: "cases/year"
        thresholds:
          low: "<30"
          medium: "30-100"
          high: ">100"
        evidence: "高容量术者并发症率更低，疗效更好"
        
      - name: learning_curve_phase
        question: "学习曲线阶段"
        options:
          - value: "early"
            description: "初期 (<50例)"
            warning: "学习曲线阶段结果可能不代表技术真实效果"
          - value: "intermediate"
            description: "中期 (50-200例)"
          - value: "mature"
            description: "成熟期 (>200例)"
```

---

### 1.2 提取执行指令

```python
# ldh_extraction_engine.py

class LDHExtractionEngine:
    """
    LDH专用提取引擎
    
    强制检索Methods章节，提取LDH特异性变量
    """
    
    LDH_PROBE_PROMPT = """
    你是一名脊柱外科方法学专家。请仔细阅读以下LDH研究的Methods章节，
    并提取以下关键信息。如果某项信息未报告，请明确标注"未报告"。
    
    ## 手术技术细节 (必须提取)
    1. 手术入路类型: [ ] 后外侧 [ ] 经椎间孔 [ ] 椎板间 [ ] 其他:___
    2. 减压范围: [ ] 单纯髓核摘除 [ ] 次全摘除 [ ] 广泛切除
    3. 可视化辅助: [ ] 显微镜 [ ] 椎间孔镜 [ ] 放大镜 [ ] 裸眼
    4. 纤维环处理: [ ] 保留 [ ] 部分切除 [ ] 广泛切开
    
    ## 患者分型 (尽量提取)
    5. Modic改变: [ ] I型 [ ] II型 [ ] III型 [ ] 无 [ ] 未报告
    6. 椎间盘退变分级 (Pfirrmann): [ ] I [ ] II [ ] III [ ] IV [ ] V [ ] 未分级
    7. 突出类型: [ ] 包容型 [ ] 非包容型 [ ] 游离型 [ ] 钙化型
    8. 症状持续时间: ___月 (急性<3月/亚急性3-12月/慢性>12月)
    
    ## 康复方案 (尽量提取)
    9. 术后负重时间: 术后___周
    10. 物理治疗: [ ] 有结构化方案 [ ] 无 [ ] 未报告
    
    ## 术者因素 (尽量提取)
    11. 术者年手术量: ___例/年
    12. 学习曲线: [ ] 初期(<50例) [ ] 中期(50-200例) [ ] 成熟期(>200例)
    
    Methods章节:
    {methods_text}
    
    请以结构化格式输出提取结果。
    """
    
    def __init__(self):
        self.extraction_results = []
    
    def extract_from_paper(
        self,
        paper_id: str,
        methods_text: str,
        use_llm: bool = True
    ) -> Dict:
        """
        从单篇文献提取LDH变量
        
        Args:
            paper_id: 文献ID
            methods_text: Methods章节全文
            use_llm: 是否使用LLM增强提取
            
        Returns:
            提取结果
        """
        # 基础正则提取
        basic_extraction = self._regex_extraction(methods_text)
        
        # LLM增强提取
        if use_llm:
            llm_extraction = self._llm_extraction(methods_text)
            # 合并结果
            extraction = self._merge_extractions(basic_extraction, llm_extraction)
        else:
            extraction = basic_extraction
        
        # 计算提取完整度
        p0_completeness = self._calculate_completeness(extraction, priority="P0")
        p1_completeness = self._calculate_completeness(extraction, priority="P1")
        
        result = {
            "paper_id": paper_id,
            "extraction": extraction,
            "completeness": {
                "P0": p0_completeness,
                "P1": p1_completeness,
                "overall": (p0_completeness * 0.6 + p1_completeness * 0.4)
            },
            "quality_score": self._calculate_quality_score(extraction),
            "missing_critical": self._identify_missing_critical(extraction)
        }
        
        self.extraction_results.append(result)
        return result
    
    def _regex_extraction(self, text: str) -> Dict:
        """正则表达式提取"""
        import re
        
        extraction = {}
        text_lower = text.lower()
        
        # 入路类型
        if "transforaminal" in text_lower:
            extraction["approach_type"] = "transforaminal"
        elif "interlaminar" in text_lower:
            extraction["approach_type"] = "interlaminar"
        elif "posterolateral" in text_lower:
            extraction["approach_type"] = "posterolateral"
        
        # 可视化
        if "microscope" in text_lower or "microscopic" in text_lower:
            extraction["visualization"] = "microscope"
        elif "endoscope" in text_lower or "endoscopic" in text_lower:
            extraction["visualization"] = "endoscope"
        
        # 手术量
        volume_match = re.search(r'(\d+)\s*(cases?|surgeries?)\s*(per year|annually|/year)', text_lower)
        if volume_match:
            extraction["surgeon_volume"] = int(volume_match.group(1))
        
        return extraction
    
    def _calculate_quality_score(self, extraction: Dict) -> int:
        """计算方法学质量评分"""
        score = 0
        
        # 显微镜/内窥镜 (+3)
        if extraction.get("visualization") in ["microscope", "endoscope"]:
            score += 3
        
        # 报告了手术量 (+2)
        if extraction.get("surgeon_volume"):
            score += 2
        
        # 报告了Modic改变 (+2)
        if extraction.get("modic_changes") and extraction["modic_changes"] != "not_reported":
            score += 2
        
        # 标准化康复方案 (+2)
        if extraction.get("rehabilitation_protocol") == "structured_PT":
            score += 2
        
        return score
```

---

## 2. LDH专用熔断规则

```python
# ldh_circuit_breaker.py

LDH_CIRCUIT_BREAKER_RULES = {
    "recurrence_rate": {
        "description": "复发率合理性检查",
        "normal_range": [0.05, 0.25],  # 5-25%
        "warning_range": [0.25, 0.40],  # 25-40% 警告
        "fuse_condition": "value < 0.01 or value > 0.50",
        "fuse_message": """
        🚨 LDH复发率熔断器触发！
        
        检测到异常复发率: {value:.1%}
        - 正常范围: 5-25%
        - 您的数值: {value:.1%}
        
        可能原因:
        1. 复发定义不一致 (再手术 vs 症状复发)
        2. 随访时间差异
        3. 患者选择偏倚
        4. 手术技术差异
        
        强制操作:
        1. 核对复发定义
        2. 检查随访时长
        3. 人工确认原始数据
        """
    },
    
    "reoperation_rate": {
        "description": "再手术率合理性检查",
        "normal_range": [0.02, 0.15],
        "fuse_condition": "value > 0.30",
        "fuse_message": "再手术率异常高，需检查手术指征选择和手术质量"
    },
    
    "vas_improvement": {
        "description": "VAS疼痛改善幅度",
        "normal_range": [30, 70],  # mm
        "unit": "mm",
        "fuse_condition": "value > 90 or value < 10",
        "fuse_message": "VAS改善幅度异常，需核对基线水平和测量方法"
    },
    
    "odi_improvement": {
        "description": "ODI评分改善",
        "normal_range": [15, 40],  # points
        "unit": "points",
        "fuse_condition": "value > 60",
        "fuse_message": "ODI改善幅度过大，可能存在测量偏倚或患者选择问题"
    },
    
    "surgical_time": {
        "description": "手术时间",
        "normal_range": [30, 120],  # minutes
        "unit": "minutes",
        "fuse_condition": "value > 300 or value < 15",
        "fuse_message": "手术时间异常，需确认手术复杂度记录"
    },
    
    "blood_loss": {
        "description": "术中出血量",
        "normal_range": [20, 200],  # mL
        "unit": "mL",
        "fuse_condition": "value > 1000",
        "fuse_message": "出血量异常高，可能存在手术并发症"
    },
    
    "hospital_stay": {
        "description": "住院天数",
        "normal_range": [1, 5],  # days
        "unit": "days",
        "fuse_condition": "value > 14",
        "fuse_message": "住院时间过长，需检查术后并发症"
    }
}

class LDHCircuitBreaker:
    """LDH专用熔断器"""
    
    def check_value(self, parameter: str, value: float, unit: str = None) -> Dict:
        """检查数值是否在合理范围"""
        rule = LDH_CIRCUIT_BREAKER_RULES.get(parameter)
        if not rule:
            return {"status": "unknown_parameter"}
        
        # 执行熔断检查
        normal_range = rule["normal_range"]
        
        if value < normal_range[0] or value > normal_range[1]:
            if self._evaluate_fuse_condition(rule["fuse_condition"], value):
                return {
                    "status": "FUSE_TRIGGERED",
                    "level": "CRITICAL",
                    "message": rule["fuse_message"].format(value=value),
                    "parameter": parameter,
                    "value": value,
                    "expected_range": normal_range
                }
            else:
                return {
                    "status": "WARNING",
                    "level": "MODERATE",
                    "message": f"数值偏离正常范围",
                    "parameter": parameter,
                    "value": value,
                    "expected_range": normal_range
                }
        
        return {
            "status": "PASS",
            "parameter": parameter,
            "value": value
        }
    
    def _evaluate_fuse_condition(self, condition: str, value: float) -> bool:
        """评估熔断条件"""
        try:
            # 安全评估条件表达式
            return eval(condition.format(value=value))
        except:
            return False
```

---

## 3. 手术陷阱与学习曲线模块

```python
# surgical_pitfall_analyzer.py

class SurgicalPitfallAnalyzer:
    """
    LDH手术陷阱与学习曲线分析器
    
    汇总术中并发症与术者经验的相关性
    """
    
    LDH_SPECIFIC_COMPLICATIONS = [
        "dural_tear",           # 硬膜囊撕裂
        "nerve_root_injury",    # 神经根损伤
        "incomplete_decompression",  # 减压不彻底
        "wrong_level",          # 节段错误
        "excessive_bone_removal",  # 骨质过度切除
        "recurrent_herniation_same_level",  # 同节段复发
        "instability",          # 节段不稳
        "epidural_hematoma",    # 硬膜外血肿
    ]
    
    def analyze_learning_curve(
        self,
        studies_data: List[Dict]
    ) -> Dict:
        """
        分析学习曲线
        
        检测并发症率与术者经验的关系
        """
        # 按术者经验分组
        early_phase = []   # <50例
        mid_phase = []     # 50-200例
        mature_phase = []  # >200例
        
        for study in studies_data:
            volume = study.get("surgeon_volume", 0)
            complications = study.get("complications", [])
            
            if volume < 50:
                early_phase.extend(complications)
            elif volume < 200:
                mid_phase.extend(complications)
            else:
                mature_phase.extend(complications)
        
        # 计算各阶段并发症率
        def calc_rate(complications, complication_type):
            if not complications:
                return 0
            return sum(1 for c in complications if c["type"] == complication_type) / len(complications)
        
        analysis = {
            "learning_curve_phases": {
                "early": {
                    "n_studies": len([s for s in studies_data if s.get("surgeon_volume", 0) < 50]),
                    "dural_tear_rate": calc_rate(early_phase, "dural_tear"),
                    "nerve_injury_rate": calc_rate(early_phase, "nerve_root_injury"),
                    "wrong_level_rate": calc_rate(early_phase, "wrong_level")
                },
                "mature": {
                    "n_studies": len([s for s in studies_data if s.get("surgeon_volume", 0) >= 200]),
                    "dural_tear_rate": calc_rate(mature_phase, "dural_tear"),
                    "nerve_injury_rate": calc_rate(mature_phase, "nerve_root_injury"),
                    "wrong_level_rate": calc_rate(mature_phase, "wrong_level")
                }
            }
        }
        
        # 检测学习曲线效应
        early_dural = analysis["learning_curve_phases"]["early"]["dural_tear_rate"]
        mature_dural = analysis["learning_curve_phases"]["mature"]["dural_tear_rate"]
        
        if early_dural > mature_dural * 2:
            analysis["learning_curve_effect"] = {
                "detected": True,
                "magnitude": f"初期硬膜囊撕裂率是成熟期的{early_dural/mature_dural:.1f}倍",
                "clinical_implication": "该技术存在明显的学习曲线，初期开展需谨慎"
            }
        
        return analysis
    
    def generate_pitfall_summary(self, analysis: Dict) -> str:
        """生成手术陷阱汇总"""
        summary = """
## LDH手术陷阱与学习曲线分析

### 学习曲线效应
"""
        if analysis.get("learning_curve_effect", {}).get("detected"):
            effect = analysis["learning_curve_effect"]
            summary += f"""
⚠️ **检测到明显学习曲线**
- {effect['magnitude']}
- {effect['clinical_implication']}

**建议**: 在综述讨论中明确指出学习曲线对结果的影响，
建议读者在开展该技术前确保充足的培训。
"""
        
        summary += """
### 常见手术陷阱
"""
        # 添加常见陷阱
        pitfalls = [
            {
                "trap": "硬膜囊撕裂",
                "frequency": "初期5-15%，成熟期<5%",
                "prevention": "使用显微镜/内窥镜，精细操作"
            },
            {
                "trap": "减压不彻底",
                "frequency": "导致早期复发的主要原因",
                "prevention": "术中神经根减压验证"
            },
            {
                "trap": "节段错误",
                "frequency": "0.5-2%",
                "prevention": "术中X线确认"
            }
        ]
        
        for i, pitfall in enumerate(pitfalls, 1):
            summary += f"""
{i}. **{pitfall['trap']}**
   - 发生率: {pitfall['frequency']}
   - 预防措施: {pitfall['prevention']}
"""
        
        return summary
```

---

## 4. 与主Skill的集成

```markdown
## 在 review-checklist 中增加LDH专项检查

### LDH专项方法学审计
- [ ] 是否提取了手术入路类型？
- [ ] 是否提取了减压范围？
- [ ] 是否记录了Modic改变？
- [ ] 是否分析了术者经验混杂？
- [ ] 是否讨论了学习曲线影响？
- [ ] 复发定义是否一致？

### LDH数值熔断检查
- [ ] 复发率在5-25%范围内？
- [ ] VAS改善在30-70mm范围内？
- [ ] 手术时间在30-120分钟范围内？
```

---

## 实现状态

- [x] LDH隐性变量探测协议
- [x] 强制提取执行指令
- [x] LDH专用熔断规则
- [x] 手术陷阱与学习曲线模块
- [x] 方法学质量评分
- [ ] 自动化提取实现 (v2.5.0)
- [ ] 与其他脊柱疾病扩展 (v2.4.1)

---

*创建日期: 2026-03-12*  
*版本: v2.4.0*  
*专科: 脊柱外科 - 腰椎间盘突出症*