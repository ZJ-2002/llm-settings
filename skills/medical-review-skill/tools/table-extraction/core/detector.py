#!/usr/bin/env python3
"""
表格检测器 - 检测PDF中的表格区域

注意：此模块需要 PyMuPDF (fitz) 支持。
请在需要PDF解析功能时安装: pip install PyMuPDF>=1.23.0
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import re

# 延迟导入 fitz，实现可选依赖
_fitz_available = False
try:
    import fitz  # PyMuPDF
    _fitz_available = True
except ImportError:
    fitz = None


@dataclass
class TableRegion:
    """表格区域定义"""
    page_num: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    table_id: str
    complexity_score: float  # 复杂度评分 0-1
    detection_method: str  # 'lines', 'layout', or 'merged'


class TableDetector:
    """PDF表格检测器
    
    此类需要 PyMuPDF (fitz) 支持。如果未安装，初始化时会抛出 ImportError。
    
    安装命令:
        pip install PyMuPDF>=1.23.0
    """
    
    def __init__(self, min_table_area: float = 10000):
        """
        初始化检测器
        
        Args:
            min_table_area: 最小表格面积（平方像素）
            
        Raises:
            ImportError: 如果 PyMuPDF 未安装
        """
        if not _fitz_available:
            raise ImportError(
                "PyMuPDF (fitz) 是必需的依赖，但未安装。\n"
                "请运行: pip install PyMuPDF>=1.23.0\n"
                "或安装完整依赖: pip install -r requirements.txt"
            )
        
        self.min_table_area = min_table_area
    
    def detect_tables(self, pdf_path: str) -> List[TableRegion]:
        """
        检测PDF中的所有表格区域
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            表格区域列表
        """
        tables = []
        doc = fitz.open(pdf_path)
        
        try:
            for page_num, page in enumerate(doc):
                page_tables = self._detect_page_tables(page, page_num)
                tables.extend(page_tables)
        finally:
            doc.close()
        
        return tables
    
    def _detect_page_tables(self, page, page_num: int) -> List[TableRegion]:
        """检测单页中的表格"""
        # 方法1: 基于图形线条检测
        line_tables = self._detect_from_lines(page)
        
        # 方法2: 基于文本布局检测
        layout_tables = self._detect_from_layout(page)
        
        # 合并检测结果
        merged = self._merge_detections(line_tables + layout_tables)
        
        # 创建TableRegion对象
        regions = []
        for i, bbox in enumerate(merged):
            complexity = self._assess_complexity(page, bbox)
            method = self._determine_detection_method(page, bbox)
            
            regions.append(TableRegion(
                page_num=page_num,
                bbox=bbox,
                table_id=f"T{page_num}_{i}",
                complexity_score=complexity,
                detection_method=method
            ))
        
        return regions
    
    def _detect_from_lines(self, page) -> List[Tuple[float, float, float, float]]:
        """基于线条检测表格"""
        drawings = page.get_drawings()
        
        # 收集水平线和垂直线
        h_lines = []
        v_lines = []
        
        for item in drawings:
            if item['type'] == 'l':  # 直线
                x0, y0, x1, y1 = item['rect']
                # 判断是水平线还是垂直线
                if abs(y1 - y0) < 2:  # 水平线
                    h_lines.append((min(x0, x1), y0, max(x0, x1), y1))
                elif abs(x1 - x0) < 2:  # 垂直线
                    v_lines.append((x0, min(y0, y1), x1, max(y0, y1)))
        
        # 基于线条交点识别表格区域
        if len(h_lines) >= 2 and len(v_lines) >= 2:
            # 简化处理：返回包含所有线条的边界框
            all_x = [p[0] for p in h_lines + v_lines] + [p[2] for p in h_lines + v_lines]
            all_y = [p[1] for p in h_lines + v_lines] + [p[3] for p in h_lines + v_lines]
            
            bbox = (min(all_x), min(all_y), max(all_x), max(all_y))
            
            # 检查面积
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if area >= self.min_table_area:
                return [bbox]
        
        return []
    
    def _detect_from_layout(self, page) -> List[Tuple[float, float, float, float]]:
        """基于文本布局检测表格"""
        blocks = page.get_text("blocks")
        
        # 分析文本块的对齐模式
        x_positions = {}
        for block in blocks:
            x0, y0, x1, y1 = block[:4]
            # 按列分组
            col_key = round(x0 / 50) * 50  # 简化：50px为列宽单位
            if col_key not in x_positions:
                x_positions[col_key] = []
            x_positions[col_key].append((y0, y1, block[4]))
        
        # 如果有多列对齐的文本，可能是表格
        if len(x_positions) >= 3:
            # 计算文本块的共同边界
            all_blocks = [b[:4] for b in blocks]
            all_x = [b[0] for b in all_blocks] + [b[2] for b in all_blocks]
            all_y = [b[1] for b in all_blocks] + [b[3] for b in all_blocks]
            
            bbox = (min(all_x) - 10, min(all_y) - 10, max(all_x) + 10, max(all_y) + 10)
            
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if area >= self.min_table_area:
                return [bbox]
        
        return []
    
    def _merge_detections(self, detections: List[Tuple[float, float, float, float]], 
                         overlap_threshold: float = 0.5) -> List[Tuple[float, float, float, float]]:
        """合并重叠的检测区域"""
        if not detections:
            return []
        
        # 按面积排序
        sorted_dets = sorted(detections, key=lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)
        
        merged = []
        for det in sorted_dets:
            # 检查是否与已合并的区域重叠
            should_merge = False
            for i, existing in enumerate(merged):
                overlap = self._calculate_overlap(det, existing)
                if overlap > overlap_threshold:
                    # 合并两个区域
                    merged[i] = self._union_bbox(existing, det)
                    should_merge = True
                    break
            
            if not should_merge:
                merged.append(det)
        
        return merged
    
    def _calculate_overlap(self, bbox1: Tuple[float, float, float, float],
                          bbox2: Tuple[float, float, float, float]) -> float:
        """计算两个边界框的重叠比例"""
        x0 = max(bbox1[0], bbox2[0])
        y0 = max(bbox1[1], bbox2[1])
        x1 = min(bbox1[2], bbox2[2])
        y1 = min(bbox1[3], bbox2[3])
        
        if x0 >= x1 or y0 >= y1:
            return 0.0
        
        intersection = (x1 - x0) * (y1 - y0)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        return intersection / min(area1, area2)
    
    def _union_bbox(self, bbox1: Tuple[float, float, float, float],
                   bbox2: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """计算两个边界框的并集"""
        return (
            min(bbox1[0], bbox2[0]),
            min(bbox1[1], bbox2[1]),
            max(bbox1[2], bbox2[2]),
            max(bbox1[3], bbox2[3])
        )
    
    def _assess_complexity(self, page, bbox: Tuple[float, float, float, float]) -> float:
        """
        评估表格复杂度 (0-1)
        
        考虑因素：
        - 行数
        - 是否有合并单元格
        - 多层表头
        - 脚注
        - 嵌套结构
        """
        clip = fitz.Rect(bbox)
        text = page.get_text("text", clip=clip)
        
        complexity_factors = {
            'row_count': min(text.count('\n') / 50, 1.0),  # 归一化到50行
            'has_merged_cells': 0.3 if ('│' in text or '├' in text or '─' * 5 in text) else 0,
            'multi_line_headers': 0.15 if text.count('\n\n') > 2 else 0,
            'has_footnotes': 0.15 if any(c in text for c in ['†', '*', '‡', '§']) else 0,
            'nested_structure': 0.1 if text.count('  ') > 10 else 0
        }
        
        # 加权计算
        weights = {
            'row_count': 0.3,
            'has_merged_cells': 0.25,
            'multi_line_headers': 0.15,
            'has_footnotes': 0.15,
            'nested_structure': 0.15
        }
        
        score = sum(complexity_factors[k] * weights[k] for k in complexity_factors)
        return min(score, 1.0)
    
    def _determine_detection_method(self, page, 
                                   bbox: Tuple[float, float, float, float]) -> str:
        """确定检测方法"""
        clip = fitz.Rect(bbox)
        drawings = page.get_drawings()
        
        # 检查区域内是否有足够的线条
        lines_in_bbox = 0
        for item in drawings:
            if item['type'] == 'l':
                rect = item['rect']
                # 检查线条是否在bbox内
                if (bbox[0] <= rect[0] <= bbox[2] and bbox[1] <= rect[1] <= bbox[3]):
                    lines_in_bbox += 1
        
        if lines_in_bbox >= 4:
            return 'lines'
        else:
            return 'layout'


def check_fitz_available() -> bool:
    """检查 PyMuPDF (fitz) 是否可用"""
    return _fitz_available


# 简单的测试代码
if __name__ == '__main__':
    import sys
    
    if not _fitz_available:
        print("错误: PyMuPDF (fitz) 未安装")
        print("请运行: pip install PyMuPDF>=1.23.0")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage: python detector.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    detector = TableDetector()
    
    print(f"正在检测: {pdf_path}")
    tables = detector.detect_tables(pdf_path)
    
    print(f"\n检测到 {len(tables)} 个表格:")
    for table in tables:
        print(f"\n  表格 {table.table_id}:")
        print(f"    页面: {table.page_num + 1}")
        print(f"    位置: ({table.bbox[0]:.1f}, {table.bbox[1]:.1f}) - ({table.bbox[2]:.1f}, {table.bbox[3]:.1f})")
        print(f"    复杂度: {table.complexity_score:.2f}")
        print(f"    检测方法: {table.detection_method}")
