---
name: table-logic-verify
description: PDF表格数据双重校验系统。通过逻辑规则验证表格数据的完整性和一致性，检测AI提取错误和数据幻觉。v2.3.0新增单位熔断器和医学符号语义保护。
version: "2.3.0"
---

# Table-Logic-Verify (TLV) 表格逻辑校验系统 v2.3.0

## 概述

TLV系统用于验证从PDF文献中提取的表格数据的**逻辑一致性**和**语义正确性**。医学文献中的表格（特别是三线表、复杂合并单元格）是AI幻觉的高发区。本系统通过多重逻辑校验确保数据可靠性。

**⚠️ v2.3.0 重大更新**：
- **单位熔断器（Unit Circuit Breaker）**：自动检测单位错误和数值量级异常
- **医学符号语义保护**：正确处理 ±、(CI)、*、† 等特殊符号

---

## 核心功能

1. **行列平衡性校验**：检查表格行/列数据的数学一致性
2. **样本量一致性校验**：验证亚组样本量之和是否等于总样本量
3. **百分比合理性校验**：检查百分比计算是否正确
4. **统计量逻辑校验**：验证P值、效应量等的合理性
5. **跨表格交叉验证**：验证不同表格间的数据一致性
6. **⚠️ v2.3.0 新增 - 单位熔断器**：检测单位错误和数值量级异常
7. **⚠️ v2.3.0 新增 - 医学符号保护**：正确处理医学特殊符号

---

## ⚠️ v2.3.0 新增：单位熔断器（Unit Circuit Breaker）

### 问题背景

医学表格中的单位错误是**致命性的**：
- 血糖 180 mg/dL 被误认为 180 mmol/L → 严重误诊
- 身高 175 cm 被提取为 175 m → 荒谬数据
- 剂量 5 mg 被当作 5 μg → 1000倍误差

### 熔断器设计原则

```yaml
熔断器工作流:
  1.领域识别: 根据表格标题/上下文识别医学领域
  2.单位检测: 提取字段名，匹配标准单位库
  3.范围检查: 验证数值是否在正常生理/临床范围内
  4.量级检查: 检测异常大或异常小的数值
  5.熔断决策:
     - 通过: 继续正常处理
     - 警告: 标记待人工复核
     - 熔断: 强制暂停，要求人工核对PDF原件
```

### 标准单位库（按医学领域）

