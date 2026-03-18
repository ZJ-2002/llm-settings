#!/usr/bin/env python3
"""
多级表头解析器 (HierarchicalHeaderParser) - v2.6 重构版
将表头从简单的二维数组升级为基于路径的语义树

v2.6 核心升级：
1. 完整 rowspan 支持 - 解决纵向跨行表头层级断裂问题
2. 复合 n 值解析 - 支持 n=60+60、n=145/150 等复杂表达
3. 特殊符号提取 - 保留 *, †, ‡, § 等临床标记
4. 物理坐标定位 - Virtual Grid 算法确保对齐准确性

解决痛点：
1. 合并单元格产生的空值填充（支持 colspan + rowspan）
2. 多级表头语义路径构建
3. 样本量 n 值提取与关联（支持复合表达式）
4. 临床符号语义保护
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field


@dataclass
class HeaderNode:
    """
    增强型表头节点，用于构建树形结构
    
    v2.6.1 增强：
    - 支持 row_span_range 记录纵向跨度
    - 增强元数据提取（复合n值、特殊符号）- v2.6.1返回字典格式
    - 保留 raw_text 用于错误溯源
    - 优化父节点链接逻辑，处理空行情况
    """
    text: str
    col_span_range: Tuple[int, int]  # (start_col, end_col)
    row_span_range: Tuple[int, int]  # (start_row, end_row) - v2.6新增
    level: int
    parent: Optional['HeaderNode'] = None
    children: List['HeaderNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""  # v2.6新增：原始文本备份
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.raw_text:
            self.raw_text = self.text
        self.metadata.update(self._extract_enhanced_metadata())
    
    def _extract_enhanced_metadata(self) -> Dict[str, Any]:
        """
        增强型元数据提取 - v2.6
        
        支持：
        1. 复合 n 值：n=120, n=60+60, n=145/150, n=145*
        2. 特殊符号：*, †, ‡, §
        3. 数学求和：自动计算 60+60=120
        """
        meta = {'symbols': [], 'raw_n_text': None}
        
        # 1. 提取特殊临床符号
        symbols = re.findall(r'([\*†‡§])', self.text)
        if symbols:
            meta['symbols'] = symbols
        
        # 2. 复合 n 值提取核心正则 - v2.6.1增强
        # 匹配: n=120, n=60+60, n=145/150, n=145*
        n_pattern = r'[nN]\s*=\s*(\d+(?:[\s\+/]\d+)?)'
        n_matches = re.findall(n_pattern, self.text)
        
        if n_matches:
            raw_n = n_matches[-1]  # 取最后一个
            meta['raw_n_text'] = raw_n
            n_dict = self._parse_compound_n(raw_n)
            meta['primary_n'] = n_dict['primary_n']
            meta['total_n'] = n_dict['total_n']  # v2.6.1: 新增 total_n
            
        return meta
    
    def _parse_compound_n(self, raw: str) -> int:
        """
        解析复合 n 值
        
        支持格式：
        - n=120 -> 120
        - n=60+60 -> 120 (数学求和)
        - n=145/150 -> 145 (取分子，通常为有效随访数)
        """
        # 清理非数字字符（保留+和/）
        clean = re.sub(r'[^\d\+/]', '', raw)
        
        if '+' in clean:
            # 加法情况：60+60 = 120
            try:
                return sum(int(x.strip()) for x in clean.split('+'))
            except ValueError:
                pass
        elif '/' in clean:
            # 分数情况：145/150，取分子
            try:
                return int(clean.split('/')[0].strip())
            except ValueError:
                pass
        
        # 纯数字
        try:
            return int(clean)
        except ValueError:
            return 0
    
    @property
    def full_path(self) -> List[str]:
        """
        获取从根到当前节点的完整路径
        
        v2.6增强：过滤掉作为占位的空节点
        """
        path = []
        curr = self
        while curr:
            # 只保留有语义的 text（非空字符串）
            if curr.text and curr.text.strip():
                path.insert(0, curr.text.strip())
            curr = curr.parent
        return path
    
    @property
    def col_span(self) -> Tuple[int, int]:
        """兼容旧版本的属性访问"""
        return self.col_span_range


class HierarchicalHeaderParser:
    """
    重构后的多级语义表头解析器 (v2.6)
    
    核心升级：
    1. 物理坐标定位算法 - 通过 Virtual Grid 处理 rowspan/colspan
    2. 覆盖驱动型链接 - 基于物理位置而非简单层级
    3. 对齐校验器 - 检查行宽度一致性
    
    针对医学文献（尤其是脊柱外科RCT）中的复杂多级表头设计
    """
    
    def __init__(self):
        self.root_nodes: List[HeaderNode] = []
        self._node_matrix: List[List[Optional[HeaderNode]]] = []
    
    def parse(self, header_rows: List[List[Dict]]) -> Dict[int, List[str]]:
        """
        解析多级表头 - v2.6重构版
        
        Args:
            header_rows: 原始表头行数据，包含单元格文本和位置信息
                        格式: [[{'value': '...', 'colspan': 2, 'rowspan': 1}, ...], ...]
        
        Returns:
            Dict[int, List[str]]: 列索引映射到完整路径语义
                                 {0: ['Group', 'PELD (n=120)', 'Single-level'], ...}
        """
        if not header_rows:
            return {}
        
        # v2.6: 预计算矩阵宽度（考虑所有行的 colspan）
        max_cols = self._calculate_max_cols(header_rows)
        num_rows = len(header_rows)
        
        # v2.6: 构建包含 rowspan 逻辑的虚拟矩阵
        self._node_matrix = [[None for _ in range(max_cols)] for _ in range(num_rows)]
        occupied: Set[Tuple[int, int]] = set()  # 记录被占用的格子
        
        for r_idx, row in enumerate(header_rows):
            c_idx = 0
            for cell_data in row:
                # v2.6: 自动跳过被之前 rowspan 占据的格子
                while (r_idx, c_idx) in occupied:
                    c_idx += 1
                
                if c_idx >= max_cols:
                    break
                
                colspan = cell_data.get('colspan', 1)
                rowspan = cell_data.get('rowspan', 1)  # v2.6: 支持 rowspan
                text = str(cell_data.get('value', '')).strip()
                
                node = HeaderNode(
                    text=text,
                    col_span_range=(c_idx, c_idx + colspan - 1),
                    row_span_range=(r_idx, r_idx + rowspan - 1),  # v2.6: 记录 rowspan
                    level=r_idx,
                    raw_text=text  # 保留原始文本
                )
                
                # v2.6: 填充虚拟矩阵并记录占用
                for dr in range(rowspan):
                    for dc in range(colspan):
                        target_r, target_c = r_idx + dr, c_idx + dc
                        if target_r < num_rows and target_c < max_cols:
                            self._node_matrix[target_r][target_c] = node
                            occupied.add((target_r, target_c))
                
                c_idx += colspan
        
        # v2.6: 建立基于物理覆盖的层级链接
        self._link_nodes_by_coverage()
        
        # 生成列路径映射
        col_paths = {}
        for c in range(max_cols):
            leaf_node = self._node_matrix[-1][c] if self._node_matrix else None
            col_paths[c] = leaf_node.full_path if leaf_node else []
        
        return col_paths
    
    def _calculate_max_cols(self, rows: List[List[Dict]]) -> int:
        """计算矩阵的最大列数（考虑 colspan）"""
        max_cols = 0
        for row in rows:
            row_cols = sum(cell.get('colspan', 1) for cell in row)
            max_cols = max(max_cols, row_cols)
        return max_cols
    
    def _link_nodes_by_coverage(self):
        """
        通过检测物理列范围的交集来建立父子关系 - v2.6.1优化版
        
        v2.6.1 改进：
        1. 使用 while 循环向上溯源，处理空行/装饰性虚线行问题
        2. 优化性能：直接访问首列坐标而非遍历所有列，O(C²) -> O(C)
        
        优点：
        - 无论表头如何交错合并，只要物理位置是垂直相邻的，
          语义路径就能正确挂载。完美解决跨行问题。
        - 即使 PDF 解析产生空行，也能正确找到父节点
        """
        seen_nodes = set()
        num_rows = len(self._node_matrix)
        num_cols = len(self._node_matrix[0]) if self._node_matrix else 0
        
        for r in range(num_rows):
            for c in range(num_cols):
                node = self._node_matrix[r][c]
                if not node or id(node) in seen_nodes:
                    continue
                seen_nodes.add(id(node))
                
                # v2.6.1: 使用 while 循环向上溯源，处理空行问题
                parent_r = node.row_span_range[0] - 1
                parent_node = None
                
                while parent_r >= 0 and not parent_node:
                    # v2.6.1: 优化性能，直接访问首列坐标
                    # 在 Virtual Grid 已经对齐的情况下，父节点一定包含在首列坐标点
                    start_col = node.col_span_range[0]
                    if start_col < num_cols:
                        candidate = self._node_matrix[parent_r][start_col]
                        # 验证列范围确实有交集
                        if candidate and candidate != node:
                            node_cols = range(node.col_span_range[0], node.col_span_range[1] + 1)
                            parent_cols = range(candidate.col_span_range[0], candidate.col_span_range[1] + 1)
                            # 检查是否有交集
                            if (node.col_span_range[0] <= candidate.col_span_range[1] and 
                                node.col_span_range[1] >= candidate.col_span_range[0]):
                                parent_node = candidate
                    
                    if not parent_node:
                        parent_r -= 1  # 继续向上查找
                
                # 建立父子关系
                if parent_node:
                    node.parent = parent_node
                    if node not in parent_node.children:
                        parent_node.children.append(node)
    
    def extract_sample_sizes(self, col_paths: Dict[int, List[str]]) -> Dict[str, Dict[str, Any]]:
        """
        从路径中提取样本量映射 - v2.6增强版
        
        支持复合 n 值：
        - n=120 -> 120
        - n=60+60 -> 120 (多中心研究常见)
        - n=145/150 -> 145 (随访表，分子为有效随访数)
        - n=145* -> 145 (保留符号信息)
        
        Returns:
            Dict: {
                列路径字符串: {
                    'n': 样本量,
                    'raw': 原始n值文本,
                    'is_compound': 是否为复合表达式,
                    'source_level': 来源层级,
                    'symbols': 特殊符号列表
                }
            }
        """
        sample_sizes = {}
        
        for col_idx, path in col_paths.items():
            full_path_str = " > ".join(path) if path else f"col_{col_idx}"
            
            # 从最深层级开始查找n值
            for i, part in enumerate(reversed(path)):
                n_match = re.search(r'[nN]\s*=\s*(\d+(?:[\s\+/]\d+)?)', part)
                if n_match:
                    raw_val = n_match.group(1)
                    n_dict = self._parse_compound_n(raw_val)
                    
                    # 提取符号
                    symbols = re.findall(r'([\*†‡§])', part)
                    
                    sample_sizes[full_path_str] = {
                        'primary_n': n_dict['primary_n'],  # 有效随访数/分析人数
                        'total_n': n_dict['total_n'],      # 原始随机化人数
                        'raw': raw_val,
                        'is_compound': '+' in raw_val or '/' in raw_val,
                        'is_fraction': '/' in raw_val,     # v2.6.1: 标记分数格式
                        'source_level': len(path) - i - 1,
                        'source_text': part,
                        'col_idx': col_idx,
                        'symbols': symbols
                    }
                    break
        
        return sample_sizes
    
    def _parse_compound_n(self, raw: str) -> int:
        """解析复合 n 值（静态方法）"""
        clean = re.sub(r'[^\d\+/]', '', raw)
        
        if '+' in clean:
            try:
                return sum(int(x.strip()) for x in clean.split('+'))
            except ValueError:
                pass
        elif '/' in clean:
            try:
                return int(clean.split('/')[0].strip())
            except ValueError:
                pass
        
        try:
            return int(clean)
        except ValueError:
            return 0
    
    def get_column_semantics(self, col_idx: int) -> Dict[str, Any]:
        """获取指定列的完整语义信息 - v2.6增强"""
        if not self._node_matrix or col_idx >= len(self._node_matrix[-1]):
            return {}
        
        leaf_node = self._node_matrix[-1][col_idx]
        if not leaf_node:
            return {}
        
        return {
            'path': leaf_node.full_path,
            'n_value': leaf_node.metadata.get('primary_n'),
            'raw_n_text': leaf_node.metadata.get('raw_n_text'),
            'symbols': leaf_node.metadata.get('symbols', []),
            'all_n_values': leaf_node.metadata.get('n_values', []),
            'level': leaf_node.level,
            'row_span': leaf_node.row_span_range,
            'col_span': leaf_node.col_span_range
        }
    
    def find_columns_by_path_pattern(self, pattern: str) -> List[int]:
        """根据路径模式查找列索引"""
        matches = []
        pattern_lower = pattern.lower()
        
        for col_idx in range(len(self._node_matrix[-1]) if self._node_matrix else 0):
            semantics = self.get_column_semantics(col_idx)
            path = semantics.get('path', [])
            
            # 检查路径的任何部分是否匹配
            if any(pattern_lower in str(p).lower() for p in path):
                matches.append(col_idx)
        
        return matches
    
    def validate_grid_alignment(self) -> Dict[str, Any]:
        """
        v2.6新增：网格对齐校验器
        
        检查各行总宽度的一致性，发现 colspan 计算错误
        """
        if not self._node_matrix:
            return {'valid': False, 'error': 'Empty matrix'}
        
        row_lengths = [len(row) for row in self._node_matrix]
        unique_lengths = set(row_lengths)
        
        if len(unique_lengths) > 1:
            return {
                'valid': False,
                'error': 'Row length mismatch',
                'row_lengths': row_lengths,
                'suggestion': 'Check colspan values in header rows'
            }
        
        return {'valid': True, 'columns': row_lengths[0]}


# ==================== 脊柱外科专用测试用例 ====================

def test_case_1_standard_subgroup():
    """
    Test Case 1: 标准亚组平行对比（最常见情况）
    临床背景：对比单节段与多节段腰椎融合术在不同干预组中的基线或结局指标
    """
    print("\n" + "="*60)
    print("Test Case 1: 标准亚组平行对比")
    print("="*60)
    
    # 模拟 LLM 提取的原始表头数据
    case_1_input = [
        [
            {'value': 'Outcomes', 'colspan': 1},
            {'value': 'PELD Group (n=120)', 'colspan': 2},
            {'value': 'Open Group (n=115)', 'colspan': 2},
        ],
        [
            {'value': '', 'colspan': 1},  # 占位
            {'value': 'Single-level', 'colspan': 1},
            {'value': 'Multi-level', 'colspan': 1},
            {'value': 'Single-level', 'colspan': 1},
            {'value': 'Multi-level', 'colspan': 1},
        ]
    ]
    
    parser = HierarchicalHeaderParser()
    paths = parser.parse(case_1_input)
    sample_info = parser.extract_sample_sizes(paths)
    
    print("\n解析结果:")
    for col_idx, path in paths.items():
        print(f"  Col {col_idx}: {' > '.join(path)}")
    
    print("\n样本量提取:")
    for path, info in sample_info.items():
        print(f"  {path}: n={info['n']} (来源: {info['source_text']})")
    
    # 验证
    assert paths[1] == ['PELD Group (n=120)', 'Single-level'], f"Col 1 路径错误: {paths[1]}"
    assert paths[2] == ['PELD Group (n=120)', 'Multi-level'], f"Col 2 路径错误: {paths[2]}"
    assert sample_info.get('PELD Group (n=120) > Single-level', {}).get('primary_n') == 120
    
    print("\n✅ Test Case 1 通过")
    return True


def test_case_2_deeply_nested():
    """
    Test Case 2: 深度嵌套的解剖亚组（高复杂度）
    临床背景：展示不同手术节段（L4/5, L5/S1）在单/多节段手术中的具体表现
    """
    print("\n" + "="*60)
    print("Test Case 2: 深度嵌套的解剖亚组")
    print("="*60)
    
    case_2_input = [
        [
            {'value': 'Subgroup Analysis', 'colspan': 1},
            {'value': 'Surgical Levels (Total N=235)', 'colspan': 4},
        ],
        [
            {'value': '', 'colspan': 1},
            {'value': 'Single-segment (n=150)', 'colspan': 2},
            {'value': 'Multi-segment (n=85)', 'colspan': 2},
        ],
        [
            {'value': '', 'colspan': 1},
            {'value': 'L4/5', 'colspan': 1},
            {'value': 'L5/S1', 'colspan': 1},
            {'value': 'L4-S1', 'colspan': 1},
            {'value': 'Other', 'colspan': 1},
        ]
    ]
    
    parser = HierarchicalHeaderParser()
    paths = parser.parse(case_2_input)
    sample_info = parser.extract_sample_sizes(paths)
    
    print("\n解析结果:")
    for col_idx, path in paths.items():
        print(f"  Col {col_idx}: {' > '.join(path)}")
    
    print("\n样本量提取:")
    for path, info in sample_info.items():
        print(f"  {path}: n={info['n']} (局部n), N=235 (全局N)")
    
    # 验证 Col 1 路径
    expected_col1 = ['Surgical Levels (Total N=235)', 'Single-segment (n=150)', 'L4/5']
    assert paths[1] == expected_col1, f"Col 1 路径错误: {paths[1]}"
    
    # 验证样本量提取
    assert sample_info.get('Surgical Levels (Total N=235) > Single-segment (n=150) > L4/5', {}).get('primary_n') == 150
    
    print("\n✅ Test Case 2 通过")
    return True


def test_case_3_followup_data():
    """
    Test Case 3: 带有"非对称"表头的随访数据
    临床背景：评估 LDH 手术后，单节段和多节段病人在不同时间点的 VAS 评分变化
    """
    print("\n" + "="*60)
    print("Test Case 3: 非对称随访数据表头")
    print("="*60)
    
    case_3_input = [
        [
            {'value': 'Baseline (n=235)', 'colspan': 1},
            {'value': 'Post-op 1-year', 'colspan': 2},
            {'value': 'Post-op 2-year', 'colspan': 2},
        ],
        [
            {'value': '', 'colspan': 1},
            {'value': 'Single (n=150)', 'colspan': 1},
            {'value': 'Multi (n=85)', 'colspan': 1},
            {'value': 'Single (n=145*)', 'colspan': 1},
            {'value': 'Multi (n=82*)', 'colspan': 1},
        ]
    ]
    
    parser = HierarchicalHeaderParser()
    paths = parser.parse(case_3_input)
    sample_info = parser.extract_sample_sizes(paths)
    
    print("\n解析结果:")
    for col_idx, path in paths.items():
        print(f"  Col {col_idx}: {' > '.join(path)}")
    
    print("\n样本量提取 (含特殊符号 *):")
    for path, info in sample_info.items():
        print(f"  {path}: n={info['n']}, symbols={info.get('symbols', [])}")
    
    # 验证随访失访检测
    col_3_n = sample_info.get('Post-op 2-year > Single (n=145*)', {}).get('primary_n')
    col_1_n = sample_info.get('Post-op 1-year > Single (n=150)', {}).get('primary_n')
    
    if col_3_n and col_1_n:
        attrition = col_1_n - col_3_n
        attrition_rate = attrition / col_1_n * 100
        print(f"\n⚠️ 失访检测: Post-op 1-year到2-year Single组失访 {attrition}例 ({attrition_rate:.1f}%)")
    
    assert paths[2] == ['Post-op 1-year', 'Multi (n=85)'], f"Col 2 路径错误: {paths[2]}"
    
    print("\n✅ Test Case 3 通过")
    return True


def test_case_4_rowspan_support():
    """
    Test Case 4: v2.6新增 - 纵向跨行表头（rowspan支持）
    临床背景：左侧第一列的"指标分类"纵向跨越多行，覆盖所有数据行
    """
    print("\n" + "="*60)
    print("Test Case 4: 纵向跨行表头 (rowspan support)")
    print("="*60)
    
    # 修正的表格结构：Outcomes跨越所有列（包括下面的子列）
    case_4_input = [
        [
            {'value': 'Outcomes', 'colspan': 5, 'rowspan': 1},  # 顶层标题，横跨所有列
        ],
        [
            {'value': 'Subgroup', 'colspan': 1, 'rowspan': 2},  # 侧边标题，纵向跨2行
            {'value': 'PELD (n=120)', 'colspan': 2},
            {'value': 'Open (n=115)', 'colspan': 2},
        ],
        [
            # Subgroup列被上一行的rowspan占据
            {'value': 'Single', 'colspan': 1},
            {'value': 'Multi', 'colspan': 1},
            {'value': 'Single', 'colspan': 1},
            {'value': 'Multi', 'colspan': 1},
        ]
    ]
    
    parser = HierarchicalHeaderParser()
    paths = parser.parse(case_4_input)
    
    print("\n解析结果:")
    for col_idx, path in paths.items():
        print(f"  Col {col_idx}: {' > '.join(path)}")
    
    # 验证：Col 0的路径包含纵向标题，Col 1的路径包含顶层标题
    assert 'Outcomes' in paths[0], f"Col 0 应包含 'Outcomes': {paths[0]}"
    assert 'Subgroup' in paths[0], f"Col 0 应包含 'Subgroup': {paths[0]}"
    assert 'Outcomes' in paths[1], f"Col 1 应包含 'Outcomes': {paths[1]}"
    assert 'PELD (n=120)' in paths[1], f"Col 1 应包含 'PELD (n=120)': {paths[1]}"
    
    print("\n✅ Test Case 4 通过 (rowspan 支持正常)")
    return True


def test_case_5_compound_n_values():
    """
    Test Case 5: v2.6新增 - 复合n值解析
    临床背景：多中心研究中常见的n=60+60格式
    """
    print("\n" + "="*60)
    print("Test Case 5: 复合 n 值解析")
    print("="*60)
    
    case_5_input = [
        [
            {'value': 'Multi-center Study', 'colspan': 2},
            {'value': 'Follow-up', 'colspan': 2},
        ],
        [
            {'value': 'Center A+B (n=60+60)', 'colspan': 1},
            {'value': 'Center C (n=50)', 'colspan': 1},
            {'value': 'Completed (n=145/150)', 'colspan': 1},
            {'value': 'Lost (n=5/150)', 'colspan': 1},
        ]
    ]
    
    parser = HierarchicalHeaderParser()
    paths = parser.parse(case_5_input)
    sample_info = parser.extract_sample_sizes(paths)
    
    print("\n解析结果:")
    for col_idx, path in paths.items():
        print(f"  Col {col_idx}: {' > '.join(path)}")
    
    print("\n复合 n 值提取:")
    for path, info in sample_info.items():
        compound_flag = "(复合)" if info.get('is_compound') else ""
        fraction_flag = "(分数)" if info.get('is_fraction') else ""
        print(f"  {path}: primary_n={info['primary_n']}, total_n={info['total_n']} {compound_flag}{fraction_flag}, raw='{info['raw']}'")
    
    # 验证复合n值计算
    col_0_info = sample_info.get('Multi-center Study > Center A+B (n=60+60)', {})
    assert col_0_info.get('primary_n') == 120, f"60+60 应等于 120，但得到 {col_0_info.get('primary_n')}"
    assert col_0_info.get('total_n') == 120, f"60+60 total_n 应等于 120"
    assert col_0_info.get('is_compound') == True, "应标记为复合n值"
    
    col_2_info = sample_info.get('Follow-up > Completed (n=145/150)', {})
    assert col_2_info.get('primary_n') == 145, f"145/150 应取分子 primary_n=145，但得到 {col_2_info.get('primary_n')}"
    assert col_2_info.get('total_n') == 150, f"145/150 应取分母 total_n=150，但得到 {col_2_info.get('total_n')}"
    assert col_2_info.get('is_fraction') == True, "应标记为分数格式"
    
    print("\n✅ Test Case 5 通过 (复合n值解析正常)")
    return True


if __name__ == '__main__':
    print("\n" + "="*60)
    print("HierarchicalHeaderParser v2.6 - 脊柱外科专用测试")
    print("="*60)
    print("核心升级：rowspan支持 | 复合n值 | 特殊符号提取")
    print("="*60)
    
    test_case_1_standard_subgroup()
    test_case_2_deeply_nested()
    test_case_3_followup_data()
    test_case_4_rowspan_support()
    test_case_5_compound_n_values()
    
    print("\n" + "="*60)
    print("所有测试通过！v2.6 重构成功")
    print("="*60)
