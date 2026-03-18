# 专科黑匣子 (Specialty Black Box)

> **版本**: v2.5.1  
> **定位**: 专科特异性数据验证与熔断机制  
> **当前实现**: 脊柱外科 (Spine Surgery) - LDH 专用

---

## 核心概念

**专科黑匣子**是针对特定医学专科的深度验证系统，包含：
1. **专科特异性解剖参数熔断器**
2. **专科手术技术指标验证**
3. **专科影像学参数检查**
4. **专科临床决策规则**

**设计理念**: 通用熔断器（血糖/身高）对于专科专家来说太基础，需要针对专科的深度验证。

---

## 脊柱外科专科黑匣子 (Spine Surgery Black Box)

### 1. 解剖参数熔断器

```yaml
# spine_surgery_circuit_breakers.yaml

spine_surgery:
  
  # ==================== 腰椎解剖参数 ====================
  lumbar_anatomy:
    
    spinal_canal_diameter:
      name: "椎管径线"
      name_en: "Spinal Canal Diameter"
      field_patterns: ["canal", "椎管", "spinal canal", "AP diameter"]
      expected_units: ["mm"]
      normal_range:
        lumbar: [15, 27]  # L1-L5正常范围
        critical_threshold: 10  # <10mm为绝对狭窄
      fuse_conditions:
        - "value < 10 or value > 30"
        - "unit == 'cm' and value < 1.0"  # 可能是mm误标为cm
      severity: "CRITICAL"
      clinical_note: "椎管径线<10mm提示绝对椎管狭窄，>30mm需核对测量位置"
    
    ligamentum_flavum_thickness:
      name: "黄韧带厚度"
      name_en: "Ligamentum Flavum Thickness"
      field_patterns: ["ligamentum flavum", "黄韧带", "LF", "ligament thickness"]
      expected_units: ["mm"]
      normal_range:
        normal: [2, 4]
        hypertrophy: [4, 6]  # 增厚
        severe: [6, 10]      # 严重增厚
      fuse_conditions:
        - "value > 8"
        - "value < 1"
        - "unit == 'cm'"  # 黄韧带不可能用cm计量
      severity: "HIGH"
      clinical_note: "黄韧带>4mm为增厚，>6mm为严重增厚，常导致椎管狭窄"
    
    disc_height:
      name: "椎间隙高度"
      name_en: "Intervertebral Disc Height"
      field_patterns: ["disc height", "椎间隙", "interspace", "DH"]
      expected_units: ["mm"]
      normal_range:
        lumbar_l1l4: [8, 15]
        lumbar_l4l5: [9, 16]
        lumbar_l5s1: [8, 14]
      fuse_conditions:
        - "value > 20"
        - "value < 3"
        - "unit == 'cm' and value > 2"
      severity: "MEDIUM"
      clinical_note: "L4-5椎间隙通常最高，<5mm提示严重退变/塌陷"
    
    foraminal_height:
      name: "椎间孔高度"
      name_en: "Neuroforaminal Height"
      field_patterns: ["foraminal", "椎间孔", "neuroforaminal", "FH"]
      expected_units: ["mm"]
      normal_range:
        normal: [15, 25]
        stenosis_threshold: 15
      fuse_conditions:
        - "value < 10"
        - "value > 30"
      severity: "HIGH"
      clinical_note: "椎间孔<15mm提示椎间孔狭窄，是神经根受压的常见原因"
    
    pedicle_screw_diameter:
      name: "椎弓根螺钉直径"
      name_en: "Pedicle Screw Diameter"
      field_patterns: ["screw", "螺钉", "pedicle", "椎弓根"]
      expected_units: ["mm"]
      normal_range:
        lumbar: [5.5, 7.5]
        thoracic: [4.0, 6.5]
      fuse_conditions:
        - "value > 10"
        - "value < 4"
        - "unit == 'cm'"
      severity: "MEDIUM"
      clinical_note: "腰椎椎弓根螺钉通常为5.5-7.5mm，过大可能突破椎弓根"

  # ==================== 颈椎解剖参数 ====================
  cervical_anatomy:
    
    cervical_canal_diameter:
      name: "颈椎管径线"
      name_en: "Cervical Spinal Canal Diameter"
      field_patterns: ["cervical canal", "颈椎管", "C-spine canal"]
      expected_units: ["mm"]
      normal_range:
        normal: [14, 18]
        stenosis: [10, 14]
        severe_stenosis: [0, 10]
      fuse_conditions:
        - "value < 8"
        - "value > 25"
      severity: "CRITICAL"
      clinical_note: "颈椎管<10mm为狭窄，<8mm为严重狭窄，脊髓损伤风险高"
    
    Pavlov_ratio:
      name: "Pavlov比值"
      name_en: "Pavlov Ratio (Torg Ratio)"
      field_patterns: ["Pavlov", "pavlov ratio", "Torg", "canal/body"]
      expected_units: ["ratio", "none", ""]
      normal_range:
        normal: [1.0, 1.5]
        stenosis_threshold: 0.82
      fuse_conditions:
        - "value > 2.0"
        - "value < 0.5"
        - "value > 10"  # 可能是百分比误标
      severity: "HIGH"
      clinical_note: "Pavlov比值<0.82提示颈椎管狭窄，是颈椎后路手术的重要参考"

  # ==================== 胸椎解剖参数 ====================
  thoracic_anatomy:
    
    thoracic_canal_diameter:
      name: "胸椎管径线"
      name_en: "Thoracic Spinal Canal Diameter"
      field_patterns: ["thoracic canal", "胸椎管", "T-spine canal"]
      expected_units: ["mm"]
      normal_range:
        normal: [14, 18]
      fuse_conditions:
        - "value < 10"
        - "value > 25"
      severity: "HIGH"
      clinical_note: "胸椎管狭窄症状更严重，因为此处血供较差"
```