```python
UNIT_CIRCUIT_BREAKER_DB = {
    "内分泌/糖尿病": {
        "血糖": {
            "units": ["mg/dL", "mmol/L"],
            "normal_range": {"mg/dL": [70, 200], "mmol/L": [3.9, 11.1]},
            "conversion": "mg/dL = mmol/L * 18",
            "熔断条件": "value > 1000 or value < 10"  # 可能是单位错误
        },
        "HbA1c": {
            "units": ["%", "mmol/mol"],
            "normal_range": {"%": [4, 15], "mmol/mol": [20, 140]},
            "熔断条件": "value > 20"  # HbA1c不可能>20%
        },
        "胰岛素": {
            "units": ["μU/mL", "mU/L", "pmol/L"],
            "normal_range": {"μU/mL": [2, 25]},
            "熔断条件": "value > 1000"  # 可能是单位错误
        }
    },
    
    "心血管": {
        "血压收缩压": {
            "units": ["mmHg"],
            "normal_range": [90, 200],
            "熔断条件": "value > 300 or value < 50"
        },
        "血压舒张压": {
            "units": ["mmHg"],
            "normal_range": [50, 130],
            "熔断_condition": "value > 200 or value < 30"
        },
        "心率": {
            "units": ["bpm", "次/分"],
            "normal_range": [40, 200],
            "熔断_condition": "value > 300 or value < 20"
        },
        "胆固醇": {
            "units": ["mg/dL", "mmol/L"],
            "normal_range": {"mg/dL": [100, 400], "mmol/L": [2.6, 10.4]},
            "熔断_condition": "value > 1000"  # 可能是mg/dL当作mmol/L
        }
    },
    
    "骨科/风湿": {
        "WOMAC评分": {
            "units": ["分", "points"],
            "normal_range": [0, 96],
            "熔断_condition": "value > 100"
        },
        "VAS评分": {
            "units": ["mm", "cm", "分"],
            "normal_range": [0, 100],  # 0-100 mm
            "熔断_condition": "value > 100"
        },
        "关节活动度": {
            "units": ["°", "度"],
            "normal_range": [0, 180],
            "熔断_condition": "value > 360"
        },
        "骨密度T值": {
            "units": ["SD", "标准差"],
            "normal_range": [-5, 5],
            "熔断_condition": "value < -10 or value > 10"
        }
    },
    
    "肿瘤": {
        "肿瘤标志物": {
            "CEA": {"units": ["ng/mL"], "normal_range": [0, 10], "熔断": "value > 10000"},
            "CA125": {"units": ["U/mL"], "normal_range": [0, 35], "熔断": "value > 10000"},
            "PSA": {"units": ["ng/mL"], "normal_range": [0, 4], "熔断": "value > 1000"}
        },
        "肿瘤大小": {
            "units": ["mm", "cm"],
            "normal_range": {"mm": [1, 200], "cm": [0.1, 20]},
            "熔断_condition": "value > 500"  # 可能是mm当作cm
        }
    },
    
    "通用人体测量": {
        "身高": {
            "units": ["cm", "m"],
            "normal_range": {"cm": [50, 250], "m": [0.5, 2.5]},
            "熔断_condition": "value > 300 and unit == 'cm'"  # 可能是m当作cm
        },
        "体重": {
            "units": ["kg", "g", "lb"],
            "normal_range": {"kg": [2, 300]},
            "熔断_condition": "value > 500"  # 可能是g当作kg
        },
        "BMI": {
            "units": ["kg/m²"],
            "normal_range": [10, 60],
            "熔断_condition": "value > 100 or value < 5"
        },
        "年龄": {
            "units": ["岁", "years"],
            "normal_range": [0, 120],
            "熔断_condition": "value > 150"
        }
    }
}
```

### 熔断触发示例

```
🚨 单位熔断器触发！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【熔断类型】: 数值量级异常
【字段名称】: 血糖
【提取数值】: 180
【提取单位】: mmol/L
【正常范围】: 3.9 - 11.1 mmol/L

【分析】:
• 该数值远超正常范围（约16倍）
• 若将 180 mg/dL 误认为 mmol/L，则真实值为 10 mmol/L（正常）
• 若确实为 180 mmol/L，则患者已昏迷/死亡，不符合研究纳入标准

【熔断动作】:
❌ 暂停自动提取
📄 请人工核对 PDF 原件
📝 确认后手动输入正确数值和单位

【历史相似错误】:
• 文献A：血糖 200 mmol/L → 实际为 200 mg/dL (11.1 mmol/L)
• 文献B：身高 1.75 m → 提取为 175 m
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 熔断器实现代码

```python
class UnitCircuitBreaker:
    """单位熔断器 - v2.3.0 核心组件"""
    
    def __init__(self):
        self.unit_db = UNIT_CIRCUIT_BREAKER_DB
        self.field_patterns = self._compile_patterns()
    
    def check(self, field_name: str, value: float, unit: str, context: dict) -> dict:
        """
        执行单位熔断检查
        
        Returns:
            {
                'status': 'PASS' | 'WARNING' | 'FUSE',
                'message': str,
                'suggestion': str,
                'confidence': float
            }
        """
        # 1. 识别领域和字段类型
        field_type = self._identify_field_type(field_name, context)
        
        if not field_type:
            return {'status': 'PASS', 'message': '未知字段，跳过熔断检查'}
        
        # 2. 获取标准单位和范围
        standard = self._get_standard(field_type)
        
        # 3. 单位标准化
        normalized_unit = self._normalize_unit(unit, standard['units'])
        
        if not normalized_unit:
            return {
                'status': 'WARNING',
                'message': f'单位"{unit}"不在标准单位列表中',
                'suggestion': f'期望单位: {standard["units"]}'
            }
        
        # 4. 范围检查
        normal_range = standard['normal_range'].get(normalized_unit, standard['normal_range'])
        if value < normal_range[0] or value > normal_range[1]:
            # 触发熔断条件检查
            if self._check_fuse_condition(value, standard.get('fuse_conditions', [])):
                return {
                    'status': 'FUSE',
                    'message': f'数值 {value} {normalized_unit} 触发熔断条件',
                    'suggestion': f'正常范围为 {normal_range}，请核对PDF原件',
                    'likely_error': self._infer_likely_error(value, normalized_unit, standard)
                }
            else:
                return {
                    'status': 'WARNING',
                    'message': f'数值 {value} 超出正常范围 {normal_range}',
                    'suggestion': '请确认该异常值是否合理（如：严重疾病患者）'
                }
        
        return {'status': 'PASS', 'message': '通过熔断检查'}
    
    def _infer_likely_error(self, value: float, unit: str, standard: dict) -> str:
        """推断可能的错误类型"""
        # 检查是否是单位换算错误
        if 'conversion' in standard:
            # 尝试反向换算
            for other_unit, factor in standard['conversion_factors'].items():
                converted = value * factor
                if standard['normal_range'].get(other_unit, [0, 999])[0] <= converted <= \
                   standard['normal_range'].get(other_unit, [0, 999])[1]:
                    return f'可能是 {value} {other_unit} 被误标为 {unit}（真实值应为 {converted:.1f} {unit}）'
        
        # 检查数量级错误
        if value > 100 and unit in ['cm', 'm']:
            return f'可能是 {value} cm 被误标为 {value} m'
        
        return '未知错误类型，请人工核对'
