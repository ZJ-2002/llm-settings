---
name: clinical-trials-monitor
description: 动态临床价值评估系统。检索ClinicalTrials.gov和最新指南，评估选题的竞争性风险和研究时效性。
version: "1.0.0"
---

# 动态临床价值评估系统

## 概述

本系统用于在综述选题阶段评估其**时效性**和**竞争性风险**，通过检索：
- ClinicalTrials.gov（正在进行/近期完成的临床试验）
- 权威医学协会最新指南
- 系统评价/Meta分析注册库（PROSPERO）

提前预警选题可能面临的"被抢发"风险。

---

## 核心功能

### 1. 临床试验竞争分析

检索正在进行的试验，评估：
- 试验阶段（Phase I/II/III/IV）
- 预计完成时间
- 样本量规模
- 研究问题重叠度

### 2. 指南动态追踪

检索权威机构的最新指南：
- 是否存在即将更新的指南
- 现有指南的发表时间
- 指南中证据空白的填补情况

### 3. 综述注册监测

检查PROSPERO等注册库：
- 是否有正在进行的系统评价
- 选题重叠情况
- 预计发表时间

---

## 竞争性风险评估矩阵

### 风险等级定义

| 等级 | 描述 | 行动建议 |
|------|------|----------|
| 🔴 **极高风险** | 已有大型Phase III试验即将完成（6个月内） | **建议更换选题**或转为快速述评 |
| 🟠 **高风险** | 有多项Phase II/III试验进行中，预计1年内完成 | 需加速撰写，明确差异化定位 |
| 🟡 **中等风险** | 有试验进行中，但完成时间>1年或样本量小 | 正常进行，关注试验进展 |
| 🟢 **低风险** | 无相关试验或仅早期试验 | 正常进行 |

### 评估维度

```yaml
竞争性风险评分:
  临床试验维度 (权重40%):
    - Phase III试验数 × 3分
    - Phase II试验数 × 2分
    - Phase I试验数 × 1分
    - 预计6个月内完成 × 5倍权重
    - 预计1年内完成 × 2倍权重
    
  指南维度 (权重30%):
    - 指南<1年 (-2分)
    - 指南1-3年 (0分)
    - 指南>3年 (+1分)
    - 指南更新进行中 (+3分)
    
  综述竞争维度 (权重30%):
    - PROSPERO注册综述 (+2分/项)
    - 预计6个月内发表 × 2倍权重
```

---

## 检索策略

### ClinicalTrials.gov 检索

```python
import requests
from datetime import datetime, timedelta

class ClinicalTrialsMonitor:
    """ClinicalTrials.gov监测器"""
    
    API_BASE = "https://clinicaltrials.gov/api/v2"
    
    def search_trials(self, condition, interventions=None, status=None):
        """
        检索相关临床试验
        
        Parameters:
            condition: 疾病/状况（如"Osteoarthritis"）
            interventions: 干预措施列表
            status: 试验状态过滤
        """
        params = {
            'query.cond': condition,
            'filter.overallStatus': status or 'RECRUITING|ENROLLING_BY_INVITATION|ACTIVE_NOT_RECRUITING',
            'pageSize': 100,
            'sort': '@relevance'
        }
        
        if interventions:
            params['query.intr'] = ' OR '.join(interventions)
        
        response = requests.get(
            f"{self.API_BASE}/studies",
            params=params
        )
        
        return self.parse_trials(response.json())
    
    def assess_competition_risk(self, trials):
        """评估竞争风险"""
        risk_score = 0
        high_risk_trials = []
        
        for trial in trials:
            # 评估试验阶段权重
            phase_weight = {
                'PHASE1': 1,
                'PHASE2': 2,
                'PHASE3': 3,
                'PHASE4': 1
            }.get(trial['phase'], 0)
            
            # 评估时间风险
            completion_date = trial.get('completionDate')
            if completion_date:
                months_to_complete = self.months_until(completion_date)
                if months_to_complete <= 6:
                    time_multiplier = 5
                    high_risk_trials.append(trial)
                elif months_to_complete <= 12:
                    time_multiplier = 2
                else:
                    time_multiplier = 1
            else:
                time_multiplier = 1
            
            risk_score += phase_weight * time_multiplier
        
        return {
            'total_trials': len(trials),
            'risk_score': risk_score,
            'risk_level': self.categorize_risk(risk_score),
            'high_risk_trials': high_risk_trials
        }
```

### 指南检索

