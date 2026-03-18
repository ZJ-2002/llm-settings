#!/usr/bin/env python3
"""
增强型表格提取器 (EnhancedTableExtractor)
v2.5.1 核心升级组件

整合以下新模块：
1. HierarchicalHeaderParser - 多级表头解析
2. FootnoteLinker - 脚注关联
3. TableSanitizer - 表格数据预处理
4. HeterogeneityMonitor - 异质性监测

使用方式：
    extractor = EnhancedTableExtractor(specialty="LDH")
    result = extractor.extract_and_validate(pdf_path, table_idx=0)
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

# 导入核心模块
from .header_parser import HierarchicalHeaderParser
from .footnote_linker import FootnoteLinker
from .table_sanitizer import TableSanitizer, SanitizationReport
from .heterogeneity_monitor import HeterogeneityMonitor


@dataclass
class ExtractionResult:
    """提取结果"""
    paper_id: str
    table_id: str
    table_title: str
    
    # 原始提取
    raw_rows: List[List[Dict]]
    raw_footnotes: List[str]
    
    # 清洗后数据
    sanitized_table: List[List[Any]]
    
    # 质量报告
    sanitization_report: Dict[str, Any]
    heterogeneity_report: Optional[Dict[str, Any]]
    
    # 元数据
    extraction_timestamp: str
    specialty: str
    confidence_level: str  # A/B/C
    
    # 输出文件路径
    output_files: Dict[str, str] = field(default_factory=dict)


class EnhancedTableExtractor:
    """
    增强型表格提取器 v2.5.1
    
    针对脊柱外科（LDH）文献优化的智能表格提取系统
    """
    
    # 置信度阈值
    AUTO_ACCEPT_THRESHOLD = 0.90  # 自动通过阈值
    MANUAL_REVIEW_THRESHOLD = 0.70  # 人工复核阈值
    
    def __init__(self, specialty: str = "LDH", output_dir: str = "./extraction"):
        """
        初始化提取器
        
        Args:
            specialty: 专科领域 (LDH/General)
            output_dir: 输出目录
        """
        self.specialty = specialty
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.sanitizer = TableSanitizer(specialty=specialty)
        self.heterogeneity_monitor = HeterogeneityMonitor()
        
        # 跨表一致性检查（Golden Master）
        self.study_registry: Dict[str, Dict[str, Any]] = {}
    
    def extract_and_validate(self, 
                             table_data: Dict[str, Any],
                             paper_id: str,
                             footnotes: List[str] = None,
                             header_row_count: int = 2) -> ExtractionResult:
        """
        提取并验证表格数据
        
        Args:
            table_data: 原始表格数据
            paper_id: 论文标识
            footnotes: 表格脚注
            header_row_count: 表头行数
        
        Returns:
            ExtractionResult: 提取结果
        """
        footnotes = footnotes or []
        table_title = table_data.get('title', 'Unknown Table')
        
        # 步骤1: 表格数据清洗
        sanitized_table, sanitization_report = self.sanitizer.sanitize(
            table_data, 
            footnotes, 
            header_row_count
        )
        
        # 步骤2: 异质性监测（针对数值型单元格）
        heterogeneity_report = self._monitor_heterogeneity(
            paper_id, sanitized_table, table_title
        )
        
        # 步骤3: 跨表一致性检查（Golden Master）
        consistency_check = self._check_cross_table_consistency(
            paper_id, sanitized_table
        )
        
        # 步骤4: 确定置信度等级
        confidence_level = self._determine_confidence_level(
            sanitization_report, heterogeneity_report, consistency_check
        )
        
        # 步骤5: 生成结果
        result = ExtractionResult(
            paper_id=paper_id,
            table_id=f"{paper_id}_table",
            table_title=table_title,
            raw_rows=table_data.get('rows', []),
            raw_footnotes=footnotes,
            sanitized_table=sanitized_table,
            sanitization_report=asdict(sanitization_report) if hasattr(sanitization_report, '__dataclass_fields__') else sanitization_report,
            heterogeneity_report=heterogeneity_report,
            extraction_timestamp=datetime.now().isoformat(),
            specialty=self.specialty,
            confidence_level=confidence_level
        )
        
        # 步骤6: 保存结果
        self._save_results(result)
        
        # 步骤7: 注册到Golden Master
        self._register_to_golden_master(paper_id, sanitized_table)
        
        return result
    
    def _monitor_heterogeneity(self, 
                               paper_id: str, 
                               sanitized_table: List[List[Any]],
                               context: str = "") -> Optional[Dict[str, Any]]:
        """监测异质性"""
        
        for row in sanitized_table:
            if not row:
                continue
            
            # 获取行标签
            row_label = row[0].row_label if hasattr(row[0], 'row_label') else ""
            
            for cell in row:
                # 只监测数值型单元格
                if not hasattr(cell, 'is_numeric') or not cell.is_numeric:
                    continue
                
                # 只监测有明确标签的行
                if not row_label:
                    continue
                
                # 获取数值
                mean_val = cell.cleaned_value if hasattr(cell, 'cleaned_value') else None
                if mean_val is None:
                    continue
                
                # 尝试提取SD
                sd_val = None
                n_val = cell.sample_size if hasattr(cell, 'sample_size') else None
                
                # 执行监测
                self.heterogeneity_monitor.monitor_cell(
                    label=row_label,
                    mean=mean_val,
                    sd=sd_val,
                    n=n_val,
                    study_id=paper_id,
                    context={'table_context': context}
                )
        
        # 生成报告
        return self.heterogeneity_monitor.generate_report()
    
    def _check_cross_table_consistency(self, 
                                       paper_id: str, 
                                       sanitized_table: List[List[Any]]) -> Dict[str, Any]:
        """
        跨表一致性检查（Golden Master）
        
        检查当前表格的样本量是否与之前记录的该研究不一致
        """
        issues = []
        
        # 提取当前表格的样本量信息
        current_sample_sizes = {}
        for row in sanitized_table:
            for cell in row:
                if hasattr(cell, 'sample_size') and cell.sample_size:
                    key = f"col_{cell.col_idx}"
                    current_sample_sizes[key] = cell.sample_size
        
        # 检查是否与已注册数据冲突
        if paper_id in self.study_registry:
            registered_data = self.study_registry[paper_id]
            registered_n = registered_data.get('sample_size')
            
            for key, current_n in current_sample_sizes.items():
                if registered_n and current_n != registered_n:
                    issues.append({
                        'type': 'sample_size_mismatch',
                        'message': f'样本量不一致: 之前记录n={registered_n}, 当前n={current_n}',
                        'severity': 'critical'
                    })
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def _register_to_golden_master(self, 
                                   paper_id: str, 
                                   sanitized_table: List[List[Any]]):
        """注册到Golden Master"""
        # 提取关键信息
        sample_sizes = set()
        for row in sanitized_table:
            for cell in row:
                if hasattr(cell, 'sample_size') and cell.sample_size:
                    sample_sizes.add(cell.sample_size)
        
        self.study_registry[paper_id] = {
            'sample_size': max(sample_sizes) if sample_sizes else None,
            'extraction_count': self.study_registry.get(paper_id, {}).get('extraction_count', 0) + 1
        }
    
    def _determine_confidence_level(self, 
                                    sanitization_report: SanitizationReport,
                                    heterogeneity_report: Optional[Dict],
                                    consistency_check: Dict[str, Any]) -> str:
        """确定置信度等级"""
        
        # 计算基础质量分
        quality_score = sanitization_report.quality_score if hasattr(sanitization_report, 'quality_score') else 1.0
        
        # 异质性惩罚
        heterogeneity_penalty = 0
        if heterogeneity_report:
            critical_count = heterogeneity_report.get('alerts', {}).get('critical', 0)
            warning_count = heterogeneity_report.get('alerts', {}).get('warning', 0)
            heterogeneity_penalty = critical_count * 0.2 + warning_count * 0.1
        
        # 一致性惩罚
        consistency_penalty = 0
        if not consistency_check.get('passed', True):
            consistency_penalty = 0.3
        
        final_score = max(0, quality_score - heterogeneity_penalty - consistency_penalty)
        
        # 确定等级
        if final_score >= self.AUTO_ACCEPT_THRESHOLD:
            return "A"
        elif final_score >= self.MANUAL_REVIEW_THRESHOLD:
            return "B"
        else:
            return "C"
    
    def _save_results(self, result: ExtractionResult):
        """保存提取结果"""
        
        # 主结果文件
        result_file = self.output_dir / f"{result.paper_id}_extracted.json"
        
        # 转换为可序列化格式
        result_dict = {
            'paper_id': result.paper_id,
            'table_id': result.table_id,
            'table_title': result.table_title,
            'extraction_timestamp': result.extraction_timestamp,
            'specialty': result.specialty,
            'confidence_level': result.confidence_level,
            'sanitization_report': result.sanitization_report,
            'heterogeneity_report': result.heterogeneity_report,
            'sanitized_data': self._serialize_sanitized_table(result.sanitized_table)
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        result.output_files['main'] = str(result_file)
        
        # 质量控制报告
        if result.confidence_level == "C" or \
           (result.heterogeneity_report and result.heterogeneity_report.get('alerts', {}).get('critical', 0) > 0):
            
            qc_file = self.output_dir / f"{result.paper_id}_qc_report.md"
            self._generate_qc_report(result, qc_file)
            result.output_files['qc_report'] = str(qc_file)
    
    def _serialize_sanitized_table(self, table: List[List[Any]]) -> List[List[Dict]]:
        """序列化清洗后的表格"""
        result = []
        for row in table:
            serialized_row = []
            for cell in row:
                if hasattr(cell, '__dataclass_fields__'):
                    serialized_row.append({
                        'original_value': cell.original_value,
                        'cleaned_value': cell.cleaned_value if hasattr(cell, 'cleaned_value') else None,
                        'is_numeric': cell.is_numeric if hasattr(cell, 'is_numeric') else False,
                        'row_label': cell.row_label if hasattr(cell, 'row_label') else '',
                        'column_path': cell.column_path if hasattr(cell, 'column_path') else [],
                        'sample_size': cell.sample_size if hasattr(cell, 'sample_size') else None,
                        'is_valid': cell.is_valid if hasattr(cell, 'is_valid') else True,
                        'footnotes': cell.footnotes if hasattr(cell, 'footnotes') else []
                    })
                else:
                    serialized_row.append({'value': str(cell)})
            result.append(serialized_row)
        return result
    
    def _generate_qc_report(self, result: ExtractionResult, output_file: Path):
        """生成质量控制报告"""
        
        report = f"""# 表格提取质量控制报告