```

---

## ⚠️ v2.3.0 新增：医学符号语义保护

### 问题背景

AI 在提取医学表格时，经常**错误解析特殊符号**：
- `85.2±3.1` → 错误拆分为两个数字 `85.2` 和 `3.1`
- `12.5 (11.0-14.2)` → 丢失括号内的置信区间
- `0.001*` → 丢失显著性标记和脚注
- `†` → 忽略 dagger 符号，不看脚注

### 符号解析规则库

```python
MEDICAL_SYMBOL_RULES = {
    "均值±标准差": {
        "pattern": r"(\d+\.?\d*)\s*[±\+\-]\s*(\d+\.?\d*)",
        "extract": {
            "mean": "group(1)",
            "sd": "group(2)",
            "full_expression": "mean ± sd"
        },
        "semantics": {
            "description": "算术均值 ± 标准差",
            "calculation": "表示数据的离散程度",
            "note": "请勿拆分为两个独立数字"
        },
        "validation": {
            "sd_should_be_positive": True,
            "sd_should_be_less_than_mean": "通常成立（但非绝对）",
            "cv_reasonable": "CV = sd/mean 应在 0-1 范围内（通常）"
        }
    },
    
    "均值(95%CI)": {
        "pattern": r"(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)",
        "extract": {
            "mean": "group(1)",
            "ci_lower": "group(2)",
            "ci_upper": "group(3)",
            "full_expression": "mean (CI_lower-CI_upper)"
        },
        "semantics": {
            "description": "点估计值 (95%置信区间)",
            "interpretation": "有95%把握真实值在此区间内",
            "note": "必须同时提取三个数值"
        },
        "validation": {
            "ci_lower_should_be_less_than_upper": True,
            "mean_should_be_inside_ci": "对于正态分布数据成立",
            "ci_width_reasonable": "CI宽度不应过大（相对点估计）"
        }
    },
    
    "P值+显著性标记": {
        "pattern": r"(<?)\s*(0?\.\d+|[<>]0\.\d+|NS)\s*([*†‡§¶#]**)",
        "extract": {
            "p_value": "group(2)",
            "inequality": "group(1)",  # < or empty
            "significance_marks": "group(3)"
        },
        "semantics": {
            "description": "P值与显著性标记",
            "interpretation": "* 通常表示 P<0.05, ** 表示 P<0.01",
            "note": "必须提取脚注解释具体含义"
        },
        "validation": {
            "p_value_should_be_0_to_1": True,
            "significance_mark_consistent": "* 应对应 P<0.05"
        },
        "mandatory_action": "提取表格脚注，解释 * 和 ** 的具体含义"
    },
    
    "范围值": {
        "pattern": r"(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)",
        "extract": {
            "min": "group(1)",
            "max": "group(2)"
        },
        "semantics": {
            "description": "最小值-最大值（范围）",
            "interpretation": "观察到的数据范围",
            "note": "与置信区间不同，不代表统计不确定性"
        },
        "validation": {
            "min_should_be_less_than_max": True,
            "not_confused_with_ci": "上下文判断是范围还是CI"
        }
    },
    
    "脚注标记": {
        "pattern": r"([†‡§¶#*])",
        "extract": {
            "mark": "group(1)"
        },
        "semantics": {
            "description": "脚注引用标记",
            "interpretation": "需要查看表格下方的脚注说明",
            "note": "绝不能忽略！"
        },
        "mandatory_action": "必须提取并关联对应的脚注文本"
    },
    
    "不等式表达": {
        "pattern": r"([<>≤≥])\s*(\d+\.?\d*)",
        "extract": {
            "operator": "group(1)",
            "value": "group(2)"
        },
        "examples": {
            "<0.001": "P值小于0.001",
            ">50": "大于50",
            "≤18": "小于等于18"
        }
    }
}
```

### 符号提取示例

```python
# 示例1: 均值±标准差
raw_text = "85.2±3.1"
extracted = {
    "type": "均值±标准差",
    "mean": 85.2,
    "sd": 3.1,
    "full": "85.2±3.1",
    "validation": {
        "sd_positive": True,
        "cv": 0.036  # 合理范围内
    }
}

