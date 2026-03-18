# Table-Extraction 与 Literature-Screening 集成方案

## 工作流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         系统化综述工作流程                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: 文献检索 (Literature Screening)                                    │
│  ═══════════════════════════════════════                                    │
│                                                                              │
│  数据库检索 ──► 导入 EndNote/Zotero ──► AI初筛                               │
│       │                                    │                                 │
│       │                                    ▼                                 │
│       │                             ┌─────────────┐                          │
│       │                             │ 文献去重     │                          │
│       │                             │ 标题摘要筛选 │                          │
│       │                             │ 初筛标签     │                          │
│       │                             └─────────────┘                          │
│       │                                    │                                 │
│       │                                    ▼                                 │
│       │                             全文获取                                  │
│       │                                    │                                 │
│       └────────────────────────────────────┼─────────────────────────────────┘
│                                            │                                 │
│                                            ▼                                 │
│  Phase 2: 表格提取 (Table Extraction)       │                                 │
│  ══════════════════════════════════════    │                                 │
│                                             │                                 │
│  ┌──────────────────────────────────────────┘                                 │
│  │                                                                            │
│  ▼                                                                            │
│  PDF表格提取 ──► 关键信息标注                                                  │
│       │              │                                                        │
│       │              ├─► PICO信息 (人群/干预/对照/结局)                        │
│       │              ├─► 基线特征 (Baseline)                                   │
│       │              ├─► 随访数据 (Follow-up)                                  │
│       │              └─► 不良事件 (Adverse Events)                             │
│       │                                                                       │
│       ▼                                                                       │
│  质量评估 ──► 证据分级                                                          │
│       │              │                                                        │
│       │              ├─► 研究类型标签                                          │
│       │              ├─► 偏倚风险评估                                          │
│       │              └─► GRADE证据质量                                         │
│       │                                                                       │
│       ▼                                                                       │
│  输出: extraction-results.json                                                │
│       │                                                                       │
│       ▼                                                                       │
│  Phase 3: 数据综合 (Evidence Synthesis)                                       │
│  ═══════════════════════════════════════                                      │
│       │                                                                       │
│       ▼                                                                       │
│  标准化数据合并 ──► 亚组分析规划                                                │
│       │              │                                                        │
│       │              ├─► 手术类型分组 (PTED vs MED)                            │
│       │              ├─► 随访时间点分组                                        │
│       │              └─► 患者特征分层                                          │
│       │                                                                       │
│       ▼                                                                       │
│  证据综合 ──► 生成综述报告                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 数据流转规范

### 从 Literature-Screening 传递的数据

```json
{
  "literature_screening_output": {
    "extraction_task": {
      "task_id": "ext-2024-001",
      "paper_info": {
        "doi": "10.1097/BRS.0000000001234",
        "pmid": "12345678",
        "title": "PELD versus MED for lumbar disc herniation: a randomized trial",
        "authors": ["Smith J", "Johnson M"],
        "journal": "Spine",
        "year": 2024,
        "volume": "49",
        "issue": "12",
        "pages": "845-853"
      },
      "screening_decision": {
        "decision": "include",
        "confidence": "high",
        "reason": "Meets all inclusion criteria for PTED vs MED comparison",
        "screened_by": "AI-Assistant",
        "screened_at": "2024-12-01T10:30:00Z"
      },
      "full_text_path": "/papers/pted_med_2024.pdf",
      "priority_level": "high",
      "tags": ["RCT", "single-level", "PTED", "MED", "lumbar"],
      "extraction_requirements": {
        "tables_required": [
          "baseline_characteristics",
          "operative_details",
          "clinical_outcomes",
          "radiographic_outcomes"
        ],
        "special_notes": "Check for subgroup analysis by disc level"
      }
    }
  }
}
```

### 表格提取系统输出的数据

