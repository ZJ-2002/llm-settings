---
name: dual-track-table-extraction
description: 人机协作双轨制表格提取系统。AI预提取+置信度评估+人工复核+自动校验的完整工作流。
version: "1.0.0"
---

# 双轨制表格提取系统 (Dual-Track Table Extraction)

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         双轨制表格提取系统                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  输入: PDF文献                                                            │
│     │                                                                    │
│     ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 轨道A: AI预提取 (自动化)                                         │    │
│  │                                                                  │    │
│  │  1. 表格检测与定位                                                │    │
│  │  2. 结构解析（行列识别）                                           │    │
│  │  3. 内容提取（文本+数值）                                          │    │
│  │  4. 置信度评估 ← 关键步骤                                          │    │
│  │  5. 标记低置信度单元格                                             │    │
│  │                                                                  │    │
│  │  输出: extraction-v1.json (含置信度标记)                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     │                                                                    │
│     ▼                                                                    │
│  置信度分流                                                              │
│     │                                                                    │
│     ├── A级 (≥90%) ──────┐                                              │
│     │                     │                                              │
│     ├── B级 (70-90%) ────┼──► 轨道C: 自动校验                           │
│     │                     │                                              │
│     └── C级 (<70%) ──────┘                                              │
│                           │                                              │
│                           ▼                                              │
│              ┌─────────────────────────┐                                │
│              │ 轨道C: 自动校验          │                                │
│              │                          │                                │
│              │  Table-Logic-Verify      │                                │
│              │  ├── 样本量一致性        │                                │
│              │  ├── 百分比合理性        │                                │
│              │  ├── 统计量逻辑          │                                │
│              │  └── 跨表一致性          │                                │
│              │                          │                                │
│              │  输出: verification-report.json                         │
│              └─────────────────────────┘                                │
│                           │                                              │
│              ┌────────────┴────────────┐                                │
│              │                         │                                │
│              ▼                         ▼                                │
│           通过                        失败                              │
│              │                         │                                │
│              ▼                         ▼                                │
│         直接入库                 轨道B: 人工复核                         │
│                                       │                                │
│                                       ▼                                │
│                          ┌─────────────────────────┐                    │
│                          │ 轨道B: 人工复核          │                    │
│                          │                          │                    │
│                          │  1. 交互式校验界面        │                    │
│                          │  2. 高亮差异单元格        │                    │
│                          │  3. 一键修正             │                    │
│                          │  4. 重新运行校验         │                    │
│                          │                          │                    │
│                          │  输出: extraction-v2.json │                    │
│                          └─────────────────────────┘                    │
│                                       │                                │
│                                       ▼                                │
│                                   最终入库                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 轨道A: AI预提取

### 步骤1: 表格检测与定位

```python
# table_detector.py
import fitz  # PyMuPDF
from dataclasses import dataclass
from typing import List, Tuple
import json

@dataclass
class TableRegion:
    """表格区域定义"""
    page_num: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    table_id: str
    complexity_score: float  # 复杂度评分 0-1

@dataclass
class ExtractedCell:
    """提取的单元格"""
    row: int
    col: int
    text: str
    bbox: Tuple[float, float, float, float]
    is_header: bool = False
    is_merged: bool = False
    row_span: int = 1
    col_span: int = 1

class TableDetector:
    """表格检测器"""
    
    def detect_tables(self, pdf_path: str) -> List[TableRegion]:
        """检测PDF中的所有表格区域"""
        tables = []
        doc = fitz.open(pdf_path)
        
        for page_num, page in enumerate(doc):
            # 方法1: 基于图形元素的表格检测
            drawings = page.get_drawings()
            tables_from_lines = self._detect_from_lines(drawings)
            
            # 方法2: 基于文本布局的表格检测
            text_blocks = page.get_text("blocks")
            tables_from_layout = self._detect_from_layout(text_blocks)
            
            # 合并检测结果
            merged_tables = self._merge_detections(
                tables_from_lines + tables_from_layout
            )
            
            for i, table_bbox in enumerate(merged_tables):
                complexity = self._assess_complexity(page, table_bbox)
                tables.append(TableRegion(
                    page_num=page_num,
                    bbox=table_bbox,
                    table_id=f"T{page_num}_{i}",
                    complexity_score=complexity
                ))
        
        return tables
    
    def _assess_complexity(self, page, bbox) -> float:
        """评估表格复杂度 (0-1)"""
        clip = fitz.Rect(bbox)
        text = page.get_text("text", clip=clip)
        
        complexity_factors = {
            'row_count': text.count('\n') / 50,  # 归一化到50行
            'has_merged_cells': '│' in text or '├' in text,
            'multi_line_headers': text.count('\n\n') > 2,
            'has_footnotes': '†' in text or '*' in text,
            'nested_structure': text.count('  ') > 10
        }
        
        # 加权计算复杂度
        weights = {
            'row_count': 0.3,
            'has_merged_cells': 0.25,
            'multi_line_headers': 0.15,
            'has_footnotes': 0.15,
            'nested_structure': 0.15
        }
        
        score = sum(
            complexity_factors[k] * weights[k] 
            for k in complexity_factors
        )
        return min(score, 1.0)
```