```python
class GuidelinesMonitor:
    """医学指南监测器"""
    
    SOURCES = {
        'NICE': 'https://www.nice.org.uk/guidance/',
        'AAOS': 'https://www.aaos.org/guidelines/',
        'ESC': 'https://www.escardio.org/Guidelines/',
        'NCCN': 'https://www.nccn.org/guidelines/',
        'WHO': 'https://www.who.int/publications/guidelines/'
    }
    
    def search_guidelines(self, topic, years=3):
        """检索相关指南"""
        guidelines = []
        
        for source, url in self.SOURCES.items():
            results = self.scrape_or_search(source, topic)
            for result in results:
                guideline = {
                    'source': source,
                    'title': result['title'],
                    'year': result['year'],
                    'url': result['url'],
                    'update_status': result.get('update_status', 'unknown')
                }
                guidelines.append(guideline)
        
        return self.analyze_guideline_freshness(guidelines)
    
    def analyze_guideline_freshness(self, guidelines):
        """分析指南时效性"""
        current_year = datetime.now().year
        
        analysis = {
            'total_guidelines': len(guidelines),
            'recent_guidelines': 0,  # <1年
            'moderate_guidelines': 0,  # 1-3年
            'outdated_guidelines': 0,  # >3年
            'updates_in_progress': 0
        }
        
        for g in guidelines:
            age = current_year - g['year']
            if age < 1:
                analysis['recent_guidelines'] += 1
            elif age <= 3:
                analysis['moderate_guidelines'] += 1
            else:
                analysis['outdated_guidelines'] += 1
            
            if g.get('update_status') == 'in_progress':
                analysis['updates_in_progress'] += 1
        
        return analysis
```

### PROSPERO检索

```python
class ProsperoMonitor:
    """PROSPERO注册库监测器"""
    
    def search_registered_reviews(self, topic):
        """检索已注册的系统评价"""
        # PROSPERO提供CSV导出或搜索界面
        # 这里简化处理，实际需解析网页或CSV
        
        search_url = "https://www.crd.york.ac.uk/prospero/#search-advanced"
        
        # 模拟搜索结果
        results = self.perform_search(search_url, topic)
        
        reviews = []
        for result in results:
            review = {
                'title': result['title'],
                'registration_number': result['id'],
                'status': result['status'],
                'expected_completion': result.get('completion_date'),
                'overlap_assessment': self.assess_topic_overlap(topic, result['title'])
            }
            reviews.append(review)
        
        return reviews
```

---

## 集成进STEP 0

### 更新 review-novelty-gate

```markdown
## STEP 0 更新：动态临床价值评估

在原有Go/No-Go决策基础上，增加竞争性风险评估：

### 新增评估维度: Q5 - 竞争性风险

检索以下数据库：
1. ClinicalTrials.gov
2. 主要指南发布机构
3. PROSPERO

### 风险评级输出

```yaml
竞争性风险评估:
  临床试验竞争:
    total_active_trials: 12
    phase3_trials: 3
    high_risk_trials:
      - trial_id: NCT04512345
        title: "大型RCT评估新药X治疗骨关节炎"
        phase: Phase 3
        sample_size: 1500
        completion_date: "2025-06-01"
        risk_contribution: 极高
    
  指南时效性:
    latest_guideline: "2024年AAOS指南"
    guideline_age_months: 8
    update_status: 无更新计划
    
  综述竞争:
    prospero_registered: 2
    near_completion: 1
    
  总体风险评级: 🔴 极高风险
  
  建议:
    - 主要建议: 考虑更换选题或转为快速述评
    - 备选方案: 聚焦该大型试验未覆盖的亚组人群
    - 时间窗口: 如坚持此选题，需在3个月内完成初稿
```

### 更新决策矩阵

| 原分类 | 竞争风险 | 最终分类 | 决策 |
|--------|----------|----------|------|
| A类 | 低风险 | A类 | 强烈推荐继续 |
| A类 | 高风险 | B类 | 推荐继续，但需加速 |
| B类 | 极高风险 | C类 | 有条件推荐，需明确差异化 |
| 任何 | 极高风险+大型III期即将完成 | D-3类 | 建议更换选题 |
```

---

## 预警系统

### 自动预警配置

```yaml
# alerts.yaml

alert_rules:
  critical_alert:
    condition: "phase3_within_6_months > 0"
    action: "immediate_notification"
    message: "检测到高风险竞争试验，建议重新评估选题"
    
  warning_alert:
    condition: "total_active_trials > 10 AND avg_completion < 12_months"
    action: "weekly_digest"
    message: "该领域研究活跃，建议加速撰写进度"
    
  guideline_alert:
    condition: "guideline_update_in_progress == true"
    action: "immediate_notification"
    message: "相关指南正在更新，可能影响综述价值"

notification_channels:
  - email
  - dashboard
  - workflow_status
```

---

## 报告模板

### 竞争性风险报告

