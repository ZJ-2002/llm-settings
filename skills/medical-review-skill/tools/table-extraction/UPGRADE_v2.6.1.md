# TableSanitizer v2.6.1 升级说明

## 升级概览

**从 v2.6 到 v2.6.1 的核心改进：**

| 功能模块 | v2.6 | v2.6.1 | 改进点 |
|---------|------|--------|--------|
| 中位数转换 | ❌ | ✅ | Median(IQR)→Mean(SD) |
| 敏感性分析 | ❌ | ✅ | Meta前自检 |
| 异质性监测 | 基础版 | 增强版 | CV+Z-score双检测 |
| 偏倚评估 | RoB 2.0 | RoB 2.0 + GRADE | 证据质量评级 |

## 新功能详解

### 1. 中位数转换器 (MedianToMeanConverter)

**问题**: Meta分析通常要求均值±标准差，但文献常报告 中位数(IQR)

**解决方案**: 基于统计文献的可靠转换算法

```python
# v2.6.1 新功能
from core.median_converter import MedianToMeanConverter

converter = MedianToMeanConverter()

# 输入: 中位数(IQR)格式
result = converter.convert_median_iqr(
    median=75.0,
    q1=65.0,
    q3=85.0,
    n=50
)

# 输出:
print(f"Mean ≈ {result.estimated_mean:.2f}")    # 估计均值
print(f"SD ≈ {result.estimated_sd:.2f}")        # 估计标准差
print(f"Method: {result.method_used}")          # 使用的方法
print(f"Confidence: {result.confidence_level}") # 高/中/低
```

**两种核心算法**:

| 算法 | 作者 | 适用场景 | 精度 |
|------|------|----------|------|
| Luo et al. | Luo et al. (2018) | Median(IQR) → Mean | 高 |
| Wan et al. | Wan et al. (2014) | Median(range) → Mean | 中 |

**置信度评估**:
- **High**: 样本量充足，转换可靠
- **Medium**: 样本量中等，建议敏感性分析
- **Low**: 样本量小，谨慎使用

### 2. 敏感性分析引擎 (SensitivityAnalyzer)

**问题**: 转换后的数据可能影响Meta分析结论

**解决方案**: 预分析自检，评估"结论翻转"风险

```python
# v2.6.1 新功能
from core.sensitivity_analyzer import SensitivityAnalyzer

analyzer = SensitivityAnalyzer()

# 模拟: 某研究使用了中位数转换
studies = [
    {
        'study_id': 'A',
        'mean': 75.0, 'sd': 10.0,
        'n': 50,
        'has_converted_data': False
    },
    {
        'study_id': 'B', 
        'mean': 72.5, 'sd': 9.5,  # 转换后的估计值
        'n': 48,
        'has_converted_data': True,  # 标记转换数据
        'conversion_method': 'Luo2018',
        'original_median': 72.0
    }
]

# 执行敏感性检查
report = analyzer.perform_check(studies, outcome='VAS')

print(f"Risk Level: {report.risk_level}")  # CRITICAL/HIGH/MODERATE/LOW
print(f"Conclusion Flip Risk: {report.conclusion_flip_risk}")

if report.impact_assessments:
    for impact in report.impact_assessments:
        print(f"  {impact['study']}: weight change {impact['weight_change']:.2%}")
```

**风险等级判定**:

| 等级 | 条件 | 建议 |
|------|------|------|
| **CRITICAL** | 转换数据占比>50% 且 接近显著性边界 | 重新设计分析策略 |
| **HIGH** | 转换数据占比30-50% 或 单研究权重>25% | 必须敏感性分析 |
| **MODERATE** | 转换数据占比10-30% | 建议敏感性分析 |
| **LOW** | 转换数据占比<10% | 常规报告即可 |

### 3. 增强型异质性监测 (HeterogeneityMonitor)

**v2.6.1 改进**: 从简单CV检测升级为 CV + Z-score 双维度检测

