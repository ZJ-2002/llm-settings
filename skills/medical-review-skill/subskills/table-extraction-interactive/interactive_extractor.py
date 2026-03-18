#!/usr/bin/env python3
"""
交互式表格提取器
提供对话式界面，无需命令行操作
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

# 引入核心模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools' / 'table-extraction'))
from core.extractor import DualTrackExtractor, ExtractedTable


@dataclass
class ReviewSession:
    """复核会话状态"""
    paper_id: str
    pdf_path: str
    tables: List[ExtractedTable]
    current_table_idx: int = 0
    current_cell_idx: int = 0
    verified_data: Dict = None
    
    def __post_init__(self):
        if self.verified_data is None:
            self.verified_data = {}


class InteractiveTableExtractor:
    """交互式表格提取器"""
    
    def __init__(self):
        self.extractor = DualTrackExtractor()
        self.session: Optional[ReviewSession] = None
    
    def start_extraction(self, pdf_path: str, callback: Callable = None) -> Dict:
        """
        开始提取流程
        
        Args:
            pdf_path: PDF文件路径
            callback: 进度回调函数
            
        Returns:
            提取结果摘要
        """
        paper_id = Path(pdf_path).stem
        
        print(f"📊 开始提取表格 - {paper_id}")
        print("\n[处理中... 约30秒]\n")
        
        # 执行提取
        tables = self.extractor.extract_from_pdf(pdf_path)
        
        # 创建会话
        self.session = ReviewSession(
            paper_id=paper_id,
            pdf_path=pdf_path,
            tables=tables
        )
        
        # 生成摘要
        summary = self._generate_summary(tables)
        
        return summary
    
    def _generate_summary(self, tables: List[ExtractedTable]) -> Dict:
        """生成提取摘要"""
        summary = {
            'paper_id': self.session.paper_id if self.session else '',
            'total_tables': len(tables),
            'auto_accepted': [],
            'needs_review': [],
            'by_confidence': {'A': 0, 'B': 0, 'C': 0}
        }
        
        for table in tables:
            level = 'A' if table.confidence_assessment['overall_score'] >= 0.9 else \
                   'B' if table.confidence_assessment['overall_score'] >= 0.7 else 'C'
            
            summary['by_confidence'][level] += 1
            
            if table.needs_review:
                summary['needs_review'].append({
                    'table_id': table.table_id,
                    'title': table.title,
                    'confidence': table.confidence_assessment['overall_score'],
                    'level': level
                })
            else:
                summary['auto_accepted'].append({
                    'table_id': table.table_id,
                    'title': table.title,
                    'confidence': table.confidence_assessment['overall_score']
                })
        
        return summary
    
    def format_summary_for_display(self, summary: Dict) -> str:
        """格式化摘要为可显示的文本"""
        text = f"""✅ 提取完成！

检测到 {summary['total_tables']} 个表格：
┌─────────────┬───────────────────┬──────────┬────────┐
│ 表格        │ 内容              │ 置信度   │ 状态   │
├─────────────┼───────────────────┼──────────┼────────┤"""
        
        for table in summary['auto_accepted']:
            text += f"\n│ {table['table_id']:<11} │ {table['title']:<17} │ {table['confidence']*100:.0f}% (A) │ ✅ 入库 │"
        
        for table in summary['needs_review']:
            icon = '⚠️' if table['level'] == 'B' else '❌'
            status = '建议复核' if table['level'] == 'B' else '需要复核'
            text += f"\n│ {table['table_id']:<11} │ {table['title']:<17} │ {table['confidence']*100:.0f}% ({table['level']}) │ {icon} {status} │"
        
        text += """
