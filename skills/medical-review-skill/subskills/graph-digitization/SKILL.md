---
name: graph-digitization
version: "2.5.1"
description: "图表数字化模块 - 使用Vision模型从医学图表中提取结构化数据"
---

# 图表数字化模块 v2.5.1

## 支持的图表类型

- Kaplan-Meier生存曲线 (P0)
- Forest Plot森林图 (P0)
- 柱状图/折线图 (P1)
- ROC曲线 (P2)

## v2.5.1 重大增强

自洽性重算熔断机制：基于提取数据重新拟合Cox模型，差异>5%强制熔断。

**版本**: 2.5.1