### 步骤2: 结构解析与内容提取

```python
# table_extractor.py
import re
from typing import Dict, List, Any
import pandas as pd

class TableExtractor:
    """表格提取器"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def extract_table(self, pdf_path: str, table_region: TableRegion) -> Dict[str, Any]:
        """提取单个表格"""
        
        # 1. 裁剪表格区域图像
        doc = fitz.open(pdf_path)
        page = doc[table_region.page_num]
        pix = page.get_pixmap(clip=fitz.Rect(table_region.bbox))
        
        # 2. 使用多模态LLM提取
        extraction_result = self._llm_extract(pix, table_region.complexity_score)
        
        # 3. 结构化输出
        return {
            'table_id': table_region.table_id,
            'page_num': table_region.page_num,
            'bbox': table_region.bbox,
            'complexity_score': table_region.complexity_score,
            'extraction': extraction_result,
            'raw_image': pix.tobytes()  # 用于人工复核时显示
        }
    
    def _llm_extract(self, image, complexity: float) -> Dict[str, Any]:
        """使用LLM提取表格内容"""
        
        prompt = f"""
        请仔细分析这个医学文献中的表格图像，提取结构化数据。
        
        表格复杂度评估: {complexity:.2f} (0-1)
        
        请按以下JSON格式输出：
        ```json
        {{
          "title": "表格标题",
          "headers": [
            {{"name": "列名", "sub_headers": []}}
          ],
          "rows": [
            {{
              "cells": [
                {{
                  "value": "单元格内容",
                  "type": "text|number|percentage|p_value|ci",
                  "confidence": 0.95,
                  "confidence_reason": "清晰可读|部分模糊|格式复杂|疑似错误"
                }}
              ]
            }}
          ],
          "footnotes": ["脚注1", "脚注2"],
          "extraction_notes": "提取过程中的注意事项"
        }}
        ```
        
        特别注意：
        1. 每个单元格的confidence字段必须填写 (0-1)
        2. 数值类型要特别小心，确保小数点位置正确
        3. 百分比和原始数值都要提取
        4. 合并单元格要正确识别并标记
        5. 脚注符号要与对应单元格关联
        """
        
        # 调用多模态LLM
        response = self.llm.vision_completion(
            prompt=prompt,
            image=image
        )
        
        return self._parse_llm_response(response)
```

### 步骤3: 置信度评估算法