```markdown
# 竞争性风险评估报告

## 评估日期
2026年3月12日

## 选题信息
- **疾病/状况**: 膝骨关节炎
- **干预措施**: 富血小板血浆(PRP)注射
- **综述类型**: 治疗性综述

---

## 一、临床试验竞争分析

### 检索策略
- 数据库: ClinicalTrials.gov
- 检索词: "knee osteoarthritis" AND "platelet-rich plasma"
- 状态: Recruiting, Active, Not yet recruiting

### 检索结果
| 试验阶段 | 数量 | 预计完成时间<6月 | 预计完成时间<12月 |
|----------|------|------------------|------------------|
| Phase III | 2 | 1 | 1 |
| Phase II | 4 | 0 | 2 |
| Phase I | 1 | 0 | 0 |
| **总计** | **7** | **1** | **3** |

### 高风险试验详情

#### 试验1: NCT05123456
- **标题**: Efficacy and Safety of Autologous PRP in Knee OA
- **阶段**: Phase III
- **样本量**: 360例
- **主要终点**: WOMAC评分变化
- **预计完成**: 2025年5月
- **风险等级**: 🔴 极高
- **与本综述重叠**: 高度重叠（相同干预、相同结局）

#### 试验2: NCT05123457
- **标题**: Comparative Study of PRP vs Hyaluronic Acid
- **阶段**: Phase III
- **样本量**: 240例
- **预计完成**: 2025年11月
- **风险等级**: 🟠 高

### 临床试验风险评估
- **风险评分**: 23/30
- **风险等级**: 🔴 极高风险

---

## 二、指南时效性分析

### 相关指南
| 指南 | 发布机构 | 年份 | 距今年限 | 更新状态 |
|------|----------|------|----------|----------|
| 膝OA管理指南 | AAOS | 2022 | 3年 | 2025年更新计划中 |
| 骨关节炎治疗指南 | OARSI | 2019 | 6年 | 已过时 |
| 膝OA非手术治疗 | NICE | 2022 | 3年 | 无更新计划 |

### 指南风险评估
- **最新指南年龄**: 3年
- **更新计划**: 有（AAOS 2025）
- **风险贡献**: 中等

---

## 三、综述竞争分析

### PROSPERO检索
检索到 **3项** 已注册的系统评价：

1. **CD4202234567** - "PRP for knee osteoarthritis"
   - 状态: 已完成
   - 发表情况: 已检索发表，2024年Cochrane
   
2. **CD4202234568** - "Comparative effectiveness of intra-articular injections"
   - 状态: 进行中
   - 预计完成: 2025年6月
   
3. **CD4202234569** - "PRP preparation methods in OA"
   - 状态: 进行中
   - 预计完成: 2025年9月

### 综述竞争风险评估
- **直接竞争**: 1项（已完成）
- **间接竞争**: 2项（进行中）
- **风险贡献**: 高

---

## 四、综合风险评估

### 风险评分汇总
| 维度 | 权重 | 原始分 | 加权分 |
|------|------|--------|--------|
| 临床试验 | 40% | 23 | 9.2 |
| 指南时效 | 30% | 6 | 1.8 |
| 综述竞争 | 30% | 8 | 2.4 |
| **总计** | | | **13.4** |

### 风险等级判定
- **总分**: 13.4
- **风险等级**: 🔴 **极高风险**

### 主要风险因素
1. 1项大型Phase III试验预计6个月内完成
2. AAOS指南2025年即将更新
3. 已有1项高质量Cochrane综述发表（2024）

---

## 五、建议

### 主要建议: ⚠️ 建议更换选题
理由：
- 大型RCT即将完成，可能改变证据格局
- 已有最新Cochrane综述覆盖相同主题
- 指南更新可能使当前结论过时

### 备选方案
如坚持此选题，建议：
1. **差异化定位**: 
   - 聚焦PRP制备方法（白细胞浓度、激活方式）
   - 或聚焦特定亚组（早期OA vs 晚期OA）
2. **加速撰写**: 
   - 目标完成时间: 2025年4月前
   - 抢在Phase III试验结果发布前投稿
3. **持续关注**: 
   - 每月监测试验进展
   - 设置NCT05123456完成提醒

### 监测计划
- 下次评估: 2025年4月1日
- 监测重点: NCT05123456试验状态
```

---

## 技术实现

```python
class ClinicalValueMonitor:
    """动态临床价值监测系统"""
    
    def __init__(self):
        self.ct_monitor = ClinicalTrialsMonitor()
        self.gl_monitor = GuidelinesMonitor()
        self.pr_monitor = ProsperoMonitor()
    
    def comprehensive_assessment(self, topic, interventions=None):
        """综合评估选题价值"""
        
        # 并行检索
        trials = self.ct_monitor.search_trials(topic, interventions)
        guidelines = self.gl_monitor.search_guidelines(topic)
        reviews = self.pr_monitor.search_registered_reviews(topic)
        
        # 风险评估
        trial_risk = self.ct_monitor.assess_competition_risk(trials)
        guideline_risk = self.assess_guideline_risk(guidelines)
        review_risk = self.assess_review_competition(reviews)
        
        # 综合评分
        total_score = (
            trial_risk['risk_score'] * 0.4 +
            guideline_risk['score'] * 0.3 +
            review_risk['score'] * 0.3
        )
        
        return {
            'overall_score': total_score,
            'risk_level': self.categorize_overall_risk(total_score),
            'trial_assessment': trial_risk,
            'guideline_assessment': guideline_risk,
            'review_assessment': review_risk,
            'recommendations': self.generate_recommendations(
                trial_risk, guideline_risk, review_risk
            )
        }
```

---

*版本: 1.0.0*
*更新日期: 2026-03-12*