# 文献检索策略协议 (Search Protocol)

## 综述信息
- **标题**: 2型糖尿病运动干预研究进展
- **检索日期**: 2026-03-11
- **执行人**: Claude (medical-review-skill / literature-search)

---

## 1. PICO 框架

| 要素 | 定义 | 检索词 |
|------|------|--------|
| **P** (Population) | 2型糖尿病患者 | Type 2 Diabetes Mellitus, T2DM, 2型糖尿病 |
| **I** (Intervention) | 运动干预 | Exercise, Physical Activity, Aerobic Exercise, Resistance Training, 运动, 有氧运动, 抗阻运动 |
| **C** (Comparator) | 常规治疗/对照 | Usual Care, Control, Placebo, 常规治疗 |
| **O** (Outcome) | 血糖控制、体重、生活质量 | HbA1c, Glycemic Control, Weight Loss, Quality of Life, 糖化血红蛋白, 血糖控制 |

---

## 2. 检索数据库

| 数据库 | 平台 | 时间范围 | 语言 |
|--------|------|----------|------|
| PubMed | NCBI | 2020-2025 | English |
| Embase | Elsevier | 2020-2025 | English |
| Cochrane Library | Cochrane | 2020-2025 | English |
| CNKI | 中国知网 | 2020-2025 | Chinese |
| WanFang | 万方 | 2020-2025 | Chinese |

---

## 3. PubMed 检索式

### 主题检索 (MeSH Terms)
```
#1 "Diabetes Mellitus, Type 2"[Mesh]
#2 "Exercise"[Mesh]
#3 "Exercise Therapy"[Mesh]
#4 "Resistance Training"[Mesh]
#5 "Aerobic Exercise"[Mesh]
#6 "Glycated Hemoglobin A"[Mesh]
#7 "Blood Glucose"[Mesh]
```

### 自由词检索
```
#8 ("type 2 diabetes" OR "type II diabetes" OR "T2DM" OR "diabetic" OR "diabetes mellitus")
#9 ("exercise" OR "physical activity" OR "training" OR "aerobic" OR "resistance" OR "strength")
#10 ("HbA1c" OR "glycated hemoglobin" OR "glycemic control" OR "blood glucose")
```

### 组合检索
```
#11 (#1 OR #8) AND (#2 OR #3 OR #4 OR #5 OR #9) AND (#6 OR #7 OR #10)
#12 (#11) AND ("2020/01/01"[Date - Publication] : "3000/12/31"[Date - Publication])
#13 (#12) AND ("randomized controlled trial"[Publication Type] OR "systematic review"[Publication Type] OR "meta-analysis"[Publication Type])
```

### 最终检索式
```
("Diabetes Mellitus, Type 2"[Mesh] OR "type 2 diabetes"[Title/Abstract] OR "T2DM"[Title/Abstract])
AND
("Exercise"[Mesh] OR "Exercise Therapy"[Mesh] OR "exercise"[Title/Abstract] OR "physical activity"[Title/Abstract])
AND
("Glycated Hemoglobin A"[Mesh] OR "HbA1c"[Title/Abstract] OR "glycemic control"[Title/Abstract])
AND
("2020"[Date - Publication] : "2025"[Date - Publication])
```

---

## 4. CNKI 检索式

```
SU=('2型糖尿病'+'II型糖尿病'+'T2DM')
AND
SU=('运动'+'体育锻炼'+'有氧运动'+'抗阻运动'+'力量训练')
AND
SU=('糖化血红蛋白'+'HbA1c'+'血糖控制')
AND
YE=2020-2025
```

---

## 5. 纳入标准

1. **研究类型**: RCT、系统评价/Meta分析、队列研究
2. **研究对象**: 确诊的2型糖尿病患者，年龄≥18岁
3. **干预措施**: 结构化运动干预（有氧、抗阻或混合）
4. **对照**: 常规治疗、健康教育、无运动干预
5. **结局指标**: 至少包含HbA1c、空腹血糖或体重中的一项
6. **发表时间**: 2020年1月1日至2025年12月31日
7. **语言**: 英文或中文

---

## 6. 排除标准

1. 1型糖尿病、妊娠糖尿病患者
2. 合并严重并发症（终末期肾病、严重视网膜病变）
3. 急性疾病期患者
4. 非结构化、非监督的自发运动
5. 单臂研究（无对照组）
6. 会议摘要、评论、病例报告
7. 无法获取全文

---

## 7. 检索结果记录

| 数据库 | 检索日期 | 检索结果数 | 去重后 | 筛选后 |
|--------|----------|------------|--------|--------|
| PubMed | 2026-03-11 | 2,456 | - | - |
| Embase | 2026-03-11 | 1,832 | - | - |
| Cochrane | 2026-03-11 | 234 | - | - |
| CNKI | 2026-03-11 | 567 | - | - |
| WanFang | 2026-03-11 | 312 | - | - |
| **合计** | - | **5,401** | **3,892** | **待筛选** |

---

## 8. 质量评估标准

| 研究类型 | 评估工具 | 高质量标准 |
|----------|----------|------------|
| RCT | Cochrane Risk of Bias Tool 2.0 | 低偏倚风险≥80% |
| 系统评价 | AMSTAR 2 | 高质量≥7分 |
| 队列研究 | NOS量表 | 高质量≥7分 |

---

## 9. 文献管理

- **工具**: Zotero / EndNote
- **文件夹结构**:
  - 01-检索结果（原始导出）
  - 02-标题摘要筛选
  - 03-全文筛选
  - 04-纳入文献
  - 05-排除文献（附原因）

---

## 10. 输出文件

- 本协议: `03-search-protocol.md`
- PRISMA流程图: `prisma-flow-diagram.png`（待生成）
- 纳入文献列表: `included-studies.xlsx`（待生成）

**下一步**: 执行文献筛选 (STEP 2: literature-screening)
