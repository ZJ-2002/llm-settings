# 双轨制表格提取系统 - 快速开始

## 系统能解决什么问题？

| 问题 | 解决方案 |
|------|----------|
| LLM提取数值错误 | 置信度评估 + 人工复核 |
| 合并单元格解析错误 | 视觉模型 + 人工校验 |
| 表格与正文数据不一致 | Table-Logic-Verify自动检测 |
| 无法追溯数据来源 | 完整审计日志 |

## 依赖安装指南

本系统采用**分层依赖设计**，根据使用场景选择安装级别：

### 方案1：最小安装（核心功能）
适用于仅需使用置信度评估、逻辑校验等非PDF功能的场景。

```bash
pip install pandas numpy
```

**可用功能：**
- ✅ HierarchicalHeaderParser (表头解析)
- ✅ FootnoteLinker (脚注关联)
- ✅ TableSanitizer (表格清洗)
- ✅ HeterogeneityMonitor (异质性监测)
- ✅ EnhancedNumericEngine (数值识别)
- ✅ BiasAssessor (偏倚评估)
- ✅ FinalSynthesizer (证据聚合)
- ❌ PDF表格提取

### 方案2：标准安装（推荐，含PDF解析）
适用于需要从PDF提取表格的场景。

```bash
pip install -r requirements.txt
```

**可用功能：**
- ✅ 全部核心功能
- ✅ PDF表格检测与提取
- ✅ 置信度评估与校验
- ❌ 高级统计分析

### 方案3：完整安装（所有功能）
适用于需要使用中位数转换、敏感性分析等高级统计功能的场景。

```bash
pip install -r requirements.txt
pip install scipy statsmodels
```

**可用功能：**
- ✅ 全部核心功能
- ✅ PDF表格检测与提取
- ✅ MedianToMeanConverter (中位数转换)
- ✅ SensitivityAnalyzer (敏感性分析)

## 5分钟快速开始

### 1. 安装依赖（选择上述方案之一）

```bash
# 推荐：标准安装
pip install -r requirements.txt
```

### 2. 验证安装

```python
from core import get_version_info

info = get_version_info()
print(f"版本: {info['version']}")
print(f"v2.6模块可用: {info['v2_6_modules_available']}")
print(f"v2.6.1模块可用: {info['v2.6_1_modules_available']}")
print("功能列表:")
for feature in info['features']:
    print(f"  - {feature}")
```

### 3. 使用核心功能（无需PDF）

```python
from core import EnhancedNumericEngine, ConfidenceAssessor

# 数值识别引擎（无需任何外部依赖）
engine = EnhancedNumericEngine()
insight = engine.recognize("75", "VAS")
print(f"VAS值: {insight}")  # 自动识别为7.5（0-10尺度）

# 置信度评估
assessor = ConfidenceAssessor()
result = assessor.assess_cell("48.5%", "percentage")
print(f"置信度: {result.level.value}级 ({result.score})")
```

### 4. 提取PDF表格（需要PyMuPDF）

```python
from core import DualTrackExtractor

# 初始化提取器
extractor = DualTrackExtractor()

# 提取表格（需要 PyMuPDF）
tables = extractor.extract_from_pdf('paper.pdf', table_page=2)

for table in tables:
    print(f"表格: {table.table_id}")
    print(f"置信度: {table.confidence_assessment['overall_score']:.2f}")
    print(f"需要复核: {'是' if table.needs_review else '否'}")
```

### 5. 启动人工复核界面

```bash
python -m table_extraction.ui \
    --extraction-result extraction-v1.json \
    --output extraction-v2.json
```

### 6. 运行校验

```python
from core import TableLogicVerifier

verifier = TableLogicVerifier()
report = verifier.verify(extraction_v2)

if report['status'] == 'passed':
    print("✅ 表格校验通过，可以入库")
else:
    print(f"❌ 发现问题: {report['summary']['critical_issues']} 个严重问题")
```