```python
# confidence_assessor.py
from enum import Enum
from typing import List, Dict
import re

class ConfidenceLevel(Enum):
    HIGH = "A"      # ≥90%
    MEDIUM = "B"    # 70-90%
    LOW = "C"       # <70%

class ConfidenceAssessor:
    """置信度评估器"""
    
    def assess_cell_confidence(self, cell: Dict) -> Dict:
        """评估单个单元格的置信度"""
        
        text = cell.get('value', '')
        cell_type = cell.get('type', 'text')
        
        factors = []
        
        # 因素1: OCR质量指标
        ocr_score = self._assess_ocr_quality(text)
        factors.append(('ocr_quality', ocr_score, 0.3))
        
        # 因素2: 数值合理性
        if cell_type in ['number', 'percentage', 'p_value']:
            numeric_score = self._assess_numeric_reasonableness(text, cell_type)
            factors.append(('numeric_reasonableness', numeric_score, 0.25))
        
        # 因素3: 上下文一致性
        context_score = self._assess_context_consistency(cell)
        factors.append(('context_consistency', context_score, 0.2))
        
        # 因素4: 格式规范性
        format_score = self._assess_format_compliance(text, cell_type)
        factors.append(('format_compliance', format_score, 0.25))
        
        # 计算加权总分
        total_confidence = sum(score * weight for _, score, weight in factors)
        
        # 确定置信度等级
        if total_confidence >= 0.9:
            level = ConfidenceLevel.HIGH
        elif total_confidence >= 0.7:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        
        return {
            'confidence_score': round(total_confidence, 3),
            'confidence_level': level.value,
            'factors': {name: score for name, score, _ in factors},
            'needs_review': level != ConfidenceLevel.HIGH,
            'review_reason': self._generate_review_reason(factors, level)
        }
    
    def _assess_ocr_quality(self, text: str) -> float:
        """评估OCR质量"""
        score = 1.0
        
        # 惩罚可疑字符
        suspicious_chars = len(re.findall(r'[^\w\s\d\.\-\+\%\(\)\,\;\:\/\<\>\=\±\℃\°]', text))
        score -= suspicious_chars * 0.1
        
        # 惩罚乱码模式
        if re.search(r'[a-z][A-Z][a-z]', text):  # 大小写混乱
            score -= 0.2
        
        # 惩罚过长数字
        long_numbers = re.findall(r'\d{5,}', text)
        if long_numbers:
            score -= 0.15
        
        return max(score, 0.0)
    
    def _assess_numeric_reasonableness(self, text: str, num_type: str) -> float:
        """评估数值合理性"""
        score = 1.0
        
        try:
            if num_type == 'percentage':
                # 百分比应在0-100之间
                val = float(text.replace('%', ''))
                if val < 0 or val > 100:
                    score -= 0.5
                elif val > 1000:  # 明显错误
                    score -= 0.8
                    
            elif num_type == 'p_value':
                # P值应在0-1之间
                val = float(text.replace('<', '').replace('>', ''))
                if val < 0 or val > 1:
                    score -= 0.6
                    
            elif num_type == 'number':
                # 检查数量级合理性
                val = float(text)
                if abs(val) > 1e9:  # 太大
                    score -= 0.3
                elif 'sample' in text.lower() and val > 100000:  # 样本量过大
                    score -= 0.4
                    
        except ValueError:
            score -= 0.5  # 解析失败
        
        return max(score, 0.0)
    
    def _assess_format_compliance(self, text: str, cell_type: str) -> float:
        """评估格式规范性"""
        score = 1.0
        
        if cell_type == 'percentage':
            if '%' not in text and not text.replace('.', '').isdigit():
                score -= 0.3
                
        elif cell_type == 'p_value':
            if not re.match(r'[<>=]?\s*0\.\d+', text):
                score -= 0.2
                
        elif cell_type == 'ci':
            if not re.search(r'\d+\.?\d*\s*[-–—]\s*\d+\.?\d*', text):
                score -= 0.3
        
        return max(score, 0.0)
    
    def _generate_review_reason(self, factors: List, level: ConfidenceLevel) -> str:
        """生成复核原因"""
        if level == ConfidenceLevel.HIGH:
            return None
        
        low_factors = [name for name, score, _ in factors if score < 0.7]
        
        reason_map = {
            'ocr_quality': 'OCR识别质量低',
            'numeric_reasonableness': '数值可能不合理',
            'context_consistency': '上下文不一致',
            'format_compliance': '格式不规范'
        }
        
        reasons = [reason_map.get(f, f) for f in low_factors]
        return '；'.join(reasons) if reasons else '置信度不足'
```

---

## 轨道B: 人工复核

