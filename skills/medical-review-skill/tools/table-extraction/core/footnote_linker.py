#!/usr/bin/env python3
"""
脚注关联器 (FootnoteLinker)
处理医学表格中的特殊符号 (*, †, ‡, §, ||, ¶) 并关联到表后备注内容

关键功能：
1. 符号解析 (Signaling)：识别单元格中的特殊字符并将其与数值分离
2. 备注解析 (Footnote Parsing)：将表后的文本行拆解为"符号-内容"对
3. 自动关联 (Linking)：将数值与具体的学术含义挂钩

针对脊柱外科文献优化：
- 支持 *, †, ‡, §, ||, ¶ 标准学术符号
- 模糊匹配（处理OCR误识别）
- LDH领域常识库兜底
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any


class FootnoteType(Enum):
    """脚注类型枚举"""
    STATISTICAL = "statistical"      # 统计显著性，如 * P<0.05
    METHODOLOGICAL = "methodological"  # 方法学备注，如 † 数据来自...
    CLINICAL = "clinical"            # 临床意义，如 ‡ MCID达成
    MISSING_DATA = "missing"         # 缺失数据，如 § n=5失访
    OTHER = "other"                  # 其他


@dataclass
class FootnoteEntry:
    """脚注条目"""
    symbol: str                      # 符号，如 "*", "†"
    content: str                     # 脚注内容
    footnote_type: FootnoteType      # 脚注类型
    parsed_meaning: Dict[str, Any] = field(default_factory=dict)  # 解析后的语义


@dataclass
class ProcessedCell:
    """处理后的单元格数据"""
    original_value: str              # 原始值
    cleaned_value: str               # 清洗后的值（移除符号）
    symbols: List[str]               # 提取的符号列表
    footnotes: List[FootnoteEntry]   # 关联的脚注条目
    numeric_value: Optional[float]   # 转换后的数值（如果适用）
    semantic_tags: List[str] = field(default_factory=list)  # 语义标签


class FootnoteLinker:
    """
    脚注关联器
    
    处理医学表格中的特殊符号，自动关联到表后备注的学术含义
    """
    
    # 标准学术符号及其正则模式
    STANDARD_SYMBOLS = ['*', '†', '‡', '§', '¶', '||', '#', '+']
    
    # OCR常见误识别映射
    OCR_ERROR_MAP = {
        't': '†',      # t 可能被误识别为 †
        'T': '†',
        '+': '†',      # + 可能是 † 的误识别
        '**': '*',     # 双星号简化为单星号
        '++': '†',
        'ss': '§',     # ss 可能被误识别为 §
        'll': '||',    # ll 可能被误识别为 ||
    }
    
    # LDH领域常识库（兜底逻辑）
    LDH_KNOWLEDGE_BASE = {
        '*': {
            'default_meaning': 'P < 0.05 (vs baseline or control)',
            'type': FootnoteType.STATISTICAL,
            'common_patterns': [
                (r'P\s*<\s*0\.05', 'P < 0.05'),
                (r'P\s*<\s*0\.01', 'P < 0.01'),
                (r'statistically\s+significant', '统计学显著'),
            ]
        },
        '†': {
            'default_meaning': 'Methodological note or subgroup analysis',
            'type': FootnoteType.METHODOLOGICAL,
            'common_patterns': [
                (r'post(\s*-\s*)?hoc', '事后分析'),
                (r'subgroup', '亚组分析'),
                (r'per protocol', '符合方案集分析'),
            ]
        },
        '‡': {
            'default_meaning': 'MCID achieved or clinical significance',
            'type': FootnoteType.CLINICAL,
            'common_patterns': [
                (r'MCID', '达到最小临床重要差异'),
                (r'clinically\s+significant', '临床意义显著'),
                (r'success\s+rate', '成功率'),
            ]
        },
        '§': {
            'default_meaning': 'Missing data or lost to follow-up',
            'type': FootnoteType.MISSING_DATA,
            'common_patterns': [
                (r'(?:lost|missing|n=\d+\s+(?:lost|missing))', '失访或缺失数据'),
                (r'attrition', '失访率'),
            ]
        }
    }
    
    def __init__(self, raw_footnotes: List[str], specialty: str = "LDH"):
        """
        初始化脚注关联器
        
        Args:
            raw_footnotes: 表格下方的原始字符串列表
                          例: ["* P < 0.05 vs Baseline", "† n=2 missing"]
            specialty: 专科领域，用于选择常识库 (LDH/General)
        """
        self.specialty = specialty
        self.footnote_map: Dict[str, FootnoteEntry] = {}
        self._parse_footnotes(raw_footnotes)
    
    def _parse_footnotes(self, lines: List[str]):
        """将备注行解析为结构化脚注条目"""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 匹配行首的符号
            match = re.match(r'^\s*([\*\†\‡\§\¶\|\#\+]+)\s*(.*)', line)
            if match:
                symbol, content = match.groups()
                symbol = symbol.strip()
                content = content.strip()
                
                # 确定脚注类型
                footnote_type = self._classify_footnote(content)
                
                # 解析语义
                parsed_meaning = self._parse_semantic(content, footnote_type)
                
                entry = FootnoteEntry(
                    symbol=symbol,
                    content=content,
                    footnote_type=footnote_type,
                    parsed_meaning=parsed_meaning
                )
                
                self.footnote_map[symbol] = entry
    
    def _classify_footnote(self, content: str) -> FootnoteType:
        """根据内容分类脚注类型"""
        content_lower = content.lower()
        
        # 统计显著性关键词
        if any(kw in content_lower for kw in ['p <', 'p=', 'significant', 'vs']):
            return FootnoteType.STATISTICAL
        
        # 缺失数据关键词
        if any(kw in content_lower for kw in ['missing', 'lost', 'attrition', 'n=', 'withdrawn']):
            return FootnoteType.MISSING_DATA
        
        # 临床意义关键词
        if any(kw in content_lower for kw in ['mcid', 'clinical', 'success', 'responder']):
            return FootnoteType.CLINICAL
        
        # 方法学关键词
        if any(kw in content_lower for kw in ['post hoc', 'subgroup', 'per protocol', 'itt']):
            return FootnoteType.METHODOLOGICAL
        
        return FootnoteType.OTHER
    
    def _parse_semantic(self, content: str, footnote_type: FootnoteType) -> Dict[str, Any]:
        """解析脚注的语义信息"""
        parsed = {'original': content}
        content_lower = content.lower()
        
        if footnote_type == FootnoteType.STATISTICAL:
            # 提取P值
            p_match = re.search(r'P\s*[<>=]\s*(0?\.\d+)', content, re.IGNORECASE)
            if p_match:
                parsed['p_value'] = float(p_match.group(1))
            
            # 提取对照对象
            vs_match = re.search(r'vs\.?\s*(\w+)', content, re.IGNORECASE)
            if vs_match:
                parsed['comparison_group'] = vs_match.group(1)
            
            # 判断vs baseline还是vs control
            if 'baseline' in content_lower:
                parsed['comparison_type'] = 'vs_baseline'
            elif any(kw in content_lower for kw in ['control', 'placebo', 'sham']):
                parsed['comparison_type'] = 'vs_control'
        
        elif footnote_type == FootnoteType.MISSING_DATA:
            # 提取缺失数量
            n_match = re.search(r'[nN]\s*=\s*(\d+)', content)
            if n_match:
                parsed['missing_n'] = int(n_match.group(1))
        
        elif footnote_type == FootnoteType.CLINICAL:
            # 提取MCID阈值
            mcid_match = re.search(r'MCID\s*(?:[=≥>]\s*)?(\d+(?:\.\d+)?)', content, re.IGNORECASE)
            if mcid_match:
                parsed['mcid_threshold'] = float(mcid_match.group(1))
        
        return parsed
    
    def link_cell(self, raw_value: str) -> ProcessedCell:
        """
        处理单元格：分离符号并关联内容
        
        Args:
            raw_value: 单元格原始值，如 "3.22*†" 或 "85.2±3.1*"
        
        Returns:
            ProcessedCell: 处理后的单元格数据
        """
        if not isinstance(raw_value, str) or not raw_value:
            return ProcessedCell(
                original_value=str(raw_value),
                cleaned_value=str(raw_value),
                symbols=[],
                footnotes=[],
                numeric_value=None
            )
        
        original = raw_value.strip()
        
        # 1. 提取末尾符号
        symbols = self._extract_symbols(original)
        
        # 2. 清洗数值部分
        cleaned = self._clean_value(original, symbols)
        
        # 3. 尝试数值转换
        numeric_value = self._convert_to_numeric(cleaned)
        
        # 4. 关联脚注
        footnotes = []
        semantic_tags = []
        
        for symbol in symbols:
            # 先查已解析的脚注
            if symbol in self.footnote_map:
                footnotes.append(self.footnote_map[symbol])
                semantic_tags.append(f"[{symbol}] {self.footnote_map[symbol].content}")
            else:
                # 使用常识库兜底
                if symbol in self.LDH_KNOWLEDGE_BASE and self.specialty == "LDH":
                    kb_entry = self.LDH_KNOWLEDGE_BASE[symbol]
                    footnote = FootnoteEntry(
                        symbol=symbol,
                        content=kb_entry['default_meaning'],
                        footnote_type=kb_entry['type'],
                        parsed_meaning={'source': 'knowledge_base', 'note': '默认含义'}
                    )
                    footnotes.append(footnote)
                    semantic_tags.append(f"[{symbol}] {kb_entry['default_meaning']} (默认)")
        
        return ProcessedCell(
            original_value=original,
            cleaned_value=cleaned,
            symbols=symbols,
            footnotes=footnotes,
            numeric_value=numeric_value,
            semantic_tags=semantic_tags
        )
    
    def _extract_symbols(self, value: str) -> List[str]:
        """提取单元格末尾的符号"""
        symbols = []
        remaining = value.strip()
        
        # 循环提取末尾符号
        while remaining:
            # 尝试匹配多字符符号（如 ||）
            matched = False
            for multi_symbol in ['||']:
                if remaining.endswith(multi_symbol):
                    symbols.insert(0, multi_symbol)
                    remaining = remaining[:-len(multi_symbol)].strip()
                    matched = True
                    break
            
            if matched:
                continue
            
            # 尝试匹配单字符符号
            last_char = remaining[-1]
            if last_char in self.STANDARD_SYMBOLS:
                symbols.insert(0, last_char)
                remaining = remaining[:-1].strip()
            elif last_char in self.OCR_ERROR_MAP:
                # OCR误识别纠正
                corrected = self.OCR_ERROR_MAP[last_char]
                symbols.insert(0, corrected)
                remaining = remaining[:-1].strip()
            else:
                break
        
        return symbols
    
    def _clean_value(self, value: str, symbols: List[str]) -> str:
        """清洗数值，移除符号"""
        cleaned = value.strip()
        for symbol in symbols:
            cleaned = cleaned.replace(symbol, '').strip()
        return cleaned
    
    def _convert_to_numeric(self, value: str) -> Optional[float]:
        """将清洗后的值转换为数值"""
        if not value:
            return None
        
        # 处理 ± 符号，取均值部分
        if '±' in value:
            value = value.split('±')[0].strip()
        
        # 处理范围格式 (如 "10-20")，取中值
        range_match = re.match(r'^(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)$', value)
        if range_match:
            low, high = float(range_match.group(1)), float(range_match.group(2))
            return (low + high) / 2
        
        # 移除非数字字符（保留小数点）
        clean_str = re.sub(r'[^\d\.]', '', value)
        
        try:
            if '.' in clean_str:
                return float(clean_str)
            else:
                return float(clean_str) if clean_str else None
        except ValueError:
            return None
    
    def get_missing_data_summary(self) -> Dict[str, Any]:
        """获取缺失数据摘要（用于失访率计算）"""
        missing_entries = [
            entry for entry in self.footnote_map.values()
            if entry.footnote_type == FootnoteType.MISSING_DATA
        ]
        
        total_missing = sum(
            entry.parsed_meaning.get('missing_n', 0)
            for entry in missing_entries
        )
        
        return {
            'total_missing': total_missing,
            'entries': missing_entries,
            'has_attrition_note': len(missing_entries) > 0
        }
    
    def get_statistical_significance_summary(self) -> Dict[str, Any]:
        """获取统计显著性摘要"""
        stat_entries = [
            entry for entry in self.footnote_map.values()
            if entry.footnote_type == FootnoteType.STATISTICAL
        ]
        
        return {
            'significance_levels': [
                {
                    'symbol': e.symbol,
                    'p_value': e.parsed_meaning.get('p_value'),
                    'comparison': e.parsed_meaning.get('comparison_type')
                }
                for e in stat_entries
            ],
            'has_multiple_comparisons': len(stat_entries) > 1
        }


# ==================== 测试用例 ====================

def test_basic_footnote_linking():
    """测试基本脚注关联"""
    print("\n" + "="*60)
    print("Test: 基本脚注关联")
    print("="*60)
    
    footnotes = [
        "* P < 0.05 compared with the Single-level group",
        "† Denotes values obtained at the 2-year final follow-up",
        "‡ MCID achieved by >80% of patients",
        "§ n=5 lost to follow-up"
    ]
    
    linker = FootnoteLinker(footnotes, specialty="LDH")
    
    # 测试单元格处理
    test_cells = [
        "3.22*",
        "85.2±3.1*†",
        "45.0‡",
        "120§",
        "Normal value"  # 无符号
    ]
    
    print("\n单元格处理结果:")
    for cell in test_cells:
        result = linker.link_cell(cell)
        print(f"\n  原始值: '{result.original_value}'")
        print(f"  清洗值: '{result.cleaned_value}'")
        print(f"  提取符号: {result.symbols}")
        print(f"  数值转换: {result.numeric_value}")
        print(f"  语义标签: {result.semantic_tags}")
    
    # 验证
    result = linker.link_cell("3.22*")
    assert result.symbols == ['*'], f"符号提取错误: {result.symbols}"
    assert result.numeric_value == 3.22, f"数值转换错误: {result.numeric_value}"
    
    print("\n✅ 基本脚注关联测试通过")
    return True


def test_ocr_error_correction():
    """测试OCR误识别纠正"""
    print("\n" + "="*60)
    print("Test: OCR误识别纠正")
    print("="*60)
    
    footnotes = [
        "† P < 0.01 vs control group"
    ]
    
    linker = FootnoteLinker(footnotes, specialty="LDH")
    
    # 模拟OCR错误
    test_cases = [
        ("3.22t", "t → †"),      # t 被误识别为 †
        ("45.0+", "+ → †"),      # + 可能是 †
    ]
    
    print("\nOCR纠错测试:")
    for cell, expected in test_cases:
        result = linker.link_cell(cell)
        print(f"  '{cell}' ({expected}): 符号={result.symbols}")
    
    result = linker.link_cell("3.22t")
    assert '†' in result.symbols, f"OCR纠错失败: {result.symbols}"
    
    print("\n✅ OCR误识别纠正测试通过")
    return True


def test_knowledge_base_fallback():
    """测试常识库兜底"""
    print("\n" + "="*60)
    print("Test: 常识库兜底")
    print("="*60)
    
    # 不传入脚注，使用常识库兜底
    linker = FootnoteLinker([], specialty="LDH")
    
    result = linker.link_cell("3.22*")
    
    print(f"\n无显式脚注时的处理:")
    print(f"  原始值: '{result.original_value}'")
    print(f"  符号: {result.symbols}")
    print(f"  语义标签: {result.semantic_tags}")
    
    assert len(result.semantic_tags) > 0, "常识库兜底失败"
    assert 'P < 0.05' in str(result.semantic_tags), "常识库内容错误"
    
    print("\n✅ 常识库兜底测试通过")
    return True


def test_missing_data_detection():
    """测试缺失数据检测"""
    print("\n" + "="*60)
    print("Test: 缺失数据检测")
    print("="*60)
    
    footnotes = [
        "§ n=8 lost to follow-up at 1-year",
        "|| n=3 withdrew due to adverse events"
    ]
    
    linker = FootnoteLinker(footnotes, specialty="LDH")
    
    summary = linker.get_missing_data_summary()
    
    print(f"\n缺失数据摘要:")
    print(f"  总失访数: {summary['total_missing']}")
    print(f"  有缺失数据备注: {summary['has_attrition_note']}")
    
    for entry in summary['entries']:
        print(f"  - [{entry.symbol}] {entry.content}")
        print(f"    解析: n={entry.parsed_meaning.get('missing_n')}")
    
    assert summary['total_missing'] == 11, f"失访计算错误: {summary['total_missing']}"
    
    print("\n✅ 缺失数据检测测试通过")
    return True


def test_spine_surgery_context():
    """测试脊柱外科专用场景"""
    print("\n" + "="*60)
    print("Test: 脊柱外科专用场景")
    print("="*60)
    
    # LDH文献常见的脚注
    footnotes = [
        "* P < 0.05 vs baseline",
        "† Post-hoc analysis of single-level subgroup",
        "‡ MCID (≥12 points ODI improvement) achieved"
    ]
    
    linker = FootnoteLinker(footnotes, specialty="LDH")
    
    # 模拟VAS评分表格数据
    test_cases = [
        ("7.2±1.3*", "基线后显著改善"),
        ("25.3*†", "亚组分析显著"),
        ("12.5‡", "达到MCID")
    ]
    
    print("\n脊柱外科场景测试:")
    for cell, desc in test_cases:
        result = linker.link_cell(cell)
        print(f"\n  {desc}:")
        print(f"    原始值: '{cell}'")
        print(f"    清洗值: '{result.cleaned_value}'")
        print(f"    符号: {result.symbols}")
        for fn in result.footnotes:
            print(f"    脚注类型: {fn.footnote_type.value}")
            print(f"    解析: {fn.parsed_meaning}")
    
    print("\n✅ 脊柱外科专用场景测试通过")
    return True


if __name__ == '__main__':
    print("\n" + "="*60)
    print("FootnoteLinker - 脚注关联器测试")
    print("="*60)
    
    test_basic_footnote_linking()
    test_ocr_error_correction()
    test_knowledge_base_fallback()
    test_missing_data_detection()
    test_spine_surgery_context()
    
    print("\n" + "="*60)
    print("所有测试通过！")
    print("="*60)
