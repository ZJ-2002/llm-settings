# TableSanitizer v2.6 升级说明

## 升级概览

**从 v2.5.1 到 v2.6 的核心改进：**

| 模块 | v2.5.1 | v2.6 | 改进点 |
|------|--------|------|--------|
| 表头解析 | 基础解析 | 语义树构建 | 支持任意层级嵌套 |
| 脚注关联 | 简单匹配 | 语义关联 | 类型识别 + 样本量提取 |
| 临床边界 | 固定边界 | 智能边界 | 尺度混淆检测 |
| MCID评估 | ❌ | ✅ | 临床意义评估 |
| 统计语义 | ❌ | ✅ | SD/SE/CI自动识别 |

## 新功能详解

### 1. 多级表头解析 (HierarchicalHeaderParser)

**问题**: 传统方法难以处理多级表头（如"时间点 > 组别 > 指标"）

**解决方案**: 构建表头语义树

```python
# v2.6 新功能
from core.header_parser import HierarchicalHeaderParser

parser = HierarchicalHeaderParser()

# 输入: 多级表头行
header_rows = [
    ['', '3 months', '3 months', '6 months', '6 months'],
    ['', 'Control', 'Treatment', 'Control', 'Treatment']
]

# 输出: 语义路径
col_paths = parser.parse(header_rows)
# 结果:
# col_0: ['Row_Label']
# col_1: ['3 months', 'Control']
# col_2: ['3 months', 'Treatment']
# col_3: ['6 months', 'Control']
# col_4: ['6 months', 'Treatment']
```

**应用场景**: 
- 随访时间点 × 治疗组别的复杂表格
- 自动识别各列对应的样本量

### 2. 脚注智能关联 (FootnoteLinker)

**问题**: 脚注符号与单元格数值混在一起，难以区分

**解决方案**: 自动剥离 + 语义识别

```python
# v2.6 新功能
from core.footnote_linker import FootnoteLinker

linker = FootnoteLinker([
    "* P < 0.05 vs baseline",
    "† Post-hoc analysis",
    "‡ LOCF imputation"
])

# 处理单元格
result = linker.link_cell("7.2±1.3*†")
# 结果:
# result.cleaned_value = "7.2±1.3"
# result.footnotes = [
#     {'symbol': '*', 'type': 'statistical', 'meaning': 'P < 0.05 vs baseline'},
#     {'symbol': '†', 'type': 'methodology', 'meaning': 'Post-hoc analysis'}
# ]
```

**LDH知识库**: 预设脊柱外科常用脚注含义

```python
LDH_KNOWLEDGE_BASE = {
    "*": {"type": "statistical", "default": "P < 0.05"},
    "†": {"type": "methodology", "default": "Post-hoc analysis"},
    "‡": {"type": "methodology", "default": "Subgroup analysis"},
    "§": {"type": "statistical", "default": "P < 0.01"},
    "¶": {"type": "methodology", "default": "Intention-to-treat"}
}
```

### 3. 尺度混淆自动检测 (v2.6 核心功能)

**问题**: VAS评分常见0-10和0-100两种尺度，混淆会导致Meta分析严重偏差

**解决方案**: 自动检测 + 标准化转换

```python
# v2.6 新功能
from core.table_sanitizer import TableSanitizer

sanitizer = TableSanitizer(specialty="LDH")

# 输入: 疑似0-100尺度的VAS值
table_data = {
    'rows': [
        [{'value': 'VAS'}, {'value': '72±13*'}],  # 明显是0-100
        [{'value': 'VAS'}, {'value': '7.2±1.3*'}]  # 0-10尺度
    ]
}

cleaned, report = sanitizer.sanitize(table_data, header_row_count=1)

# 结果:
# cleaned[0][1].cleaned_value = 7.2  # 自动转换为0-10
# cleaned[0][1].original_value = 72  # 保留原始值
# report.scale_warnings = [
#   "检测到尺度混淆: VAS 值 72 可能为 0-100 尺度，已自动转换为 7.2 (0-10)"
# ]
```

**支持的尺度转换**:
| 指标 | 标准尺度 | 替代尺度 | 转换因子 |
|------|----------|----------|----------|
| VAS | 0-10 | 0-100 | ÷10 |
| VAS | 0-10 | 0-100mm | ÷10 |

### 4. 统计语义识别 (v2.6 核心功能)

**问题**: 不同的离散度指标（SD/SE/CI）不能混用，Meta分析需要统一

**解决方案**: 自动识别统计类型