# 示例2: 置信区间
raw_text = "12.5 (11.0-14.2)"
extracted = {
    "type": "均值(95%CI)",
    "mean": 12.5,
    "ci_lower": 11.0,
    "ci_upper": 14.2,
    "ci_includes_mean": True,  # 12.5 在 [11.0, 14.2] 内
    "note": "这是正态分布近似，点估计应在CI内"
}

# 示例3: P值+脚注
raw_text = "0.001*"
extracted = {
    "type": "P值+显著性标记",
    "p_value": 0.001,
    "significance": "*",
    "footnote_required": True,
    "footnote_text": "* P<0.05 vs baseline; ** P<0.01 vs baseline",
    "interpretation": "与基线相比，P<0.05，具有统计学显著性"
}

# 示例4: 带脚注的数值
raw_text = "45.2†"
extracted = {
    "value": 45.2,
    "footnote_mark": "†",
    "footnote_text": "† 基于ITT分析",
    "note": "该数据基于意向性治疗分析，非PP分析"
}
```

### 错误处理示例

```
❌ 错误提取：
原始表格：75.2±5.3
AI提取：mean=75.2, sd=5.3  ✓
但后续处理错误拆分为两个独立数值

✅ 正确提取（v2.3.0）：
原始表格：75.2±5.3
AI提取：{
    "type": "mean±sd",
    "mean": 75.2,
    "sd": 5.3,
    "protect": True,  # 标记为保护单元，禁止拆分
    "forbidden_operations": ["拆分", "单独使用sd"]
}

❌ 错误提取：
原始表格：0.001*
AI提取：p_value=0.001  ✓
但丢失了 * 标记，不知道是与什么比较

✅ 正确提取（v2.3.0）：
原始表格：0.001*
AI提取：{
    "p_value": 0.001,
    "significance_mark": "*",
    "footnote": "* P<0.05 vs placebo",
    "comparison_baseline": "placebo",
    "mandatory_note": "与安慰剂相比具有统计学显著性"
}
```

---

## 原有校验规则库（v1.0保留）

### 规则1: 样本量加和校验

```python
def check_sample_size_consistency(table_data):
    """验证亚组样本量加和"""
    errors = []
    
    # 检查行加和
    for row in table_data['rows']:
        subgroups = row['subgroups']
        total = row['total']
        if sum(subgroups) != total:
            errors.append({
                'type': 'row_sum_mismatch',
                'row': row['name'],
                'expected': total,
                'calculated': sum(subgroups),
                'severity': 'high'
            })
    
    return errors