**论文**: {result.paper_id}  
**表格**: {result.table_title}  
**提取时间**: {result.extraction_timestamp}  
**置信度等级**: {result.confidence_level}

---

## 数据质量摘要

"""
        
        # 清洗报告
        if result.sanitization_report:
            report += f"""### 清洗统计
- 总单元格数: {result.sanitization_report.get('total_cells', 'N/A')}
- 数值单元格: {result.sanitization_report.get('numeric_cells', 'N/A')}
- 无效单元格: {result.sanitization_report.get('invalid_cells', 'N/A')}
- 质量评分: {result.sanitization_report.get('quality_score', 'N/A')}

### 边界违规
"""
            violations = result.sanitization_report.get('boundary_violations', [])
            if violations:
                for v in violations:
                    report += f"- [{v['row']},{v['col']}] {v['label']}: {v['value']} - {'; '.join(v['issues'])}\n"
            else:
                report += "无边界违规\n"
            
            # 建议
            recommendations = result.sanitization_report.get('recommendations', [])
            if recommendations:
                report += "\n### 建议\n"
                for rec in recommendations:
                    report += f"- 💡 {rec}\n"
        
        # 异质性报告
        if result.heterogeneity_report:
            report += f"""

## 异质性监测

- 监测指标数: {result.heterogeneity_report.get('monitored_metrics', 'N/A')}
- 严重警报: {result.heterogeneity_report.get('alerts', {}).get('critical', 'N/A')}
- 警告: {result.heterogeneity_report.get('alerts', {}).get('warning', 'N/A')}