### 2. 手术技术指标验证

```yaml
spine_surgery:
  
  surgical_technical:
    
    operative_time:
      name: "手术时间"
      name_en: "Operative Time"
      field_patterns: ["operative time", "手术时间", "surgery time", "OT"]
      expected_units: ["min", "minutes", "h", "hours"]
      normal_range:
        microdiscectomy: [30, 120]      # 分钟
        laminectomy: [60, 180]
        fusion_1level: [90, 240]
        fusion_multilevel: [180, 480]
      fuse_conditions:
        - "unit in ['min', 'minutes'] and value > 600"  # >10小时
        - "unit in ['h', 'hours'] and value > 10"
        - "unit in ['min', 'minutes'] and value < 15"
      severity: "HIGH"
      clinical_note: "腰椎间盘显微切除通常30-90分钟，>4小时需核对手术范围"
    
    blood_loss:
      name: "术中出血量"
      name_en: "Estimated Blood Loss (EBL)"
      field_patterns: ["blood loss", "出血", "EBL", "estimated blood"]
      expected_units: ["mL", "ml"]
      normal_range:
        microdiscectomy: [20, 100]
        laminectomy: [50, 300]
        fusion: [100, 800]
      fuse_conditions:
        - "value > 2000"
        - "value < 0"
        - "unit == 'L' and value > 2"
      severity: "MEDIUM"
      clinical_note: "微创手术出血通常<100mL，开放融合手术可能500-1000mL"
    
    hospital_stay:
      name: "住院时间"
      name_en: "Length of Stay"
      field_patterns: ["hospital stay", "住院", "LOS", "length of stay"]
      expected_units: ["days", "d", "day"]
      normal_range:
        microdiscectomy_day_surgery: [0, 1]
        microdiscectomy_overnight: [1, 2]
        laminectomy: [1, 3]
        fusion: [2, 5]
      fuse_conditions:
        - "value > 30"
        - "value < 0"
      severity: "MEDIUM"
      clinical_note: "椎间盘手术通常日间手术或住院1-2天，>7天需核对并发症"

  # ==================== 手术效果指标 ====================
  surgical_outcomes:
    
    recurrence_rate:
      name: "复发率"
      name_en: "Recurrence Rate"
      field_patterns: ["recurrence", "复发", "reoperation", "再手术"]
      expected_units: ["%", "percent"]
      normal_range:
        discectomy_1year: [5, 15]
        discectomy_5year: [10, 25]
        conservative: [5, 20]
      fuse_conditions:
        - "value > 50"
        - "value < 0"
        - "value > 40 and follow_up == '1 year'"  # 1年复发>40%异常
      severity: "HIGH"
      clinical_note: "椎间盘切除术后1年复发率通常5-10%，5年约10-20%"
    
    complication_rate:
      name: "并发症发生率"
      name_en: "Complication Rate"
      field_patterns: ["complication", "并发症", "adverse event"]
      expected_units: ["%", "percent"]
      normal_range:
        microdiscectomy: [2, 8]
        laminectomy: [5, 15]
        fusion: [10, 25]
      fuse_conditions:
        - "value > 50"
        - "value < 0"
      severity: "MEDIUM"
      clinical_note: "微创手术并发症<5%，开放融合手术10-20%"
```

### 3. 影像学参数验证

```yaml
spine_surgery:
  
  imaging_parameters:
    
    herniation_size:
      name: "椎间盘突出大小"
      name_en: "Herniation Size"
      field_patterns: ["herniation size", "突出大小", "protrusion", "extrusion"]
      expected_units: ["mm"]
      normal_range:
        small: [3, 6]
        medium: [6, 9]
        large: [9, 15]
        massive: [15, 30]
      fuse_conditions:
        - "value > 30"
        - "value < 2"
      severity: "MEDIUM"
      clinical_note: "突出>10mm为大型突出，>15mm为巨大突出，可能影响手术方式选择"
    
    migration_distance:
      name: "椎间盘游离距离"
      name_en: "Migration Distance"
      field_patterns: ["migration", "游离", "sequestration", " migrated"]
      expected_units: ["mm"]
      normal_range:
        contained: [0, 0]
        subligamentous: [0, 10]
        sequestered: [10, 50]
      fuse_conditions:
        - "value > 50"
        - "value < 0"
      severity: "MEDIUM"
      clinical_note: "游离>10mm为游离型突出，手术难度增加"
    
    sagittal_balance:
      name: "矢状面平衡"
      name_en: "Sagittal Balance"
      field_patterns: ["sagittal balance", "SVA", "sagittal vertical axis"]
      expected_units: ["mm"]
      normal_range:
        normal: [0, 40]
        mild_positive: [40, 60]
        severe_positive: [60, 100]
      fuse_conditions:
        - "value > 150"
        - "value < -100"
      severity: "HIGH"
      clinical_note: "SVA>50mm提示矢状面失衡，可能需要矫形融合手术"
```