```json
{
  "table_extraction_output": {
    "extraction_id": "ext-2024-001",
    "extraction_timestamp": "2024-12-02T14:20:00Z",
    "extraction_status": "completed",
    
    "extracted_tables": [
      {
        "table_id": "T1",
        "table_type": "baseline_characteristics",
        "page_num": 3,
        "verification_status": "verified",
        "verification_method": "auto_accept",
        "confidence_score": 0.94,
        "data": {
          "headers": [...],
          "rows": [...]
        },
        "annotations": {
          "population_tags": ["PTED", "single-level", "lumbar"],
          "key_variables": ["age", "sex", "bmi", "symptom_duration"]
        }
      }
    ],
    
    "quality_assessment": {
      "rob2_assessment": {
        "overall_risk": "low",
        "domain_judgments": {
          "D1_randomization": "low",
          "D2_deviations": "low",
          "D3_missing_data": "some_concerns",
          "D4_measurement": "low",
          "D5_selective_reporting": "low"
        }
      },
      "grade_assessment": {
        "overall_quality": "high",
        "downgrade_factors": []
      }
    },
    
    "summary_statistics": {
      "total_tables_found": 4,
      "tables_extracted": 4,
      "auto_accepted": 3,
      "human_verified": 1,
      "avg_confidence": 0.91
    },
    
    "errors_and_warnings": [
      {
        "level": "warning",
        "message": "One cell with low confidence in table T3",
        "location": "T3:row5,col2"
      }
    ]
  }
}
```

## 协作接口设计

### 1. 任务队列接口

```python
# 从 Literature-Screening 接收任务
class ExtractionTaskQueue:
    """提取任务队列"""
    
    def receive_task(self, screening_result: Dict) -> str:
        """接收初筛通过的任务"""
        task = {
            'task_id': f"ext-{uuid.uuid4().hex[:8]}",
            'paper_info': screening_result['paper'],
            'status': 'pending',
            'priority': self._calculate_priority(screening_result),
            'created_at': datetime.now().isoformat()
        }
        self.queue.add(task)
        return task['task_id']
    
    def _calculate_priority(self, screening_result: Dict) -> int:
        """计算任务优先级"""
        score = 0
        
        # RCT 优先级更高
        if 'RCT' in screening_result.get('study_type', ''):
            score += 10
        
        # 近期研究
        year = screening_result['paper'].get('year', 2000)
        if year >= 2020:
            score += 5
        
        # 高影响期刊
        if screening_result['paper'].get('journal_impact', 0) > 5:
            score += 3
        
        return score
```

### 2. 数据标准化接口

```python
# 标准化输出格式供 Evidence Synthesis 使用
class StandardizationPipeline:
    """数据标准化流水线"""
    
    def standardize_for_synthesis(self, extraction_result: Dict) -> Dict:
        """标准化为证据综合格式"""
        
        standardized = {
            'paper_id': extraction_result['extraction_id'],
            'paper_metadata': self._extract_metadata(extraction_result),
            'population': self._standardize_population(extraction_result),
            'interventions': self._standardize_interventions(extraction_result),
            'outcomes': self._standardize_outcomes(extraction_result),
            'study_characteristics': self._standardize_study_chars(extraction_result),
            'quality_assessment': extraction_result.get('quality_assessment', {}),
            'extraction_quality': {
                'confidence_score': extraction_result.get('avg_confidence', 0),
                'verification_status': extraction_result.get('extraction_status', 'unknown')
            }
        }
        
        return standardized
    
    def _standardize_population(self, extraction_result: Dict) -> Dict:
        """标准化人群信息"""
        baseline_table = self._find_table_by_type(
            extraction_result, 'baseline_characteristics'
        )
        
        return {
            'total_sample_size': self._extract_n(baseline_table),
            'age_mean_sd': self._extract_age(baseline_table),
            'sex_distribution': self._extract_sex(baseline_table),
            'inclusion_criteria': self._extract_inclusion_criteria(extraction_result),
            'disease_characteristics': self._extract_disease_chars(baseline_table)
        }
```

## 协作工具函数

### 常用工具函数