## 典型工作流

```
PDF文献
   │
   ▼
┌─────────────────┐
│ AI预提取        │ ← 2分钟
│ 标记置信度      │
└─────────────────┘
   │
   ▼
分流决策
   │
   ├── A级(≥90%) ─────┐
   │                   │
   ├── B级(70-90%) ────┼──► 自动校验 ──► 通过 ──► 入库
   │                   │                    │
   └── C级(<70%) ──────┘                    └──► 人工复核
```

## 功能可用性矩阵

| 模块/功能 | 最小安装 | 标准安装 | 完整安装 |
|-----------|---------|---------|---------|
| HierarchicalHeaderParser | ✅ | ✅ | ✅ |
| FootnoteLinker | ✅ | ✅ | ✅ |
| TableSanitizer | ✅ | ✅ | ✅ |
| HeterogeneityMonitor | ✅ | ✅ | ✅ |
| EnhancedNumericEngine | ✅ | ✅ | ✅ |
| BiasAssessor | ✅ | ✅ | ✅ |
| FinalSynthesizer | ✅ | ✅ | ✅ |
| ConfidenceAssessor | ✅ | ✅ | ✅ |
| TableLogicVerifier | ✅ | ✅ | ✅ |
| DualTrackExtractor | ❌ | ✅ | ✅ |
| TableDetector | ❌ | ✅ | ✅ |
| MedianToMeanConverter | ❌ | ❌ | ✅ |
| SensitivityAnalyzer | ❌ | ❌ | ✅ |

## 文件结构

```
table-extraction/
├── core/
│   ├── detector.py              # 表格检测（需PyMuPDF）
│   ├── extractor.py             # AI提取（需PyMuPDF）
│   ├── confidence.py            # 置信度评估（无依赖）
│   ├── verification.py          # 逻辑校验（无依赖）
│   ├── enhanced_numeric_engine.py  # 数值识别（无依赖）
│   ├── bias_assessor.py         # 偏倚评估（无依赖）
│   ├── final_synthesizer.py     # 证据聚合（无依赖）
│   ├── median_converter.py      # 中位数转换（需scipy）
│   └── sensitivity_analyzer.py  # 敏感性分析（需scipy）
├── ui/
│   ├── web_interface.py         # Web界面
│   └── components/              # UI组件
├── tests/
│   └── test_cases/              # 测试用例
├── requirements.txt             # 依赖配置（分层）
├── config.yaml                  # 配置文件
└── README.md                    # 本文件
```

## 常见问题

**Q: 为什么需要人工复核？LLM不能直接提取正确吗？**

A: 医学表格对精度要求极高（p=0.049 vs p=0.0491含义完全不同），当前LLM在数值精确性上仍有局限。双轨制是在"效率"和"准确性"之间的务实平衡。

**Q: PyMuPDF安装失败怎么办？**

A: PyMuPDF在某些系统上可能需要额外依赖：
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev libxml2-dev libxslt1-dev

# macOS
brew install swig

# 然后安装
pip install PyMuPDF>=1.23.0
```

**Q: 什么样的表格可以自动通过？**

A: 满足以下条件：
- 简单结构（<10行，无合并单元格）
- 所有单元格置信度≥90%
- 通过Table-Logic-Verify全部校验

**Q: 人工复核需要多长时间？**

A: 经验数据：
- 简单表格（20单元格）：2-3分钟
- 中等表格（50单元格）：5-8分钟
- 复杂表格（100+单元格）：15-20分钟

**Q: 没有PyMuPDF能用哪些功能？**

A: 可以正常使用所有非PDF功能：
- 数值识别与MCID评估
- 置信度评估
- 表格逻辑校验
- 偏倚风险评估
- 证据聚合

只需将数据以字典格式传入，无需PDF解析。

## 进阶使用

参见 `dual-track-system.md` 获取完整文档。

---

*最后更新: 2026-03-13*
