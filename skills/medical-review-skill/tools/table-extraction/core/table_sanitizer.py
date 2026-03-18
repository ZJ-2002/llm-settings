#!/usr/bin/env python3
"""
表格数据预处理器 (TableSanitizer) - v2.6 增强版
整合：多级表头解析、脚注关联、临床边界检查、MCID评估、尺度混淆检测

v2.6 核心升级：
1. MCID（最小临床意义差异）检测 - 临床意义 vs 统计学意义
2. 尺度混淆自动识别 - VAS 0-10 vs 0-100 自动检测与标准化
3. 统计语义识别 - 区分 SD/SE/CI/IQR
4. P值精度保留 - 保留 <, > 等不等号

设计目标：
1. 从"原始提取结果"到"高质量分析数据"的闭环
2. 作为主程序中 DualTrackExtractor 与 EvidenceSynthesis 之间的关键层
3. 确保进入综述的所有数据都经过学术语境的洗礼

针对脊柱外科（LDH）优化：
- 脊柱外科专用临床边界常数
- 解剖参数熔断器（椎管径线、黄韧带厚度等）
- VAS/ODI等核心指标的智能识别与尺度标准化
- MCID达成率自动评估

作者：AI Assistant (基于专业评审反馈)
版本：v2.6 (2026-03-13)
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

# 导入核心模块
try:
    from header_parser import HierarchicalHeaderParser, HeaderNode
    from footnote_linker import FootnoteLinker, ProcessedCell, FootnoteType
except ImportError:
    # 相对导入支持
    from .header_parser import HierarchicalHeaderParser, HeaderNode
    from .footnote_linker import FootnoteLinker, ProcessedCell, FootnoteType


class StatType(Enum):
    """统计指标类型"""
    MEAN_SD = "mean_sd"           # 均值±标准差
    MEAN_SE = "mean_se"           # 均值±标准误
    MEAN_CI = "mean_ci"           # 均值 (95%CI)
    MEDIAN_IQR = "median_iqr"     # 中位数 (IQR)
    MEDIAN_RANGE = "median_range" # 中位数 (范围)
    POINT = "point"               # 纯数值
    P_VALUE = "p_value"           # P值
    UNKNOWN = "unknown"


@dataclass
class ClinicalBoundary:
    """临床边界定义"""
    name: str
    min_val: float
    max_val: float
    unit: str
    severity: str = "critical"  # critical/warning
    description: str = ""
    # v2.6新增: 尺度信息
    scale_factor: float = 1.0   # 缩放因子（如100mm -> 10cm，factor=10）
    alternative_scales: List[Tuple[float, float]] = field(default_factory=list)  # 替代尺度 [(min, max), ...]


@dataclass
class NumericInsight:
    """数值深度洞察 - v2.6新增"""
    value: Optional[float] = None
    dispersion: Optional[float] = None
    operator: str = "="                    # <, >, <=, >=
    stat_type: StatType = StatType.UNKNOWN
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    is_scaled: bool = False                # 是否经过尺度转换
    original_value: Optional[float] = None # 转换前的原始值
    raw_context: str = ""


@dataclass
class SanitizedCell:
    """清洗后的单元格数据 - v2.6增强"""
    # 原始信息
    original_value: str
    row_idx: int
    col_idx: int
    
    # 清洗后信息
    cleaned_value: Any          # 转换为 float/int/str 后的值
    is_numeric: bool
    
    # v2.6新增: 统计语义
    numeric_insight: Optional[NumericInsight] = None
    stat_type: StatType = StatType.UNKNOWN
    
    # 语义信息
    column_path: List[str] = field(default_factory=list)      # 表头语义路径
    row_label: str = ""              # 行标签（通常是第一列的指标名称）
    
    # 脚注信息
    footnotes: List[str] = field(default_factory=list)        # 关联的脚注内容
    footnote_types: List[str] = field(default_factory=list)   # 脚注类型
    
    # 样本量信息
    sample_size: Optional[int] = None  # 该列对应的样本量 n
    
    # 边界检查
    is_valid: bool = True
    boundary_issues: List[str] = field(default_factory=list)  # 发现的问题描述
    
    # v2.6新增: MCID评估
    mcid_threshold: Optional[float] = None
    mcid_achievable: bool = False      # 该指标是否有MCID定义
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SanitizationReport:
    """清洗报告 - v2.6增强"""
    paper_id: str
    table_id: str
    timestamp: str
    
    # 统计
    total_cells: int
    numeric_cells: int
    cells_with_footnotes: int
    invalid_cells: int
    
    # v2.6新增: 尺度转换统计
    scaled_cells: int                  # 经过尺度转换的单元格数
    scale_warnings: List[str]          # 尺度混淆警告
    
    # 问题汇总
    boundary_violations: List[Dict]
    footnote_summary: Dict[str, int]
    sample_size_info: Dict[str, Any]
    
    # 数据质量
    quality_score: float  # 0-1
    
    # 建议
    recommendations: List[str]
    
    # v2.6新增: 统计语义统计（带默认值，必须放在最后）
    stat_type_distribution: Dict[str, int] = field(default_factory=dict)
    
    # v2.6新增: MCID相关建议
    mcid_recommendations: List[str] = field(default_factory=list)


class TableSanitizer:
    """
    医学表格数据预处理器 (Sanitizer) - v2.6增强版
    
    整合模块：
    - HierarchicalHeaderParser: 多级表头解析
    - FootnoteLinker: 脚注关联
    - ClinicalBoundaryChecker: 临床边界检查
    - ScaleDetector: 尺度混淆检测（v2.6新增）
    - StatisticalSemanticRecognizer: 统计语义识别（v2.6新增）
    """
    
    # 脊柱外科（LDH）临床边界常数 - v2.6增强
    SPINE_BOUNDARIES = {
        # 疼痛评分 - v2.6: 支持多尺度
        "VAS": ClinicalBoundary(
            "VAS", 0, 10, "score", "critical", "视觉模拟评分",
            scale_factor=10.0,
            alternative_scales=[(0, 100)]  # 支持 0-100mm 尺度
        ),
        "NRS": ClinicalBoundary(
            "NRS", 0, 10, "score", "critical", "数字评分量表",
            alternative_scales=[(0, 100)]
        ),
        
        # 功能障碍指数
        "ODI": ClinicalBoundary("ODI", 0, 100, "%", "critical", "Oswestry功能障碍指数"),
        "JOA": ClinicalBoundary("JOA", 0, 29, "score", "critical", "日本骨科学会评分"),
        
        # 解剖参数
        "Spinal_Canal_Diameter": ClinicalBoundary("Spinal_Canal_Diameter", 5, 30, "mm", "critical", "椎管直径"),
        "Ligamentum_Flavum": ClinicalBoundary("Ligamentum_Flavum", 1, 8, "mm", "warning", "黄韧带厚度"),
        "Disc_Height": ClinicalBoundary("Disc_Height", 3, 20, "mm", "warning", "椎间盘高度"),
        "Canal_Area": ClinicalBoundary("Canal_Area", 50, 300, "mm²", "warning", "椎管面积"),
        
        # 统计学
        "P_value": ClinicalBoundary("P_value", 0, 1, "", "critical", "P值"),
        "Alpha": ClinicalBoundary("Alpha", 0, 1, "", "critical", "显著性水平"),
        
        # 人口统计学
        "Age": ClinicalBoundary("Age", 0, 120, "years", "warning", "年龄"),
        "BMI": ClinicalBoundary("BMI", 10, 60, "kg/m²", "warning", "体重指数"),
        
        # 手术参数
        "Blood_Loss": ClinicalBoundary("Blood_Loss", 0, 5000, "mL", "warning", "术中出血"),
        "Operative_Time": ClinicalBoundary("Operative_Time", 0, 600, "min", "warning", "手术时间"),
    }
    
    # 脊柱外科 MCID 阈值 - v2.6新增
    MCID_THRESHOLDS = {
        "VAS": 1.5,           # VAS 改善需 > 1.5 分
        "VAS_BACK": 1.5,
        "VAS_LEG": 2.0,       # 腿痛 VAS 的 MCID 更高
        "NRS": 1.5,
        "ODI": 12.8,          # ODI 改善需 > 12.8%
        "JOA": 2.5,           # JOA 改善
    }
    
    # 指标名称映射（用于智能识别）
    METRIC_ALIASES = {
        "VAS": ["vas", "visual analog", "visual analogue", "leg pain", "back pain", "腿痛", "腰痛", "疼痛"],
        "VAS_LEG": ["leg pain", "lower limb pain", "sciatica", "腿痛", "下肢痛", "坐骨神经痛"],
        "VAS_BACK": ["back pain", "low back pain", "腰痛", "下腰痛"],
        "ODI": ["odi", "oswestry", "disability index", "功能障碍"],
        "JOA": ["joa", "japanese orthopaedic", "日本骨科"],
        "Spinal_Canal_Diameter": ["canal diameter", "spinal canal", "椎管直径", "椎管径", "椎管矢状径"],
        "Ligamentum_Flavum": ["ligamentum flavum", "yellow ligament", "黄韧带", "lf thickness"],
        "Age": ["age", "years", "年龄", "岁数"],
        "BMI": ["bmi", "body mass index", "体重指数", "体质指数"],
    }
    
    # v2.6: 统计类型关键词映射
    STAT_TYPE_KEYWORDS = {
        StatType.MEAN_SD: ["sd", "standard deviation", "std dev", "标准差"],
        StatType.MEAN_SE: ["se", "standard error", "sem", "标准误"],
        StatType.MEAN_CI: ["ci", "confidence interval", "95% ci", "95%ci", "置信区间"],
        StatType.MEDIAN_IQR: ["iqr", "interquartile", "四分位"],
    }
    
    def __init__(self, specialty: str = "LDH"):
        """
        初始化预处理器
        
        Args:
            specialty: 专科领域 (LDH/General)
        """
        self.specialty = specialty
        self.header_parser = HierarchicalHeaderParser()
        
        # 选择边界配置
        if specialty == "LDH":
            self.boundaries = self.SPINE_BOUNDARIES
            self.mcid_thresholds = self.MCID_THRESHOLDS
        else:
            self.boundaries = {}
            self.mcid_thresholds = {}
    
    def sanitize(self, 
                 table_data: Dict[str, Any], 
                 raw_footnotes: List[str] = None,
                 header_row_count: int = 2) -> Tuple[List[List[SanitizedCell]], SanitizationReport]:
        """
        主处理函数 - v2.6增强版
        
        Args:
            table_data: LLM提取的原始表格数据
                       格式: {'rows': [[{'value': '...'}, ...], ...], 'title': '...'}
            raw_footnotes: 表格下方的原始脚注文本列表
            header_row_count: 表头行数
        
        Returns:
            (清洗后的表格, 清洗报告)
        """
        raw_footnotes = raw_footnotes or []
        
        # 1. 初始化组件
        footnote_linker = FootnoteLinker(raw_footnotes, specialty=self.specialty)
        
        # 2. 解析多级表头
        all_rows = table_data.get('rows', [])
        header_rows = all_rows[:header_row_count] if len(all_rows) >= header_row_count else all_rows
        data_rows = all_rows[header_row_count:]
        
        col_paths = self.header_parser.parse(header_rows)
        sample_info = self.header_parser.extract_sample_sizes(col_paths)
        
        # 3. 逐行清洗数据
        sanitized_table = []
        boundary_violations = []
        footnote_type_counts = {}
        scaled_cells_count = 0
        scale_warnings = []
        stat_type_distribution = {}
        
        for row_idx, row in enumerate(data_rows):
            sanitized_row = []
            
            # 提取行标签（通常第一列是指标名称）
            row_label = self._extract_row_label(row)
            
            for col_idx, cell in enumerate(row):
                raw_val = cell.get('value', '') if isinstance(cell, dict) else str(cell)
                
                # A. 脚注剥离与关联
                processed = footnote_linker.link_cell(raw_val)
                
                # 统计脚注类型
                for fn in processed.footnotes:
                    fn_type = fn.footnote_type.value
                    footnote_type_counts[fn_type] = footnote_type_counts.get(fn_type, 0) + 1
                
                # B. v2.6: 增强数值识别（含统计语义）
                numeric_insight = self._recognize_numeric_enhanced(
                    processed.cleaned_value, 
                    row_label,
                    col_paths.get(col_idx, [])
                )
                is_numeric = numeric_insight is not None and numeric_insight.value is not None
                
                # C. v2.6: 尺度混淆检测与自动对齐
                scale_issue = None
                if is_numeric:
                    scale_issue = self._detect_and_fix_scale(
                        numeric_insight, row_label, col_paths.get(col_idx, [])
                    )
                    if numeric_insight.is_scaled:
                        scaled_cells_count += 1
                    if scale_issue:
                        scale_warnings.append(scale_issue)
                
                # D. 临床边界检查（使用可能已缩放的值）
                valid, issues = self._check_clinical_boundary(row_label, numeric_insight)
                
                if issues:
                    boundary_violations.append({
                        'row': row_idx,
                        'col': col_idx,
                        'label': row_label,
                        'value': numeric_insight.value if numeric_insight else None,
                        'original_value': numeric_insight.original_value if numeric_insight else None,
                        'issues': issues
                    })
                
                # E. v2.6: 统计类型统计
                if numeric_insight and numeric_insight.stat_type:
                    stat_type_str = numeric_insight.stat_type.value
                    stat_type_distribution[stat_type_str] = stat_type_distribution.get(stat_type_str, 0) + 1
                
                # F. v2.6: MCID 信息获取
                mcid_threshold = self._get_mcid_threshold(row_label)
                
                # G. 封装清洗后的对象
                sanitized_cell = SanitizedCell(
                    original_value=raw_val,
                    row_idx=row_idx,
                    col_idx=col_idx,
                    cleaned_value=numeric_insight.value if is_numeric else processed.cleaned_value,
                    is_numeric=is_numeric,
                    numeric_insight=numeric_insight,
                    stat_type=numeric_insight.stat_type if numeric_insight else StatType.UNKNOWN,
                    column_path=col_paths.get(col_idx, []),
                    row_label=row_label,
                    footnotes=[fn.content for fn in processed.footnotes],
                    footnote_types=[fn.footnote_type.value for fn in processed.footnotes],
                    sample_size=self._match_sample_size(col_paths.get(col_idx, []), sample_info),
                    is_valid=valid,
                    boundary_issues=issues,
                    mcid_threshold=mcid_threshold,
                    mcid_achievable=mcid_threshold is not None,
                    metadata={
                        'symbols': processed.symbols,
                        'footnote_details': [
                            {'symbol': fn.symbol, 'type': fn.footnote_type.value, 'parsed': fn.parsed_meaning}
                            for fn in processed.footnotes
                        ],
                        'scale_info': {
                            'is_scaled': numeric_insight.is_scaled if numeric_insight else False,
                            'original_value': numeric_insight.original_value if numeric_insight else None,
                            'scale_factor': 10.0 if (numeric_insight and numeric_insight.is_scaled) else 1.0
                        }
                    }
                )
                sanitized_row.append(sanitized_cell)
            
            sanitized_table.append(sanitized_row)
        
        # 4. 生成报告
        report = self._generate_report(
            table_data.get('title', 'Unknown'),
            sanitized_table,
            boundary_violations,
            footnote_type_counts,
            sample_info,
            footnote_linker,
            scaled_cells_count,
            scale_warnings,
            stat_type_distribution
        )
        
        return sanitized_table, report
    
    def _extract_row_label(self, row: List[Any]) -> str:
        """提取行标签（第一列的文本）"""
        if not row:
            return ""
        
        first_cell = row[0]
        if isinstance(first_cell, dict):
            return str(first_cell.get('value', '')).strip()
        return str(first_cell).strip()
    
    def _recognize_numeric_enhanced(
        self, 
        value: str, 
        row_label: str = "",
        col_path: List[str] = []
    ) -> Optional[NumericInsight]:
        """
        v2.6: 增强型数值识别 - 支持统计语义
        
        识别：
        1. 算子（<, >, ≤, ≥）
        2. 统计类型（Mean±SD, Mean(SE), Median(IQR)等）
        3. 置信区间
        """
        if not value or not isinstance(value, str):
            return None
        
        text = value.strip()
        if not text:
            return None
        
        insight = NumericInsight(raw_context=text)
        
        # 1. 算子提取
        text = self._extract_operator(text, insight)
        
        # 2. 统计模式识别
        self._recognize_statistical_pattern(text, insight, row_label, col_path)
        
        return insight
    
    def _extract_operator(self, text: str, insight: NumericInsight) -> str:
        """提取不等号算子"""
        op_match = re.match(r'^([<>≤≥=]{1,2})\s*', text)
        if op_match:
            op = op_match.group(1)
            insight.operator = op.replace("≤", "<=").replace("≥", ">=")
            text = text[len(op_match.group(0)):]
        return text
    
    def _recognize_statistical_pattern(
        self, 
        text: str, 
        insight: NumericInsight,
        row_label: str = "",
        col_path: List[str] = []
    ):
        """识别统计包装模式"""
        
        # 模式 A: Mean ± SD
        if '±' in text:
            parts = text.split('±')
            if len(parts) == 2:
                insight.value = self._to_float(parts[0])
                insight.dispersion = self._to_float(parts[1])
                insight.stat_type = self._infer_dispersion_type(row_label, col_path)
                return
        
        # 模式 B: Mean (SD/SE/CI)
        paren_match = re.match(r'^([\d\.]+)\s*\(([^)]+)\)', text)
        if paren_match:
            main_val = paren_match.group(1)
            inside = paren_match.group(2)
            insight.value = self._to_float(main_val)
            
            # 判断括号内内容
            if '-' in inside or '–' in inside:
                # CI 或范围
                range_parts = re.split(r'[-–]', inside)
                if len(range_parts) == 2:
                    low = self._to_float(range_parts[0])
                    high = self._to_float(range_parts[1])
                    if low is not None and high is not None:
                        insight.ci_lower = low
                        insight.ci_upper = high
                        insight.dispersion = (high - low) / 2
                        insight.stat_type = StatType.MEAN_CI
            else:
                # SD 或 SE
                insight.dispersion = self._to_float(inside)
                insight.stat_type = self._infer_dispersion_type(row_label, col_path, default=StatType.UNKNOWN)
            return
        
        # 模式 C: 纯数字
        insight.value = self._to_float(text)
        insight.stat_type = StatType.POINT
    
    def _infer_dispersion_type(
        self, 
        row_label: str, 
        col_path: List[str],
        default: StatType = StatType.MEAN_SD
    ) -> StatType:
        """根据上下文推断离散指标类型（SD vs SE）"""
        context = (row_label + " " + " ".join(col_path)).upper()
        
        for stat_type, keywords in self.STAT_TYPE_KEYWORDS.items():
            if any(kw.upper() in context for kw in keywords):
                return stat_type
        
        return default
    
    def _to_float(self, s: str) -> Optional[float]:
        """安全转换为浮点数"""
        if s is None:
            return None
        try:
            clean = re.sub(r'[^\d\.\-]', '', str(s))
            return float(clean) if clean else None
        except (ValueError, TypeError):
            return None
    
    def _detect_and_fix_scale(
        self, 
        insight: NumericInsight, 
        row_label: str,
        col_path: List[str]
    ) -> Optional[str]:
        """
        v2.6: 尺度混淆检测与自动修正
        
        检测 VAS 等指标是否使用了 0-100 尺度而非 0-10
        如果是，自动转换为 0-10 并标记
        """
        if insight.value is None:
            return None
        
        # 识别指标类型
        metric_type = self._identify_metric_type(row_label)
        
        # 检查是否需要缩放
        boundary = self.boundaries.get(metric_type)
        if not boundary or not boundary.alternative_scales:
            return None
        
        # 检查是否在替代尺度范围内
        for alt_min, alt_max in boundary.alternative_scales:
            if alt_min <= insight.value <= alt_max:
                # 在替代尺度范围内，需要转换
                if insight.value > boundary.max_val * 1.5:  # 明显大于标准最大值
                    insight.original_value = insight.value
                    insight.value = insight.value / boundary.scale_factor
                    if insight.dispersion:
                        insight.dispersion = insight.dispersion / boundary.scale_factor
                    insight.is_scaled = True
                    
                    return (
                        f"检测到尺度混淆: {metric_type} 值 {insight.original_value} "
                        f"可能为 0-{int(alt_max)} 尺度，已自动转换为 {insight.value:.1f} (0-10)"
                    )
        
        return None
    
    def _check_clinical_boundary(
        self, 
        label: str, 
        insight: Optional[NumericInsight]
    ) -> Tuple[bool, List[str]]:
        """
        v2.6: 临床边界检查（支持已缩放的值）
        """
        issues = []
        
        if insight is None or insight.value is None:
            return True, issues
        
        # 识别指标类型
        metric_type = self._identify_metric_type(label)
        
        if not metric_type:
            return True, issues
        
        boundary = self.boundaries.get(metric_type)
        if not boundary:
            return True, issues
        
        value = insight.value
        
        # 检查边界（使用标准尺度）
        if value < boundary.min_val:
            issues.append(
                f"{boundary.name} 数值 {value:.2f} 低于临床范围 "
                f"({boundary.min_val}-{boundary.max_val} {boundary.unit})"
            )
        elif value > boundary.max_val:
            # v2.6: 如果原始值也超出边界，才报告问题
            if not insight.is_scaled or (insight.original_value and insight.original_value > boundary.max_val):
                issues.append(
                    f"{boundary.name} 数值 {value:.2f} 超出临床范围 "
                    f"({boundary.min_val}-{boundary.max_val} {boundary.unit})"
                    f"{'[已缩放]' if insight.is_scaled else ''}"
                )
        
        return len(issues) == 0, issues
    
    def _identify_metric_type(self, label: str) -> Optional[str]:
        """根据标签识别指标类型"""
        if not label:
            return None
        
        label_lower = label.lower()
        
        for metric_type, aliases in self.METRIC_ALIASES.items():
            if any(alias in label_lower for alias in aliases):
                return metric_type
        
        return None
    
    def _get_mcid_threshold(self, label: str) -> Optional[float]:
        """v2.6: 获取指标的 MCID 阈值"""
        metric_type = self._identify_metric_type(label)
        if not metric_type:
            return None
        return self.mcid_thresholds.get(metric_type)
    
    def _match_sample_size(self, path: List[str], sample_info: Dict) -> Optional[int]:
        """根据路径匹配该单元格对应的样本量 n"""
        path_str = " > ".join(path) if path else ""
        info = sample_info.get(path_str, {})
        return info.get('n')
    
    def _generate_report(self, 
                        table_id: str,
                        sanitized_table: List[List[SanitizedCell]],
                        boundary_violations: List[Dict],
                        footnote_type_counts: Dict[str, int],
                        sample_info: Dict,
                        footnote_linker: FootnoteLinker,
                        scaled_cells: int,
                        scale_warnings: List[str],
                        stat_type_distribution: Dict[str, int]) -> SanitizationReport:
        """v2.6: 生成增强版清洗报告"""
        
        # 统计
        total_cells = sum(len(row) for row in sanitized_table)
        numeric_cells = sum(
            1 for row in sanitized_table for cell in row if cell.is_numeric
        )
        cells_with_footnotes = sum(
            1 for row in sanitized_table for cell in row if cell.footnotes
        )
        invalid_cells = len(boundary_violations)
        
        # 计算质量分数
        if total_cells > 0:
            quality_score = 1.0 - (invalid_cells / total_cells)
        else:
            quality_score = 1.0
        
        # 获取缺失数据信息
        missing_data = footnote_linker.get_missing_data_summary()
        
        # 生成建议
        recommendations = []
        mcid_recommendations = []
        
        if invalid_cells > 0:
            recommendations.append(f"发现 {invalid_cells} 个临床边界违规，请人工核对")
        
        if scaled_cells > 0:
            recommendations.append(f"检测到 {scaled_cells} 个单元格经过尺度转换，请确认转换正确性")
        
        if scale_warnings:
            for warning in scale_warnings[:3]:  # 只显示前3个
                recommendations.append(f"尺度警告: {warning}")
        
        if missing_data['has_attrition_note']:
            recommendations.append(
                f"检测到失访数据: 共 {missing_data['total_missing']} 例，"
                "建议在Meta分析中进行敏感性分析"
            )
        
        if footnote_type_counts.get('statistical', 0) > 3:
            recommendations.append(
                "存在多重比较，建议检查是否已进行P值校正"
            )
        
        if not sample_info:
            recommendations.append("未能提取样本量信息，请检查表头格式")
        
        # v2.6: MCID 相关建议
        mcid_cells = sum(1 for row in sanitized_table for cell in row if cell.mcid_achievable)
        if mcid_cells > 0:
            mcid_recommendations.append(
                f"发现 {mcid_cells} 个具有 MCID 定义的结局指标，"
                "建议在证据综合时评估 MCID 达成率"
            )
        
        # v2.6: 统计类型建议
        if StatType.UNKNOWN.value in stat_type_distribution:
            unknown_count = stat_type_distribution[StatType.UNKNOWN.value]
            if unknown_count > 0:
                recommendations.append(
                    f"有 {unknown_count} 个数值未能识别统计类型（SD/SE/CI），"
                    "建议人工确认以确保 Meta 分析权重计算正确"
                )
        
        return SanitizationReport(
            paper_id="unknown",
            table_id=table_id,
            timestamp=datetime.now().isoformat(),
            total_cells=total_cells,
            numeric_cells=numeric_cells,
            cells_with_footnotes=cells_with_footnotes,
            invalid_cells=invalid_cells,
            scaled_cells=scaled_cells,
            scale_warnings=scale_warnings,
            stat_type_distribution=stat_type_distribution,
            boundary_violations=boundary_violations,
            footnote_summary=footnote_type_counts,
            sample_size_info=sample_info,
            quality_score=round(quality_score, 3),
            recommendations=recommendations,
            mcid_recommendations=mcid_recommendations
        )
    
    def export_to_analysis_format(self, 
                                   sanitized_table: List[List[SanitizedCell]],
                                   report: SanitizationReport) -> Dict[str, Any]:
        """导出为分析格式（供Meta分析使用）- v2.6增强"""
        
        # 转换为DataFrame-like结构
        headers = []
        if sanitized_table and sanitized_table[0]:
            headers = ['Row_Label'] + [
                ' > '.join(cell.column_path[-2:]) if len(cell.column_path) >= 2 
                else cell.column_path[-1] if cell.column_path else f"Col_{cell.col_idx}"
                for cell in sanitized_table[0]
            ]
        
        data = []
        for row in sanitized_table:
            row_data = {'Row_Label': row[0].row_label if row else ''}
            for cell in row:
                col_name = headers[cell.col_idx + 1] if cell.col_idx + 1 < len(headers) else f"Col_{cell.col_idx}"
                
                # v2.6: 包含统计语义信息
                insight_dict = {}
                if cell.numeric_insight:
                    insight_dict = {
                        'value': cell.numeric_insight.value,
                        'dispersion': cell.numeric_insight.dispersion,
                        'operator': cell.numeric_insight.operator,
                        'stat_type': cell.numeric_insight.stat_type.value,
                        'ci_lower': cell.numeric_insight.ci_lower,
                        'ci_upper': cell.numeric_insight.ci_upper,
                        'is_scaled': cell.numeric_insight.is_scaled,
                        'original_value': cell.numeric_insight.original_value
                    }
                
                row_data[col_name] = {
                    'value': cell.cleaned_value,
                    'is_numeric': cell.is_numeric,
                    'n': cell.sample_size,
                    'footnotes': cell.footnotes,
                    'valid': cell.is_valid,
                    # v2.6新增
                    'stat_type': cell.stat_type.value,
                    'numeric_insight': insight_dict,
                    'mcid_threshold': cell.mcid_threshold,
                    'mcid_achievable': cell.mcid_achievable
                }
            data.append(row_data)
        
        return {
            'metadata': {
                'table_id': report.table_id,
                'timestamp': report.timestamp,
                'quality_score': report.quality_score,
                'specialty': self.specialty,
                # v2.6新增
                'scaled_cells': report.scaled_cells,
                'scale_warnings': report.scale_warnings,
                'stat_type_distribution': report.stat_type_distribution
            },
            'headers': headers,
            'data': data,
            'quality_report': {
                'total_cells': report.total_cells,
                'invalid_cells': report.invalid_cells,
                'boundary_violations': report.boundary_violations,
                'recommendations': report.recommendations,
                'mcid_recommendations': report.mcid_recommendations
            }
        }


# ==================== 测试用例 ====================

def test_spine_surgery_table():
    """测试脊柱外科表格清洗 - v2.6增强"""
    print("\n" + "="*70)
    print("Test: 脊柱外科LDH表格清洗 (v2.6)")
    print("="*70)
    
    # 模拟 LLM 提取的表格数据（含尺度混淆）
    table_data = {
        'title': 'Baseline Characteristics',
        'rows': [
            # 表头
            [
                {'value': 'Characteristics'},
                {'value': 'PELD Group (n=120)', 'colspan': 2},
                {'value': 'Open Group (n=115)', 'colspan': 2},
            ],
            [
                {'value': ''},
                {'value': 'Single-level'},
                {'value': 'Multi-level'},
                {'value': 'Single-level'},
                {'value': 'Multi-level'},
            ],
            # 数据行 - 包含尺度混淆测试
            [{'value': 'Age (years)'}, {'value': '55.2±8.3'}, {'value': '58.1±9.2'}, {'value': '54.8±9.1'}, {'value': '57.5±8.8'}],
            [{'value': 'VAS leg pain (0-10)'}, {'value': '7.2±1.3*'}, {'value': '7.5±1.1*'}, {'value': '6.8±1.2*'}, {'value': '7.0±1.4*'}],
            # v2.6: 故意设置 0-100 尺度的 VAS
            [{'value': 'VAS leg pain (wrong scale)'}, {'value': '72±13*'}, {'value': '75±11*'}, {'value': ''}, {'value': ''}],
            [{'value': 'ODI (%)'}, {'value': '45.2±12.3'}, {'value': '48.5±11.8'}, {'value': '44.8±13.1'}, {'value': '47.2±12.5'}],
            # v2.6: SE 而非 SD
            [{'value': 'BMI (kg/m², SE)'}, {'value': '24.5 (1.2)'}, {'value': '25.8 (1.5)'}, {'value': '24.2 (1.1)'}, {'value': '25.5 (1.3)'}],
            # v2.6: 带 CI 的格式
            [{'value': 'Canal Area (mm²)'}, {'value': '185 [165, 205]'}, {'value': '192 [172, 212]'}, {'value': '180 [160, 200]'}, {'value': '188 [168, 208]'}],
            # 故意设置一个异常值用于测试
            [{'value': 'VAS leg pain (invalid)'}, {'value': '12.5*'}, {'value': ''}, {'value': ''}, {'value': ''}],
        ]
    }
    
    footnotes = [
        "* P < 0.05 vs baseline",
        "† Post-hoc analysis",
    ]
    
    sanitizer = TableSanitizer(specialty="LDH")
    cleaned_table, report = sanitizer.sanitize(table_data, footnotes, header_row_count=2)
    
    print(f"\n清洗报告:")
    print(f"  总单元格数: {report.total_cells}")
    print(f"  数值单元格: {report.numeric_cells}")
    print(f"  含脚注单元格: {report.cells_with_footnotes}")
    print(f"  无效单元格: {report.invalid_cells}")
    # v2.6新增
    print(f"  尺度转换单元格: {report.scaled_cells}")
    print(f"  质量评分: {report.quality_score}")
    
    print(f"\n尺度混淆警告:")
    for warning in report.scale_warnings:
        print(f"  ⚠️ {warning}")
    
    print(f"\n统计类型分布:")
    for stat_type, count in report.stat_type_distribution.items():
        print(f"  {stat_type}: {count}")
    
    print(f"\n边界违规详情:")
    for violation in report.boundary_violations:
        print(f"  [{violation['row']},{violation['col']}] {violation['label']}: {violation['value']}")
        for issue in violation['issues']:
            print(f"    🔴 {issue}")
    
    print(f"\n样本量信息:")
    for path, info in report.sample_size_info.items():
        print(f"  {path}: n={info['n']}")
    
    print(f"\n建议:")
    for rec in report.recommendations:
        print(f"  💡 {rec}")
    
    if report.mcid_recommendations:
        print(f"\nMCID 相关建议:")
        for rec in report.mcid_recommendations:
            print(f"  📊 {rec}")
    
    print(f"\n清洗后数据预览（含尺度转换）:")
    for i, row in enumerate(cleaned_table[:4]):
        print(f"\n  第{i}行 ({row[0].row_label}):")
        for cell in row[1:3]:  # 显示第1-2列
            scale_info = ""
            if cell.numeric_insight and cell.numeric_insight.is_scaled:
                scale_info = f" [原值:{cell.numeric_insight.original_value:.1f}]"
            stat_info = f" [{cell.stat_type.value}]" if cell.stat_type != StatType.UNKNOWN else ""
            print(f"    Col {cell.col_idx}: {cell.cleaned_value}{scale_info}{stat_info} (n={cell.sample_size})")
    
    # 验证
    assert report.scaled_cells > 0, "应该检测到尺度混淆并转换"
    assert len(report.stat_type_distribution) > 0, "应该识别统计类型"
    
    print("\n✅ 脊柱外科表格清洗测试通过 (v2.6)")
    return True


def test_mcid_detection():
    """v2.6: 测试 MCID 检测"""
    print("\n" + "="*70)
    print("Test: MCID 阈值检测")
    print("="*70)
    
    sanitizer = TableSanitizer(specialty="LDH")
    
    # 测试 MCID 识别
    test_labels = [
        ("VAS leg pain", 1.5),      # 应该有 MCID
        ("ODI score", 12.8),         # 应该有 MCID
        ("JOA score", 2.5),          # 应该有 MCID
        ("Age (years)", None),       # 无 MCID
        ("BMI", None),               # 无 MCID
    ]
    
    for label, expected_mcid in test_labels:
        mcid = sanitizer._get_mcid_threshold(label)
        status = "✅" if mcid == expected_mcid else "❌"
        print(f"  {status} {label:20s}: MCID={mcid}")
        assert mcid == expected_mcid, f"{label} 的 MCID 应为 {expected_mcid}"
    
    print("\n✅ MCID 检测测试通过")


def test_export_format():
    """测试导出格式 - v2.6增强"""
    print("\n" + "="*70)
    print("Test: 导出分析格式 (v2.6)")
    print("="*70)
    
    table_data = {
        'title': 'Test Table',
        'rows': [
            [
                {'value': 'Metric'},
                {'value': 'Group A (n=50)'},
                {'value': 'Group B (n=48)'},
            ],
            [{'value': 'VAS'}, {'value': '7.2±1.3*'}, {'value': '6.8±1.1*'}],
            [{'value': 'VAS (wrong scale)'}, {'value': '72±13*'}, {'value': ''}],
        ]
    }
    
    footnotes = ["* P < 0.05"]
    
    sanitizer = TableSanitizer(specialty="LDH")
    cleaned_table, report = sanitizer.sanitize(table_data, footnotes, header_row_count=1)
    
    export = sanitizer.export_to_analysis_format(cleaned_table, report)
    
    print(f"\n导出格式:")
    print(f"  元数据: {export['metadata']}")
    print(f"  表头: {export['headers']}")
    print(f"  数据行数: {len(export['data'])}")
    
    # 验证 v2.6 字段
    assert 'scaled_cells' in export['metadata'], "应包含 scaled_cells"
    assert 'stat_type_distribution' in export['metadata'], "应包含 stat_type_distribution"
    
    # 验证数据中的统计语义
    first_data = export['data'][0]
    if 'Group A (n=50)' in first_data:
        group_data = first_data['Group A (n=50)']
        assert 'stat_type' in group_data, "应包含 stat_type"
        assert 'numeric_insight' in group_data, "应包含 numeric_insight"
    
    print("\n✅ 导出格式测试通过 (v2.6)")
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("TableSanitizer v2.6 - 表格数据预处理器测试")
    print("="*70)
    print("新功能：MCID检测 | 尺度混淆自动修正 | 统计语义识别")
    print("="*70)
    
    test_spine_surgery_table()
    test_mcid_detection()
    test_export_format()
    
    print("\n" + "="*70)
    print("所有测试通过！v2.6 功能正常")
    print("="*70)