```python
# v2.6.1 增强版
from core.heterogeneity_monitor import HeterogeneityMonitor

monitor = HeterogeneityMonitor()

# 添加多个研究的数据
monitor.add_study('Smith2020', 'VAS', mean=7.2, sd=1.3, n=50)
monitor.add_study('Jones2021', 'VAS', mean=6.8, sd=1.5, n=45)
monitor.add_study('Wang2022', 'VAS', mean=4.5, sd=1.1, n=48)  # 异常值

# 获取分布报告
report = monitor.get_distribution_report('VAS')

print(f"CV: {report.cv:.2f}")  # 变异系数
print(f"Status: {report.status}")  # NORMAL/BORDERLINE/HIGH

if report.zscore_outliers:
    print("Z-score异常值:")
    for outlier in report.zscore_outliers:
        print(f"  {outlier['study']}: Z={outlier['zscore']:.2f}")

print(f"建议模型: {report.recommended_model}")  # FE/RE/REM
```

**多维度异质性评估**:

| 指标 | 阈值 | 意义 |
|------|------|------|
| CV < 0.35 | 低异质性 | 可用固定效应模型 |
| CV 0.35-0.50 | 中等异质性 | 建议随机效应 |
| CV > 0.50 | 高异质性 | 必须随机效应+亚组分析 |
| \|Z\| > 2.5 | 异常值 | 检查数据或排除 |

### 4. 增强型偏倚评估 (BiasAssessor)

**v2.6.1 改进**: 新增 GRADE 证据质量评级

```python
# v2.6.1 增强版
from core.bias_assessor import BiasAssessor

assessor = BiasAssessor()

# 评估单篇文献
assessment = assessor.assess_study(
    study_data={
        'study_type': 'RCT',
        'randomization_described': True,
        'allocation_concealed': True,
        'blinding_participants': True,
        'blinding_outcome': True,
        'attrition_rate': 0.08,  # 8%失访
        'itt_analysis': True,
        'protocol_registered': True
    },
    outcome='VAS leg pain'
)

# RoB 2.0 结果
print("Risk of Bias Assessment:")
for domain, judgment in assessment.domain_judgments.items():
    print(f"  {domain}: {judgment}")
print(f"Overall: {assessment.overall_risk}")

# v2.6.1 新增: GRADE评级
print("\nGRADE Assessment:")
print(f"  Quality: {assessment.grade_quality}")  # High/Moderate/Low/Very Low
print(f"  Downgrade factors:")
for factor in assessment.grade_downgrade_factors:
    print(f"    - {factor}")
```

**GRADE 降级因素**:

| 因素 | 阈值 | 降级 |
|------|------|------|
| 偏倚风险 | RoB≥2个Some Concerns | -1级 |
| 不一致性 | I²>50% 或 异质性明显 | -1或-2级 |
| 间接性 | 人群/干预/结局有差异 | -1或-2级 |
| 不精确性 | 总样本量<400 (二分类) | -1或-2级 |
| 发表偏倚 | 漏斗图不对称或缺失研究 | -1级 |

## API变更

### 新增模块

```python
# v2.6.1 新增模块
from core.median_converter import MedianToMeanConverter, ConversionResult
from core.sensitivity_analyzer import SensitivityAnalyzer, SensitivityReport
from core.enhanced_numeric_engine import EnhancedNumericEngine, NumericInsight
```

### 增强模块

```python
# HeterogeneityMonitor - 新增功能
monitor.add_study(study_id, metric, mean, sd, n)
report = monitor.get_distribution_report(metric)
# 新增: zscore_outliers, recommended_model

# BiasAssessor - 新增功能  
assessment = assessor.assess_study(study_data, outcome)
# 新增: grade_quality, grade_downgrade_factors
```

### 条件导入支持

```python
# core/__init__.py
# v2.6.1 新增: 优雅的依赖缺失处理

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# MedianConverter 和 SensitivityAnalyzer 仅在 scipy 可用时导入
if SCIPY_AVAILABLE:
    from .median_converter import MedianToMeanConverter
    from .sensitivity_analyzer import SensitivityAnalyzer
else:
    MedianToMeanConverter = None
    SensitivityAnalyzer = None

def get_version_info():
    """获取版本信息"""
    return {
        'version': '2.6.1',
        'v2_6_modules_available': True,
        'v2.6_1_modules_available': SCIPY_AVAILABLE,
        'features': [
            'HierarchicalHeaderParser',
            'FootnoteLinker', 
            'TableSanitizer',
            'BiasAssessor',
            'HeterogeneityMonitor',
            'EnhancedNumericEngine',
            # 仅当 scipy 可用时
            'MedianToMeanConverter' if SCIPY_AVAILABLE else None,
            'SensitivityAnalyzer' if SCIPY_AVAILABLE else None,
        ]
    }
```

