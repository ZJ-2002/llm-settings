#!/usr/bin/env python3
"""
双轨制表格提取器 - 主类
整合检测、提取、置信度评估、校验全流程

注意：如需PDF解析功能，请安装 PyMuPDF:
    pip install PyMuPDF>=1.23.0
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
from datetime import datetime

# 从 detector 导入 TableRegion (dataclass，无需 fitz)
from .detector import TableRegion, check_fitz_available
from .confidence import ConfidenceAssessor, ConfidenceLevel
from .verification import TableLogicVerifier


@dataclass
class ExtractedTable:
    """提取的表格数据"""
    table_id: str
    page_num: int
    bbox: Tuple[float, float, float, float]
    complexity_score: float
    
    # 提取内容
    title: str
    headers: List[Dict]
    rows: List[Dict]
    footnotes: List[str]
    
    # 置信度信息
    confidence_assessment: Dict
    
    # 校验结果
    verification_result: Optional[Dict] = None
    
    # 元数据
    extraction_timestamp: str = ''
    needs_review: bool = False


class DualTrackExtractor:
    """双轨制表格提取器
    
    此类需要 PyMuPDF (fitz) 支持才能解析PDF文件。
    其他功能（置信度评估、校验）无需外部依赖。
    
    安装命令:
        pip install PyMuPDF>=1.23.0
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化提取器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化各组件（延迟初始化 detector）
        self._detector = None
        self.confidence_assessor = ConfidenceAssessor()
        self.verifier = TableLogicVerifier()
        
        # 配置参数
        self.auto_accept_threshold = self.config.get('auto_accept_threshold', 0.90)
        self.review_threshold = self.config.get('review_threshold', 0.70)
    
    @property
    def detector(self):
        """延迟初始化 detector"""
        if self._detector is None:
            if not check_fitz_available():
                raise ImportError(
                    "PDF解析功能需要 PyMuPDF (fitz)，但未安装。\n"
                    "请运行: pip install PyMuPDF>=1.23.0\n"
                    "或: pip install -r requirements.txt"
                )
            from .detector import TableDetector
            self._detector = TableDetector()
        return self._detector
    
    def extract_from_pdf(self, pdf_path: str, 
                        table_page: Optional[int] = None) -> List[ExtractedTable]:
        """
        从PDF提取所有表格
        
        注意：此功能需要 PyMuPDF (fitz) 支持。
        
        Args:
            pdf_path: PDF文件路径
            table_page: 指定页面（可选，0-based）
            
        Returns:
            提取的表格列表
            
        Raises:
            ImportError: 如果 PyMuPDF 未安装
        """
        # 轨道A: 检测表格
        print(f"[轨道A] 检测表格: {pdf_path}")
        regions = self.detector.detect_tables(pdf_path)
        
        if table_page is not None:
            regions = [r for r in regions if r.page_num == table_page]
        
        print(f"[轨道A] 检测到 {len(regions)} 个表格")
        
        # 提取每个表格
        extracted_tables = []
        for region in regions:
            table = self._extract_single_table(pdf_path, region)
            extracted_tables.append(table)
        
        return extracted_tables
    
    def _extract_single_table(self, pdf_path: str, 
                             region: TableRegion) -> ExtractedTable:
        """提取单个表格"""
        print(f"[轨道A] 提取表格 {region.table_id} (复杂度: {region.complexity_score:.2f})")
        
        # TODO: 实际项目中这里会调用LLM进行提取
        # 这里使用模拟数据进行演示
        mock_extraction = self._mock_llm_extraction(region)
        
        # 置信度评估
        print(f"[轨道A] 评估置信度...")
        confidence_result = self.confidence_assessor.assess_table(mock_extraction)
        
        # 判断是否需要复核
        needs_review = (
            confidence_result['low_confidence_count'] > 0 or
            confidence_result['overall_score'] < self.review_threshold
        )
        
        # 如果置信度高，直接校验
        verification_result = None
        if not needs_review or confidence_result['overall_score'] >= self.auto_accept_threshold:
            print(f"[轨道C] 自动校验...")
            verification_result = self.verifier.verify(mock_extraction)
            
            if verification_result['status'] == 'failed':
                needs_review = True
        
        return ExtractedTable(
            table_id=region.table_id,
            page_num=region.page_num,
            bbox=region.bbox,
            complexity_score=region.complexity_score,
            title=mock_extraction.get('title', ''),
            headers=mock_extraction.get('headers', []),
            rows=mock_extraction.get('rows', []),
            footnotes=mock_extraction.get('footnotes', []),
            confidence_assessment=confidence_result,
            verification_result=verification_result,
            extraction_timestamp=datetime.now().isoformat(),
            needs_review=needs_review
        )
    
    def _mock_llm_extraction(self, region: TableRegion) -> Dict:
        """模拟LLM提取（实际项目中替换为真实LLM调用）"""
        # 返回模拟的表格结构
        return {
            'title': f'Table from page {region.page_num + 1}',
            'headers': [
                {'name': 'Characteristic', 'type': 'text'},
                {'name': 'Group A (n=98)', 'type': 'text'},
                {'name': 'Group B (n=102)', 'type': 'text'},
                {'name': 'P value', 'type': 'text'}
            ],
            'rows': [
                {
                    'cells': [
                        {'value': 'Age, years', 'type': 'text'},
                        {'value': '55.2±8.3', 'type': 'text'},
                        {'value': '54.8±9.1', 'type': 'text'},
                        {'value': '0.74', 'type': 'p_value', 'confidence': 0.95}
                    ]
                },
                {
                    'cells': [
                        {'value': 'Male, n (%)', 'type': 'text'},
                        {'value': '48 (49.0%)', 'type': 'percentage', 'confidence': 0.88},
                        {'value': '52 (51.0%)', 'type': 'percentage', 'confidence': 0.88},
                        {'value': '0.82', 'type': 'p_value', 'confidence': 0.92}
                    ]
                }
            ],
            'footnotes': ['Data are mean±SD or n (%)']
        }
    
    def generate_review_report(self, table: ExtractedTable) -> str:
        """
        生成人工复核报告
        
        Returns:
            Markdown格式的复核报告
        """
        report = f"""# 表格复核报告

## 基本信息
- **表格ID**: {table.table_id}
- **页面**: {table.page_num + 1}
- **复杂度**: {table.complexity_score:.2f}/1.0
- **提取时间**: {table.extraction_timestamp}

## 置信度评估
- **整体置信度**: {table.confidence_assessment['overall_score']:.2f}
- **单元格总数**: {table.confidence_assessment['cell_count']}
- **A级(>=90%)**: {table.confidence_assessment['high_confidence_count']}
- **B级(70-90%)**: {table.confidence_assessment['medium_confidence_count']}
- **C级(<70%)**: {table.confidence_assessment['low_confidence_count']}

## 需要复核的单元格
"""
        
        for cell in table.confidence_assessment.get('cells_need_review', []):
            assessment = cell['assessment']
            report += f"""
### 位置: 行{cell['row']+1}, 列{cell['col']+1}
- **提取值**: {cell['value']}
- **置信度**: {assessment.score:.2f} ({assessment.level.value}级)
- **原因**: {assessment.review_reason}
- **各因素得分**:
"""
            for factor, score in assessment.factors.items():
                report += f"  - {factor}: {score:.2f}\n"
        
        if table.verification_result:
            report += f"""
## 自动校验结果
- **状态**: {table.verification_result['status']}
- **严重问题**: {table.verification_result['summary']['critical_issues']}
- **警告**: {table.verification_result['summary']['warning_issues']}
"""
        
        return report
    
    def export_to_json(self, table: ExtractedTable, filepath: str):
        """导出提取结果到JSON"""
        data = {
            'table_id': table.table_id,
            'page_num': table.page_num,
            'bbox': table.bbox,
            'complexity_score': table.complexity_score,
            'title': table.title,
            'headers': table.headers,
            'rows': table.rows,
            'footnotes': table.footnotes,
            'confidence_assessment': table.confidence_assessment,
            'verification_result': table.verification_result,
            'extraction_timestamp': table.extraction_timestamp,
            'needs_review': table.needs_review
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"已导出到: {filepath}")


# 简化的命令行接口
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extractor.py <pdf_path> [--page N]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # 检查依赖
    if not check_fitz_available():
        print("错误: PyMuPDF (fitz) 未安装")
        print("请运行: pip install PyMuPDF>=1.23.0")
        sys.exit(1)
    
    # 解析参数
    page = None
    if '--page' in sys.argv:
        page_idx = sys.argv.index('--page')
        if page_idx + 1 < len(sys.argv):
            page = int(sys.argv[page_idx + 1]) - 1  # 转换为0-based
    
    # 运行提取
    extractor = DualTrackExtractor()
    tables = extractor.extract_from_pdf(pdf_path, page)
    
    # 输出结果
    for table in tables:
        print(f"\n{'='*60}")
        print(f"表格: {table.table_id}")
        print(f"置信度: {table.confidence_assessment['overall_score']:.2f}")
        print(f"需要复核: {'是' if table.needs_review else '否'}")
        
        if table.needs_review:
            report = extractor.generate_review_report(table)
            print("\n复核报告预览:")
            print(report[:500] + "...")