```python
# integration_utils.py

def get_paper_priority(paper: Dict) -> str:
    """根据文献特征确定提取优先级"""
    score = 0
    
    # 研究设计
    study_design = paper.get('study_design', '').upper()
    if 'RCT' in study_design:
        score += 10
    elif 'COHORT' in study_design:
        score += 5
    elif 'CASE' in study_design:
        score += 2
    
    # 发表年份
    year = paper.get('year', 2000)
    if year >= 2023:
        score += 5
    elif year >= 2020:
        score += 3
    
    # 期刊影响因子
    impact_factor = paper.get('impact_factor', 0)
    if impact_factor >= 10:
        score += 5
    elif impact_factor >= 5:
        score += 3
    
    if score >= 15:
        return "high"
    elif score >= 8:
        return "medium"
    else:
        return "low"


def generate_extraction_summary(extraction_results: List[Dict]) -> str:
    """生成提取结果摘要"""
    total = len(extraction_results)
    auto_accepted = sum(1 for r in extraction_results 
                       if r.get('verification_status') == 'auto_accept')
    human_verified = sum(1 for r in extraction_results 
                        if r.get('verification_status') == 'human_verified')
    avg_confidence = sum(r.get('confidence_score', 0) for r in extraction_results) / total if total else 0
    
    summary = f"""
提取完成摘要:
=============
文献总数: {total}
自动通过: {auto_accepted} ({auto_accepted/total*100:.1f}%)
人工验证: {human_verified} ({human_verified/total*100:.1f}%)
平均置信度: {avg_confidence:.3f}
"""
    return summary


def validate_extraction_completeness(extraction: Dict, requirements: Dict) -> List[str]:
    """验证提取完整性"""
    missing = []
    
    required_tables = requirements.get('tables_required', [])
    extracted_types = [t.get('table_type') for t in extraction.get('extracted_tables', [])]
    
    for table_type in required_tables:
        if table_type not in extracted_types:
            missing.append(f"缺少必需表格: {table_type}")
    
    # 验证关键变量
    baseline_table = next(
        (t for t in extraction.get('extracted_tables', []) 
         if t.get('table_type') == 'baseline_characteristics'),
        None
    )
    
    if baseline_table:
        required_vars = requirements.get('required_variables', [])
        available_vars = baseline_table.get('annotations', {}).get('key_variables', [])
        
        for var in required_vars:
            if var not in available_vars:
                missing.append(f"基线特征表缺少变量: {var}")
    
    return missing
```

## 错误处理与反馈

### 提取失败时的反馈机制

```json
{
  "extraction_failure_report": {
    "task_id": "ext-2024-001",
    "status": "failed",
    "failure_type": "pdf_parsing_error",
    "error_details": {
      "error_code": "PDF_CORRUPTED",
      "message": "无法解析PDF第3页表格",
      "suggested_action": "request_rescan"
    },
    "feedback_to_screening": {
      "action": "request_full_text_update",
      "reason": "PDF文件损坏或扫描质量过低",
      "original_paper_id": "pmid-12345678"
    }
  }
}
```

## 质量保障机制

### 1. 交叉验证

- **文献筛选与表格提取联动**: 筛选阶段的排除理由应在提取报告中体现
- **多表格一致性检查**: 同一研究的不同表格间数值应保持一致
- **正文与表格对照**: 关键数据需在正文中找到对应描述

### 2. 审计追踪

```json
{
  "audit_trail": {
    "extraction_id": "ext-2024-001",
    "events": [
      {
        "timestamp": "2024-12-02T10:00:00Z",
        "event": "task_received",
        "source": "literature_screening",
        "details": "Task created from screening result SR-2024-089"
      },
      {
        "timestamp": "2024-12-02T10:05:00Z",
        "event": "ai_extraction_started",
        "source": "table_extraction_system"
      },
      {
        "timestamp": "2024-12-02T10:08:00Z",
        "event": "verification_required",
        "source": "confidence_assessor",
        "details": "3 cells marked for human review"
      },
      {
        "timestamp": "2024-12-02T14:20:00Z",
        "event": "human_verification_completed",
        "source": "reviewer_id_42",
        "details": "All cells verified, 1 correction made"
      }
    ]
  }
}
```

## 使用示例

### 完整的集成工作流

```python
# integration_example.py

from literature_screening import ScreenResult
from table_extraction import DualTrackExtractor
from evidence_synthesis import SynthesisPipeline

# 1. 从文献筛选接收结果
screen_result = ScreenResult.load("screening_output.json")

# 2. 创建提取任务
extractor = DualTrackExtractor()
task = extractor.create_task(screen_result)

# 3. 执行双轨提取
extraction_result = extractor.extract(task)

# 4. 验证完整性
missing = validate_extraction_completeness(
    extraction_result, 
    screen_result.extraction_requirements
)

if missing:
    print(f"提取不完整: {missing}")
    # 请求人工介入或重新提取

# 5. 标准化输出
standardizer = StandardizationPipeline()
synthesis_ready_data = standardizer.standardize_for_synthesis(extraction_result)

# 6. 传递给证据综合
synthesis = SynthesisPipeline()
synthesis.add_study(synthesis_ready_data)

# 7. 生成报告
print(generate_extraction_summary([extraction_result]))
```

---

*文档版本: 1.0.0*
*更新日期: 2024-12-02*