## 依赖更新

### requirements.txt

```
# 核心依赖（必需）
numpy>=1.20.0
pandas>=1.3.0
PyMuPDF>=1.23.0  # PDF处理

# v2.6.1 新增（推荐安装）
scipy>=1.7.0      # 中位数转换和统计功能
```

### 分层安装

```bash
# 基础安装（不含v2.6.1高级功能）
pip install -r requirements.txt

# 完整安装（含所有功能）
pip install -r requirements.txt scipy
```

## 使用示例

### 完整的Meta前自检流程

```python
from core import (
    TableSanitizer, 
    BiasAssessor,
    HeterogeneityMonitor
)

# 仅当scipy可用时
try:
    from core import MedianToMeanConverter, SensitivityAnalyzer
    ADVANCED_MODE = True
except ImportError:
    ADVANCED_MODE = False

def pre_meta_screening(table_data_list):
    """Meta分析前的完整自检"""
    
    sanitizer = TableSanitizer(specialty="LDH")
    monitor = HeterogeneityMonitor()
    assessor = BiasAssessor()
    
    if ADVANCED_MODE:
        converter = MedianToMeanConverter()
        sensitivity = SensitivityAnalyzer()
    
    results = []
    
    for table_data in table_data_list:
        # 1. 表格清洗
        cleaned, report = sanitizer.sanitize(table_data)
        
        # 检查尺度混淆
        if report.scaled_cells > 0:
            print(f"⚠️ 检测到{report.scaled_cells}个尺度转换单元格")
        
        # 2. 异质性预监测
        for row in cleaned:
            for cell in row:
                if cell.is_numeric and cell.sample_size:
                    monitor.add_study(
                        study_id=table_data['study_id'],
                        metric=cell.row_label,
                        mean=cell.numeric_insight.value,
                        sd=cell.numeric_insight.dispersion or 0,
                        n=cell.sample_size
                    )
        
        # 3. 偏倚评估
        rob = assessor.assess_study(table_data['study_info'])
        
        # 4. v2.6.1: 中位数转换（如需要）
        if ADVANCED_MODE and has_median_data(table_data):
            conv_result = converter.convert_median_iqr(
                median=table_data['median'],
                q1=table_data['q1'],
                q3=table_data['q3'],
                n=table_data['n']
            )
            print(f"转换: Median→Mean, 置信度={conv_result.confidence_level}")
        
        results.append({
            'study_id': table_data['study_id'],
            'sanitization_report': report,
            'rob_assessment': rob,
            'quality_score': report.quality_score
        })
    
    # 5. v2.6.1: 敏感性分析（如需要）
    if ADVANCED_MODE:
        sens_report = sensitivity.perform_check(results, outcome='VAS')
        if sens_report.risk_level in ['CRITICAL', 'HIGH']:
            print(f"🚨 敏感性风险: {sens_report.risk_level}")
            print(sens_report.recommendations)
    
    # 6. 异质性汇总
    for metric in monitor.metrics:
        dist_report = monitor.get_distribution_report(metric)
        if dist_report.status == 'HIGH':
            print(f"⚠️ {metric} 高异质性: CV={dist_report.cv:.2f}")
    
    return results
```

## 升级检查清单

- [ ] 安装 scipy (如需 v2.6.1 高级功能)
- [ ] 更新 core/__init__.py 的条件导入
- [ ] 验证 MedianConverter 转换准确性
- [ ] 测试 SensitivityAnalyzer 风险检测
- [ ] 检查 GRADE 评估逻辑
- [ ] 更新 Meta 分析流程以集成自检

## 向后兼容性

v2.6.1 完全向后兼容：
- 所有 v2.6 API 保持不变
- v2.6.1 功能为新增，不影响现有代码
- 缺失 scipy 时优雅降级

---

*版本: v2.6.1*
*发布日期: 2026-03-13*
*依赖: Python 3.8+, numpy, pandas, PyMuPDF, scipy (可选)*