---

## 熔断触发示例

### 示例1: 椎管径线异常

```markdown
🚨 脊柱外科专科熔断器触发！

**检测到异常数值**: 椎管径线 8.5 mm
- 检测到字段: "spinal canal diameter"
- 正常范围: 15-27 mm (腰椎)
- 异常类型: 严重低于正常范围

**临床解读**:
- 椎管径线 8.5 mm 提示严重椎管狭窄
- 正常下限为 15 mm，< 10 mm 为绝对狭窄

**可能原因**:
1. 测量位置错误（可能测量了侧隐窝而非中央椎管）
2. 单位错误（可能是 cm 误标为 mm，即 8.5 cm = 85 mm）
3. 先天性椎管狭窄病例
4. 退变性椎管狭窄严重病例

**强制操作**:
1. 暂停自动提取
2. 请人工核对 CT/MRI 影像
3. 确认测量位置：中央椎管 vs 侧隐窝 vs 椎间孔
4. 确认单位标注正确

**临床建议**:
如果确认为 8.5 mm 中央椎管径线，该患者存在严重椎管狭窄，
手术指征明确，但需注意术中神经损伤风险较高。
```

### 示例2: 黄韧带厚度异常

```markdown
🚨 脊柱外科专科熔断器触发！

**检测到异常数值**: 黄韧带厚度 12 mm
- 检测到字段: "ligamentum flavum thickness"
- 正常范围: 2-4 mm
- 异常类型: 严重增厚

**临床解读**:
- 黄韧带厚度 12 mm 为极严重增厚（正常 < 4 mm）
- 这是导致椎管狭窄的主要因素

**可能原因**:
1. 长期退变性改变
2. 测量包含钙化部分
3. 单位错误（可能是 mm 误标为 cm，即 1.2 mm）
4. 真性严重黄韧带肥厚症

**强制操作**:
1. 核对 MRI T2 加权像测量
2. 确认是否包含钙化
3. 检查是否为节段性 vs 弥漫性增厚
```

---

## 集成到表格提取系统

```python
class SpineSurgeryCircuitBreaker:
    """
    脊柱外科专科熔断器 ⚠️ v2.5.1 新增
    
    集成到 table-extraction-interactive 模块
    """
    
    def __init__(self):
        self.rules = self.load_spine_surgery_rules()
    
    def check(self, field_name: str, value: float, unit: str) -> CircuitBreakerResult:
        """
        检查字段是否触发专科熔断器
        """
        # 匹配规则
        matched_rule = None
        for rule in self.rules:
            if any(pattern in field_name.lower() for pattern in rule.field_patterns):
                matched_rule = rule
                break
        
        if not matched_rule:
            return CircuitBreakerResult(passed=True)
        
        # 执行熔断检查
        for condition in matched_rule.fuse_conditions:
            if self.evaluate_condition(condition, value, unit):
                return CircuitBreakerResult(
                    passed=False,
                    severity=matched_rule.severity,
                    rule=matched_rule,
                    message=self.generate_alert(matched_rule, value, unit)
                )
        
        return CircuitBreakerResult(passed=True)
    
    def generate_alert(self, rule, value, unit) -> str:
        """生成熔断警告"""
        return f"""
🚨 脊柱外科专科熔断器触发！

**检测到异常数值**: {rule.name} {value} {unit}
- 正常范围: {rule.normal_range}
- 严重程度: {rule.severity}

**临床提示**: {rule.clinical_note}

**强制操作**: 请人工核对原始影像/文献
        """
```

---

## 扩展计划

### 已实现的专科黑匣子
- [x] 脊柱外科 (Spine Surgery) - LDH 专用

### 计划实现的专科黑匣子
- [ ] 关节外科 (Joint Surgery) - 膝关节置换专用
- [ ] 创伤骨科 (Trauma) - 骨折愈合专用
- [ ] 运动医学 (Sports Medicine) - 韧带重建专用
- [ ] 骨肿瘤 (Orthopedic Oncology) - 肿瘤切除专用

---

**最后更新**: 2026-03-13  
**版本**: v2.5.1 - 脊柱外科专科黑匣子首发  
**适用**: 腰椎间盘突出症 (LDH) 相关综述