### 交互式校验界面规范

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Table Verification Interface",
  "type": "object",
  "properties": {
    "table_metadata": {
      "type": "object",
      "properties": {
        "table_id": {"type": "string"},
        "paper_info": {
          "type": "object",
          "properties": {
            "doi": {"type": "string"},
            "title": {"type": "string"},
            "first_author": {"type": "string"},
            "year": {"type": "integer"}
          }
        },
        "page_num": {"type": "integer"},
        "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "verification_grid": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "row_idx": {"type": "integer"},
          "col_idx": {"type": "integer"},
          "extracted_value": {"type": "string"},
          "confidence_score": {"type": "number"},
          "confidence_level": {"enum": ["A", "B", "C"]},
          "cell_type": {"enum": ["text", "number", "percentage", "p_value", "ci"]},
          "image_snippet": {"type": "string", "description": "base64 encoded cell image"},
          "verification_status": {
            "enum": ["pending", "verified", "corrected", "unclear"]
          },
          "corrected_value": {"type": "string"},
          "reviewer_notes": {"type": "string"}
        },
        "required": ["row_idx", "col_idx", "extracted_value", "confidence_level"]
      }
    },
    "verification_summary": {
      "type": "object",
      "properties": {
        "total_cells": {"type": "integer"},
        "high_confidence_cells": {"type": "integer"},
        "needs_review_cells": {"type": "integer"},
        "verified_cells": {"type": "integer"},
        "corrected_cells": {"type": "integer"},
        "verification_complete": {"type": "boolean"}
      }
    }
  }
}
```

### 复核工作流

```markdown
## 人工复核操作指南

### 复核界面布局
```
┌─────────────────────────────────────────────────────────────────────┐
│ 表格复核 - T1_2 (Jordan et al., 2024)                    [保存] [提交]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ 左侧: 原始PDF图像                    右侧: 提取数据表格               │
│ ┌─────────────────────────┐        ┌─────────────────────────┐      │
│ │  [表格区域放大显示]      │        │  ┌───┬─────┬─────┬────┐ │      │
│ │                         │        │  │   │ 男   │ 女   │ P  │ │      │
│ │  当前高亮单元格          │        │  ├───┼─────┼─────┼────┤ │      │
│ │  ┌─────┐               │        │  │实验│ 48  │ 52  │0.82│ │      │
│ │  │ 48  │ ← 红框标记     │        │  │组  │🔴   │ 🟡  │ 🟢 │ │      │
│ │  └─────┘               │        │  ├───┼─────┼─────┼────┤ │      │
│ │                         │        │  │对照│ 52  │ 48  │0.74│ │      │
│ │                         │        │  │组  │ 🟡  │ 🟡  │ 🟢 │ │      │
│ └─────────────────────────┘        │  └───┴─────┴─────┴────┘ │      │
│                                      └─────────────────────────┘      │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│ 底部: 操作面板                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ 当前单元格: 行2列2 - "48" (置信度: 0.65 - C级)                    ││
│ │ 置信度原因: OCR识别质量低；数值可能不合理                        ││
│ │                                                                  ││
│ │ [✓ 确认正确]  [✏ 修正为: ____]  [? 标记为不清晰]  [→ 下一个]    ││
│ └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 颜色编码
- 🟢 绿色 (A级, ≥90%): 可信，快速确认即可
- 🟡 黄色 (B级, 70-90%): 需仔细核对
- 🔴 红色 (C级, <70%): 必须仔细核对，可能错误

### 操作选项
1. **确认正确**: 保留原值，标记为verified
2. **修正**: 输入正确值，标记为corrected
3. **标记为不清晰**: 原文确实无法辨认，标记为unclear
4. **跳过**: 暂时不处理，保持pending状态

### 复核完成标准
- 所有C级单元格必须处理（确认/修正/标记）
- 至少90%的B级单元格已处理
- 整体表格通过Table-Logic-Verify校验

### 快捷键
- `Space`: 确认正确
- `Enter`: 确认并下一个
- `Esc`: 标记为不清晰
- `Tab`: 切换到修正输入框
```

---

## 轨道C: 自动校验