```

### 规则2-6: 百分比、统计量、置信区间、缺失数据、基线可比性

[详见 v1.0 文档，此处省略]

---

## v2.3.0 完整执行流程

```python
class EnhancedTableVerifier:
    """增强版表格校验器 v2.3.0"""
    
    def verify(self, table_data: Dict, context: Dict) -> Dict:
        """
        执行完整校验流程（含单位熔断器和符号保护）
        """
        all_issues = []
        
        # Step 1: 医学符号语义解析
        parsed_cells = self._parse_medical_symbols(table_data)
        
        # Step 2: 单位熔断器检查（v2.3.0 新增）
        unit_issues = self._check_unit_circuit_breaker(parsed_cells, context)
        all_issues.extend(unit_issues)
        
        # 如果有熔断级别问题，立即停止
        fuse_issues = [i for i in unit_issues if i['severity'] == 'fuse']
        if fuse_issues:
            return {
                'status': 'FUSED',
                'message': '单位熔断器触发，必须人工核对',
                'fuse_issues': fuse_issues,
                'action_required': '请人工核对PDF原件，确认数值和单位'
            }
        
        # Step 3: 传统逻辑校验
        all_issues.extend(check_sample_size_consistency(table_data))
        all_issues.extend(check_percentage_validity(table_data))
        all_issues.extend(check_statistic_pvalue_consistency(table_data))
        all_issues.extend(check_confidence_interval(table_data))
        
        # Step 4: 生成报告
        return self._generate_enhanced_report(all_issues)
```

---

## 校验报告示例（v2.3.0）

```markdown
## 表格校验报告 v2.3.0

### 表格信息
- **来源文献**: Smith et al., 2023, Ann Rheum Dis
- **表号**: Table 2
- **标题**: Efficacy Outcomes at 6 Months

### 校验结果: 🚨 需要人工处理（熔断器触发）

#### 🔴 熔断器触发 (1项) - 必须人工核对

| 熔断类型 | 字段 | 提取值 | 问题描述 | 建议 |
|----------|------|--------|----------|------|
| 单位错误 | 血糖 | 180 mmol/L | 远超正常范围(3.9-11.1) | 可能是mg/dL误标为mmol/L |

**⚠️ 强制操作**: 由于熔断器触发，自动提取已暂停。请查看PDF原件第3页Table 2，
确认"血糖"一行的单位究竟是 mg/dL 还是 mmol/L。

---

#### 🟡 符号保护警告 (2项)

| 位置 | 原始文本 | 解析结果 | 警告 |
|------|----------|----------|------|
| 实验组有效率 | 75.0%* | mean=75.0, mark=* | 已提取脚注：* P<0.05 vs baseline |
| 对照组n | 98† | n=98, mark=† | 已提取脚注：† ITT analysis |

---

#### 🟢 逻辑校验通过

- ✅ 样本量加和一致
- ✅ 百分比计算正确
- ✅ 统计量-P值一致
- ✅ 置信区间逻辑正确

### 下一步操作
- [ ] 核对血糖单位（优先级：紧急）
- [ ] 确认脚注提取准确性
- [ ] 修正后重新运行校验
```

---

## 附录：单位熔断器配置指南

### 如何添加新的熔断规则

```python
# 在 UNIT_CIRCUIT_BREAKER_DB 中添加新的领域/字段

"新的医学领域": {
    "字段名称": {
        "units": ["标准单位1", "标准单位2"],
        "normal_range": {
            "标准单位1": [最小值, 最大值],
            "标准单位2": [最小值, 最大值]
        },
        "conversion_factors": {  # 单位换算系数
            "标准单位2": 0.1  # 单位2 = 单位1 * 0.1
        },
        "fuse_conditions": [
            "value > 最大值 * 10",  # 数量级异常
            "value < 最小值 / 10"
        ],
        "notes": "该字段的特殊说明"
    }
}
```

---

*版本: 2.3.0*  
*更新日期: 2026-03-12*  
*v2.3.0 更新：新增单位熔断器和医学符号语义保护*