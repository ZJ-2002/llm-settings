#!/usr/bin/env python3
"""
表格提取核心模块 v2.6.1
整合：多级表头解析、脚注关联、临床边界检查、异质性监测、数值识别、偏倚评估、证据聚合
        中位数转换、敏感性分析（v2.6.1新增）

主要组件：
- HierarchicalHeaderParser: 多级表头解析器（v2.6.1: 修复父节点链接+性能优化）
- FootnoteLinker: 脚注关联器
- TableSanitizer: 表格数据预处理器（v2.6: MCID+尺度检测+统计语义）
- HeterogeneityMonitor: 异质性监测模块
- EnhancedNumericEngine: 增强型数值识别引擎（v2.6新增）- 无需外部依赖
- BiasAssessor: Cochrane RoB 2.0偏倚评估（v2.6.1: 不精确性评估增强）- 无需外部依赖
- FinalSynthesizer: 证据聚合器（v2.6新增）- 无需外部依赖
- MedianToMeanConverter: 中位数转换引擎（v2.6.1新增）- 需要scipy
- SensitivityAnalyzer: 敏感性分析引擎（v2.6.1新增）- 需要scipy
- EnhancedTableExtractor: 增强型表格提取器（整合以上所有组件）

版本: 2.6.1
更新: 2026-03-13
"""

from .header_parser import HierarchicalHeaderParser, HeaderNode
from .footnote_linker import FootnoteLinker, ProcessedCell, FootnoteEntry, FootnoteType
from .table_sanitizer import TableSanitizer, SanitizedCell, SanitizationReport, ClinicalBoundary, StatType, NumericInsight
from .heterogeneity_monitor import HeterogeneityMonitor, HeterogeneityAlert, AlertLevel, StudyDataPoint
from .confidence import ConfidenceAssessor, ConfidenceLevel, ConfidenceAssessment
from .verification import TableLogicVerifier

# v2.6 基础模块（无需外部依赖）
try:
    from .enhanced_numeric_engine import EnhancedNumericEngine, NumericInsight as ENNumericInsight, StatType as ENStatType, MCIDResult
    from .bias_assessor import BiasAssessor, BiasJudgment, RoBAssessment, RiskLevel, Domain
    from .final_synthesizer import FinalSynthesizer, EvidenceItem, SynthesisReport, EvidenceLevel
    __v2_6_modules_available__ = True
except ImportError as e:
    __v2_6_modules_available__ = False
    import warnings
    warnings.warn(f"v2.6基础模块导入失败: {e}")

# v2.6.1 高级统计模块（需要scipy）
try:
    from .median_converter import (
        MedianToMeanConverter, 
        ConversionResult, 
        BatchConversionReport,
        ConversionMethod,
        DistributionType,
        convert_median_to_mean,
        batch_convert_studies
    )
    __v2_6_1_median_available__ = True
except ImportError as e:
    __v2_6_1_median_available__ = False

# 单独导入敏感性分析模块
try:
    from .sensitivity_analyzer import (
        SensitivityAnalyzer,
        SensitivityReport,
        MetaAnalysisResult,
        ConclusionStatus,
        RiskLevel as SensitivityRiskLevel,
        perform_sensitivity_analysis,
        check_conclusion_robustness
    )
    __v2_6_1_sensitivity_available__ = True
except ImportError as e:
    __v2_6_1_sensitivity_available__ = False

# 合并v2.6.1模块可用性
__v2_6_1_modules_available__ = __v2_6_1_median_available__ and __v2_6_1_sensitivity_available__

__all__ = [
    # 表头解析
    'HierarchicalHeaderParser',
    'HeaderNode',
    
    # 脚注关联
    'FootnoteLinker',
    'ProcessedCell',
    'FootnoteEntry',
    'FootnoteType',
    
    # 表格清洗
    'TableSanitizer',
    'SanitizedCell',
    'SanitizationReport',
    'ClinicalBoundary',
    'StatType',
    'NumericInsight',
    
    # 异质性监测
    'HeterogeneityMonitor',
    'HeterogeneityAlert',
    'AlertLevel',
    'StudyDataPoint',
    
    # 置信度评估（无需外部依赖）
    'ConfidenceAssessor',
    'ConfidenceLevel',
    'ConfidenceAssessment',
    
    # 逻辑校验（无需外部依赖）
    'TableLogicVerifier',
]

# v2.6新增导出
if __v2_6_modules_available__:
    __all__.extend([
        # 数值识别
        'EnhancedNumericEngine',
        'ENNumericInsight',
        'ENStatType',
        'MCIDResult',
        
        # 偏倚评估
        'BiasAssessor',
        'BiasJudgment',
        'RoBAssessment',
        'RiskLevel',
        'Domain',
        
        # 证据聚合
        'FinalSynthesizer',
        'EvidenceItem',
        'SynthesisReport',
        'EvidenceLevel',
    ])

# v2.6.1中位数转换导出
if __v2_6_1_median_available__:
    __all__.extend([
        'MedianToMeanConverter',
        'ConversionResult',
        'BatchConversionReport',
        'ConversionMethod',
        'DistributionType',
        'convert_median_to_mean',
        'batch_convert_studies',
    ])

# v2.6.1敏感性分析导出
if __v2_6_1_sensitivity_available__:
    __all__.extend([
        'SensitivityAnalyzer',
        'SensitivityReport',
        'MetaAnalysisResult',
        'ConclusionStatus',
        'SensitivityRiskLevel',
        'perform_sensitivity_analysis',
        'check_conclusion_robustness',
    ])

__version__ = "2.6.1"

# 版本信息
def get_version_info():
    """获取版本信息"""
    features = [
        'HierarchicalHeaderParser with rowspan support',
        'FootnoteLinker with symbol extraction',
        'TableSanitizer with scale detection and MCID',
    ]
    
    if __v2_6_modules_available__:
        features.extend([
            'EnhancedNumericEngine with statistical semantics',
            'BiasAssessor with Cochrane RoB 2.0',
            'FinalSynthesizer with evidence aggregation',
        ])
    
    if __v2_6_1_median_available__:
        features.append('MedianToMeanConverter (Luo-Wan estimation)')
    
    if __v2_6_1_sensitivity_available__:
        features.append('SensitivityAnalyzer (conclusion flip detection)')
    
    return {
        'version': __version__,
        'v2_6_modules_available': __v2_6_modules_available__,
        'v2_6_1_median_available': __v2_6_1_median_available__,
        'v2_6_1_sensitivity_available': __v2_6_1_sensitivity_available__,
        'v2_6_1_modules_available': __v2_6_1_modules_available__,
        'features': features
    }