```python
# verification_pipeline.py
from typing import Dict, List, Tuple
import json

class VerificationPipeline:
    """校验流水线"""
    
    def __init__(self):
        self.rules = [
            SampleSizeConsistencyRule(),
            PercentageValidityRule(),
            StatisticPValueConsistencyRule(),
            ConfidenceIntervalRule(),
            CrossTableConsistencyRule()
        ]
    
    def verify(self, extraction: Dict) -> Dict:
        """运行完整校验"""
        all_issues = []
        
        for rule in self.rules:
            issues = rule.check(extraction)
            all_issues.extend(issues)
        
        # 分类问题
        critical_issues = [i for i in all_issues if i['severity'] == 'critical']
        warning_issues = [i for i in all_issues if i['severity'] == 'warning']
        info_issues = [i for i in all_issues if i['severity'] == 'info']
        
        # 判定结果
        if critical_issues:
            status = 'failed'
            action = 'needs_human_review'
        elif warning_issues:
            status = 'passed_with_warnings'
            action = 'optional_review'
        else:
            status = 'passed'
            action = 'accept'
        
        return {
            'status': status,
            'action': action,
            'summary': {
                'total_checks': len(self.rules),
                'critical_issues': len(critical_issues),
                'warning_issues': len(warning_issues),
                'info_issues': len(info_issues)
            },
            'issues': all_issues,
            'timestamp': datetime.now().isoformat()
        }
```

---

## 完整工作流集成

```yaml
# dual-track-config.yaml

dual_track_system:
  version: "1.0.0"
  
  # 轨道A配置
  track_a:
    enabled: true
    llm_model: "gpt-4o-vision"
    
    confidence_thresholds:
      high: 0.90    # A级
      medium: 0.70  # B级
      low: 0.00     # C级
    
    auto_accept:
      enabled: true
      min_confidence: 0.90
      max_cells: 100  # 简单表格自动通过
  
  # 轨道B配置
  track_b:
    enabled: true
    
    review_priorities:
      critical:  # C级必须复核
        auto_assign: true
        due_hours: 24
      warning:   # B级建议复核
        auto_assign: false
        due_hours: 72
    
    ui_config:
      show_original_image: true
      show_confidence_reason: true
      enable_shortcuts: true
  
  # 轨道C配置
  track_c:
    enabled: true
    
    validation_rules:
      - name: sample_size_consistency
        enabled: true
        severity: critical
      
      - name: percentage_validity
        enabled: true
        severity: critical
      
      - name: statistic_pvalue_consistency
        enabled: true
        severity: warning
      
      - name: confidence_interval
        enabled: true
        severity: warning
      
      - name: cross_table_consistency
        enabled: true
        severity: info
    
    retry_policy:
      max_attempts: 3
      on_failure: escalate_to_human
  
  # 数据存储
  storage:
    raw_extraction: "./extraction/raw/"
    verified_data: "./extraction/verified/"
    verification_logs: "./extraction/logs/"
    
    formats:
      - json
      - csv
      - excel
```

---

## 性能预期

| 指标 | 纯LLM提取 | 双轨制系统 | 改进 |
|------|----------|-----------|------|
| 数值准确率 | 70-80% | 95-98% | +25% |
| 人工复核工作量 | 100% | 15-30% | ↓70% |
| 处理时间/表 | 2分钟 | 5分钟（含复核） | +150% |
| 数据可信度 | 中 | 高 | 显著 |
| 错误检出率 | 30% | 90%+ | +200% |

---

## 使用建议

### 场景1: 快速筛选阶段（大量表格）
```yaml
配置:
  track_a.auto_accept.enabled: true
  track_a.auto_accept.min_confidence: 0.85
  track_b.enabled: false  # 先不人工复核
  
流程:
  1. AI批量提取所有表格
  2. 仅标记C级表格
  3. 统计提取成功率
  4. 决定是否需要启用人工复核
```

### 场景2: 精筛阶段（关键表格）
```yaml
配置:
  track_a.auto_accept.enabled: false
  track_b.enabled: true
  
流程:
  1. AI提取关键表格
  2. 所有B/C级单元格人工复核
  3. 运行Table-Logic-Verify
  4. 通过后进入证据综合
```

### 场景3: 顶刊综述（高质量要求）
```yaml
配置:
  track_a.auto_accept.enabled: false
  track_b.enabled: true
  track_c.retry_policy.max_attempts: 5
  
流程:
  1. AI提取所有表格
  2. 100%人工复核（即使是A级也抽检）
  3. 运行完整校验套件
  4. 不通过则返回重新提取
  5. 最终人工确认
```

---

*版本: 1.0.0*
*更新日期: 2026-03-12*