### 警报详情
"""
            alerts = result.heterogeneity_report.get('alert_details', [])
            if alerts:
                for alert in alerts:
                    level_icon = "🛑" if alert['level'] == 'critical' else "⚠️"
                    report += f"- {level_icon} [{alert['metric']}] {alert['study']}: {alert['message']} (CV={alert['cv']}, Z={alert['z_score']})\n"
            else:
                report += "无异质性警报\n"
            
            # 建议
            recommendations = result.heterogeneity_report.get('recommendations', [])
            if recommendations:
                report += "\n### 异质性建议\n"
                for rec in recommendations:
                    report += f"- 💡 {rec}\n"
        
        report += f"""

---

*报告由 Medical Review Skill v2.5.1 自动生成*
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)


# ==================== 快速使用接口 ====================

def quick_extract(table_data: Dict[str, Any], 
                  paper_id: str,
                  specialty: str = "LDH") -> ExtractionResult:
    """
    快速提取接口
    
    使用示例：
        result = quick_extract({
            'title': 'Baseline',
            'rows': [...]
        }, paper_id='Smith2023')
    """
    extractor = EnhancedTableExtractor(specialty=specialty)
    return extractor.extract_and_validate(table_data, paper_id)


# ==================== 测试 ====================

def test_enhanced_extraction():
    """测试增强提取"""
    print("\n" + "="*70)
    print("Test: 增强型表格提取")
    print("="*70)
    
    # 模拟表格数据
    table_data = {
        'title': 'Baseline Characteristics (LDH)',
        'rows': [
            # 表头
            [{'value': 'Characteristics'}, {'value': 'PELD (n=120)', 'colspan': 2}, {'value': 'Open (n=115)', 'colspan': 2}],
            [{'value': ''}, {'value': 'Single'}, {'value': 'Multi'}, {'value': 'Single'}, {'value': 'Multi'}],
            # 数据
            [{'value': 'Age (years)'}, {'value': '55.2±8.3'}, {'value': '58.1±9.2'}, {'value': '54.8±9.1'}, {'value': '57.5±8.8'}],
            [{'value': 'VAS leg pain'}, {'value': '7.2±1.3*'}, {'value': '7.5±1.1*'}, {'value': '6.8±1.2*'}, {'value': '7.0±1.4*'}],
            [{'value': 'ODI (%)'}, {'value': '45.2±12.3'}, {'value': '48.5±11.8'}, {'value': '44.8±13.1'}, {'value': '47.2±12.5'}],
        ]
    }
    
    footnotes = [
        "* P < 0.05 vs baseline",
        "† Post-hoc subgroup analysis"
    ]
    
    extractor = EnhancedTableExtractor(specialty="LDH")
    result = extractor.extract_and_validate(table_data, "Smith2023", footnotes)
    
    print(f"\n提取结果:")
    print(f"  论文ID: {result.paper_id}")
    print(f"  表格标题: {result.table_title}")
    print(f"  置信度: {result.confidence_level}")
    print(f"  输出文件: {result.output_files}")
    
    print(f"\n质量报告:")
    print(f"  质量评分: {result.sanitization_report.get('quality_score')}")
    
    if result.heterogeneity_report:
        print(f"\n异质性报告:")
        print(f"  监测指标: {result.heterogeneity_report.get('monitored_metrics')}")
        print(f"  警报: {result.heterogeneity_report.get('alerts')}")
    
    print("\n✅ 增强提取测试通过")
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("EnhancedTableExtractor - 增强型表格提取器测试")
    print("="*70)
    
    test_enhanced_extraction()
    
    print("\n" + "="*70)
    print("所有测试通过！")
    print("="*70)