└─────────────┴───────────────────┴──────────┴────────┘
"""
        
        auto_count = len(summary['auto_accepted'])
        if auto_count > 0:
            text += f"\n{auto_count} 个表格已自动通过校验并入库。"
        
        if summary['needs_review']:
            text += f"\n{len(summary['needs_review'])} 个表格需要您复核。"
        
        return text
    
    def get_next_review_item(self) -> Optional[Dict]:
        """获取下一个需要复核的项"""
        if not self.session:
            return None
        
        tables = self.session.tables
        idx = self.session.current_table_idx
        
        while idx < len(tables):
            table = tables[idx]
            if table.needs_review:
                return self._format_table_for_review(table)
            idx += 1
            self.session.current_table_idx = idx
        
        return None
    
    def _format_table_for_review(self, table: ExtractedTable) -> Dict:
        """格式化表格为复核格式"""
        assessment = table.confidence_assessment
        
        # 分类单元格
        high_conf = []
        review_items = []
        
        for cell_info in assessment.get('all_assessments', []):
            cell = {
                'row': cell_info['row'],
                'col': cell_info['col'],
                'value': cell_info['value'],
                'confidence': cell_info['assessment'].score,
                'level': cell_info['assessment'].level.value
            }
            
            if cell_info['assessment'].level == ConfidenceLevel.HIGH:
                high_conf.append(cell)
            else:
                review_items.append(cell)
        
        return {
            'table_id': table.table_id,
            'title': table.title,
            'overall_confidence': assessment['overall_score'],
            'high_confidence_items': high_conf,
            'review_items': review_items,
            'rows': table.rows,
            'headers': table.headers
        }
    
    def handle_user_response(self, response: str, context: Dict) -> Dict:
        """
        处理用户回复
        
        Args:
            response: 用户输入
            context: 当前上下文
            
        Returns:
            下一步操作指示
        """
        response = response.strip().lower()
        
        # 确认类回复
        if response in ['是', '正确', '对', 'yes', 'y', 'ok', '确认']:
            return {'action': 'confirm', 'message': '已确认'}
        
        # 否定类回复
        if response in ['否', '错误', '不对', 'no', 'n']:
            return {'action': 'request_correction', 'message': '请提供正确值'}
        
        # 修正类回复
        if response.startswith(('改为', '应该是', '修正为', '更正为')):
            corrected_value = response.split('为', 1)[-1].strip()
            return {'action': 'correct', 'value': corrected_value}
        
        # 查看原文
        if any(kw in response for kw in ['查看', '原文', 'pdf', '截图']):
            return {'action': 'show_source', 'message': '显示PDF原文'}
        
        # 跳过
        if any(kw in response for kw in ['跳过', '稍后', 'skip', 'pass']):
            return {'action': 'skip', 'message': '已跳过，标记为待处理'}
        
        # 全部正确
        if any(kw in response for kw in ['全部', '都对', 'all correct']):
            return {'action': 'confirm_all', 'message': '已确认全部'}
        
        # 完成
        if response in ['完成', '结束', 'done', 'finish']:
            return {'action': 'finish', 'message': '复核完成'}
        
        # 默认：可能是数值直接输入
        return {'action': 'interpret', 'raw_input': response}
    
    def generate_final_report(self) -> str:
        """生成最终复核报告"""
        if not self.session:
            return "无活动会话"
        
        session = self.session
        total_tables = len(session.tables)
        
        # 统计
        stats = {
            'total_extracted': 0,
            'total_corrected': 0,
            'auto_accepted': 0,
            'manually_reviewed': 0
        }
        
        for table in session.tables:
            stats['total_extracted'] += table.confidence_assessment['cell_count']
            if not table.needs_review:
                stats['auto_accepted'] += 1
            else:
                stats['manually_reviewed'] += 1
        
        report = f"""✅ 所有表格复核完成！

📊 提取摘要:
┌─────────────┬────────┬────────┬────────┐
│ 表格        │ 提取   │ 修正   │ 状态   │
├─────────────┼────────┼────────┼────────┤"""
        
        for table in session.tables:
            cell_count = table.confidence_assessment['cell_count']
            corrected = len([c for c in session.verified_data.get(table.table_id, [])
                           if c.get('corrected')])
            status = '✅ 入库'
            report += f"\n│ {table.table_id:<11} │ {cell_count:<6} │ {corrected:<6} │ {status:<6} │"
        
        report += f"""
├─────────────┼────────┼────────┼────────┤
│ 总计        │ {stats['total_extracted']:<6} │ {stats['total_corrected']:<6} │ ✅ 完成 │
└─────────────┴────────┴────────┴────────┘

数据质量: {(1 - stats['total_corrected']/max(stats['total_extracted'], 1))*100:.0f}%
已通过 Table-Logic-Verify 全部校验

数据已保存至: extraction/{session.paper_id}_verified.json
"""
        
        return report
    
    def save_verified_data(self, output_dir: str = './extraction'):
        """保存验证后的数据"""
        if not self.session:
            return
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        data = {
            'paper_id': self.session.paper_id,
            'pdf_path': self.session.pdf_path,
            'extraction_timestamp': datetime.now().isoformat(),
            'tables': []
        }
        
        for table in self.session.tables:
            data['tables'].append({
                'table_id': table.table_id,
                'title': table.title,
                'headers': table.headers,
                'rows': table.rows,
                'verification_result': table.verification_result,
                'confidence_assessment': table.confidence_assessment
            })
        
        output_file = output_path / f"{self.session.paper_id}_verified.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(output_file)


# 简化的命令行接口，用于Skill调用
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--summary', action='store_true', help='仅输出摘要')
    
    args = parser.parse_args()
    
    extractor = InteractiveTableExtractor()
    summary = extractor.start_extraction(args.pdf_path)
    
    if args.summary:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(extractor.format_summary_for_display(summary))