```python
# v2.6 新功能
from core.table_sanitizer import TableSanitizer

sanitizer = TableSanitizer(specialty="LDH")

# 输入: 不同格式的统计值
test_cases = [
    "7.2±1.3",           # Mean±SD (默认)
    "24.5 (1.2)",        # Mean(SE) - 上下文推断
    "185 [165, 205]",    # Mean (95% CI)
    "<0.001",            # P值带算子
]

for value in test_cases:
    insight = sanitizer._recognize_numeric_enhanced(value, "BMI")
    print(f"{value} -> {insight.stat_type}")
    # 7.2±1.3 -> StatType.MEAN_SD
    # 24.5 (1.2) -> StatType.MEAN_SE (根据上下文)
    # 185 [165, 205] -> StatType.MEAN_CI
    # <0.001 -> StatType.P_VALUE
```

### 5. MCID 评估 (v2.6 新增)

**问题**: 统计学显著 ≠ 临床有意义

**解决方案**: 内置MCID阈值评估

```python
# v2.6 新增: MCID阈值
MCID_THRESHOLDS = {
    "VAS": 1.5,           # VAS改善>1.5分才有临床意义
    "VAS_LEG": 2.0,       # 腿痛MCID更高
    "VAS_BACK": 1.5,
    "ODI": 12.8,          # ODI改善>12.8%
    "JOA": 2.5,           # JOA改善
}

# 使用示例
mcid = sanitizer._get_mcid_threshold("VAS leg pain")
print(f"VAS腿痛的MCID阈值: {mcid}")  # 输出: 2.0
```

## API变更

### 新增类

```python
# v2.6 新增类
from core.header_parser import HierarchicalHeaderParser, HeaderNode
from core.footnote_linker import FootnoteLinker, ProcessedCell, FootnoteType
from core.table_sanitizer import NumericInsight, StatType
```

### SanitizedCell 扩展

```python
@dataclass
class SanitizedCell:
    # v2.5.1 已有字段
    original_value: str
    cleaned_value: Any
    is_numeric: bool
    column_path: List[str]
    ...
    
    # v2.6 新增字段
    numeric_insight: Optional[NumericInsight]  # 数值深度洞察
    stat_type: StatType                         # 统计类型
    mcid_threshold: Optional[float]            # MCID阈值
    mcid_achievable: bool                       # 是否有MCID定义
```

### 清洗报告扩展

```python
@dataclass
class SanitizationReport:
    # v2.5.1 已有字段
    total_cells: int
    numeric_cells: int
    ...
    
    # v2.6 新增字段
    scaled_cells: int                          # 尺度转换计数
    scale_warnings: List[str]                  # 尺度混淆警告
    stat_type_distribution: Dict[str, int]     # 统计类型分布
    mcid_recommendations: List[str]            # MCID相关建议
```

## 使用示例

### 完整工作流

```python
from core import TableSanitizer

# 初始化（LDH专科）
sanitizer = TableSanitizer(specialty="LDH")

# 模拟LLM提取结果
table_data = {
    'title': 'Clinical Outcomes',
    'rows': [
        # 表头: 时间点 × 组别
        ['', '3 months', '3 months', '6 months', '6 months'],
        ['', 'Control', 'Treatment', 'Control', 'Treatment'],
        # 数据行
        ['VAS (0-10)', '7.2±1.3*', '6.1±1.1*†', '6.8±1.2*', '4.5±1.0*†'],
        ['ODI (%)', '45.2±12.3', '38.5±11.8*', '42.8±11.9', '28.2±10.5*†'],
        ['VAS (wrong scale)', '72±13*', '', '', ''],  # 尺度混淆测试
    ]
}

footnotes = [
    "* P < 0.05 vs baseline",
    "† P < 0.05 vs Control group",
    "Values are mean±SD"
]

# 执行清洗
cleaned_table, report = sanitizer.sanitize(
    table_data, 
    footnotes,
    header_row_count=2
)

# 查看报告
print(f"总单元格: {report.total_cells}")
print(f"尺度转换: {report.scaled_cells}")
print(f"统计类型分布: {report.stat_type_distribution}")

# 查看建议
for rec in report.recommendations:
    print(f"💡 {rec}")

# 导出为分析格式
export = sanitizer.export_to_analysis_format(cleaned_table, report)
# 包含完整的统计语义信息，可直接用于Meta分析
```

## 升级检查清单

- [ ] 更新代码到 v2.6
- [ ] 运行测试用例验证功能
- [ ] 检查现有表格处理逻辑兼容性
- [ ] 验证尺度转换功能正确性
- [ ] 确认MCID阈值配置
- [ ] 更新下游证据综合模块以使用新字段

## 向后兼容性

v2.6 保持与 v2.5.1 的向后兼容：
- 所有旧API继续工作
- 新增字段有合理默认值
- 原有输出格式不变

**建议**: 逐步迁移使用新功能，特别是尺度检测和统计语义识别。

---

*版本: v2.6*
*发布日期: 2026-03-13*
*作者: AI Assistant*
