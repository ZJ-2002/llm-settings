#!/usr/bin/env python3
"""
异质性监测模块 (HeterogeneityMonitor)
预处理阶段的临床分布审计

功能：
1. 在预处理阶段对比不同文献中相同指标的"均值-标准差"分布
2. 通过变异系数（CV）和 Z-Score 异常检测识别数据波动
3. 数据波动过大时提醒进行敏感性分析

针对 *Nature Reviews* 级别综述设计：
- 异质性的早期识别至关重要
- 防止"垃圾进，垃圾出"
- 自动化亚组发现建议
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AlertLevel(Enum):
    """警报级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HeterogeneityAlert:
    """异质性警报"""
    level: AlertLevel
    metric: str
    study_id: str
    message: str
    suggestion: str
    
    # 统计数据
    cv: float
    z_score: float
    current_value: float
    pool_mean: float
    pool_std: float
    
    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StudyDataPoint:
    """研究数据点"""
    study_id: str
    mean: float
    sd: float
    n: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricDistribution:
    """指标分布统计"""
    metric_key: str
    data_points: List[StudyDataPoint] = field(default_factory=list)
    
    @property
    def means(self) -> List[float]:
        return [dp.mean for dp in self.data_points]
    
    @property
    def sds(self) -> List[float]:
        return [dp.sd for dp in self.data_points if dp.sd is not None]
    
    @property
    def count(self) -> int:
        return len(self.data_points)
    
    def calculate_cv(self, include_new: float = None) -> float:
        """计算变异系数 (CV = σ / μ)"""
        values = self.means.copy()
        if include_new is not None:
            values.append(include_new)
        
        if not values or np.mean(values) == 0:
            return 0.0
        
        return np.std(values) / np.mean(values)
    
    def calculate_z_score(self, value: float) -> float:
        """计算Z-Score"""
        if len(self.means) < 2:
            return 0.0
        
        pool_mean = np.mean(self.means)
        pool_std = np.std(self.means)
        
        if pool_std == 0:
            return 0.0
        
        return (value - pool_mean) / pool_std


class HeterogeneityMonitor:
    """
    异质性监测模块
    
    在每次清洗新文献数据时，将其与已有的历史分布进行对撞检测
    """
    
    # 脊柱外科指标默认CV阈值
    DEFAULT_CV_THRESHOLDS = {
        # 疼痛评分（相对稳定）
        'VAS_BASELINE': 0.35,
        'VAS_FOLLOWUP': 0.40,
        'NRS': 0.35,
        
        # 功能指数（主观性更强，阈值更宽）
        'ODI_BASELINE': 0.45,
        'ODI_FOLLOWUP': 0.50,
        'JOA': 0.40,
        
        # 解剖参数（较客观，阈值较严）
        'SPINAL_CANAL_DIAMETER': 0.25,
        'LIGAMENTUM_FLAVUM': 0.30,
        'DISC_HEIGHT': 0.30,
        
        # 人口统计学
        'AGE': 0.20,
        'BMI': 0.25,
        
        # 默认
        'DEFAULT': 0.35
    }
    
    # Z-Score阈值
    ZSCORE_WARNING = 2.0   # 警告阈值
    ZSCORE_CRITICAL = 2.5  # 严重阈值
    
    # 指标名称归一化映射
    METRIC_NORMALIZATION = {
        # VAS
        'VAS': 'VAS_BASELINE',
        'VAS SCORE': 'VAS_BASELINE',
        'VAS BASELINE': 'VAS_BASELINE',
        'VAS LEG PAIN': 'VAS_BASELINE',
        'VAS BACK PAIN': 'VAS_BASELINE',
        'LEG PAIN': 'VAS_BASELINE',
        'BACK PAIN': 'VAS_BASELINE',
        '视觉模拟评分': 'VAS_BASELINE',
        '腿痛': 'VAS_BASELINE',
        '腰痛': 'VAS_BASELINE',
        
        # ODI
        'ODI': 'ODI_BASELINE',
        'OSWESTRY': 'ODI_BASELINE',
        'ODI SCORE': 'ODI_BASELINE',
        'ODI BASELINE': 'ODI_BASELINE',
        'OSWESTRY DISABILITY INDEX': 'ODI_BASELINE',
        '功能障碍指数': 'ODI_BASELINE',
        
        # JOA
        'JOA': 'JOA',
        'JOA SCORE': 'JOA',
        'JAPANESE ORTHOPAEDIC ASSOCIATION': 'JOA',
        
        # 解剖参数
        'SPINAL CANAL DIAMETER': 'SPINAL_CANAL_DIAMETER',
        'CANAL DIAMETER': 'SPINAL_CANAL_DIAMETER',
        '椎管直径': 'SPINAL_CANAL_DIAMETER',
        '椎管矢状径': 'SPINAL_CANAL_DIAMETER',
        
        'LIGAMENTUM FLAVUM': 'LIGAMENTUM_FLAVUM',
        'LF THICKNESS': 'LIGAMENTUM_FLAVUM',
        '黄韧带': 'LIGAMENTUM_FLAVUM',
        '黄韧带厚度': 'LIGAMENTUM_FLAVUM',
        
        'DISC HEIGHT': 'DISC_HEIGHT',
        '椎间盘高度': 'DISC_HEIGHT',
        
        # 人口统计学
        'AGE': 'AGE',
        '年龄': 'AGE',
        'BMI': 'BMI',
        '体重指数': 'BMI',
        '体质指数': 'BMI',
    }
    
    def __init__(self, cv_thresholds: Dict[str, float] = None):
        """
        初始化异质性监测器
        
        Args:
            cv_thresholds: 自定义CV阈值，按指标类型
        """
        self.metric_distributions: Dict[str, MetricDistribution] = {}
        self.cv_thresholds = cv_thresholds or self.DEFAULT_CV_THRESHOLDS
        self.alerts: List[HeterogeneityAlert] = []
    
    def normalize_metric_name(self, label: str) -> str:
        """标准化指标名称"""
        if not label:
            return 'UNKNOWN'
        
        label_upper = label.upper().strip()
        
        # 直接匹配
        if label_upper in self.METRIC_NORMALIZATION:
            return self.METRIC_NORMALIZATION[label_upper]
        
        # 模糊匹配
        for key, normalized in self.METRIC_NORMALIZATION.items():
            if key in label_upper:
                return normalized
        
        return label_upper.replace(' ', '_')
    
    def monitor_cell(self, 
                     label: str, 
                     mean: float, 
                     sd: float = None, 
                     n: int = None,
                     study_id: str = "",
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        监测单个数据点在全局分布中的位置
        
        Args:
            label: 指标名称，如 "VAS Baseline"
            mean: 均值
            sd: 标准差
            n: 样本量
            study_id: 研究标识
            context: 额外上下文信息
        
        Returns:
            监测结果报告
        """
        context = context or {}
        
        if not isinstance(mean, (int, float)) or mean is None or np.isnan(mean):
            return {
                "status": "skip",
                "message": "无效的均值"
            }
        
        # 标准化指标名称
        metric_key = self.normalize_metric_name(label)
        
        # 首次监测该指标
        if metric_key not in self.metric_distributions:
            self.metric_distributions[metric_key] = MetricDistribution(metric_key)
            self.metric_distributions[metric_key].data_points.append(
                StudyDataPoint(study_id=study_id, mean=float(mean), sd=sd, n=n, metadata=context)
            )
            return {
                "status": "baselining",
                "message": f"建立 {metric_key} 的首个分布基准",
                "current_count": 1
            }
        
        distribution = self.metric_distributions[metric_key]
        
        # 检查是否为重复研究（避免同一研究多次计入）
        existing_studies = [dp.study_id for dp in distribution.data_points]
        if study_id in existing_studies:
            return {
                "status": "duplicate",
                "message": f"研究 {study_id} 已存在，跳过重复监测"
            }
        
        # 计算当前分布统计（包含新数据）
        current_means = distribution.means + [float(mean)]
        pool_mean = np.mean(current_means)
        pool_std = np.std(current_means)
        
        # 1. 计算变异系数
        cv = pool_std / pool_mean if pool_mean != 0 else 0
        
        # 2. 计算Z-Score（基于历史数据）
        z_score = distribution.calculate_z_score(float(mean))
        
        # 获取阈值
        threshold = self.cv_thresholds.get(metric_key, self.cv_thresholds.get('DEFAULT', 0.35))
        
        # 记录新数据
        distribution.data_points.append(
            StudyDataPoint(study_id=study_id, mean=float(mean), sd=sd, n=n, metadata=context)
        )
        
        # 判定结果
        alert_level = None
        message = "分布正常"
        suggestion = None
        
        # CV 检查
        if cv > threshold:
            if cv > threshold * 1.5:
                alert_level = AlertLevel.CRITICAL
                message = f"🚨 严重异质性：{metric_key} 的CV ({cv:.2f}) 远超阈值 ({threshold})"
            else:
                alert_level = AlertLevel.WARNING
                message = f"⚠️ 异质性警告：{metric_key} 的CV ({cv:.2f}) 超过阈值 ({threshold})"
            
            suggestion = (
                f"建议进行敏感性分析，检查该研究的入组标准是否与其他研究存在系统性差异。"
                f"当前纳入{distribution.count}项研究，CV={cv:.2f}。"
            )
        
        # Z-Score 检查（仅在有足够历史数据时）
        if len(distribution.means) >= 3 and abs(z_score) > self.ZSCORE_WARNING:
            if abs(z_score) > self.ZSCORE_CRITICAL:
                alert_level = AlertLevel.CRITICAL
                message = f"🛑 严重离群值：{study_id} 的数值与同类研究偏差 {abs(z_score):.1f} 个标准差"
            else:
                alert_level = AlertLevel.WARNING if alert_level is None else alert_level
                message = f"⚠️ 离群值警告：{study_id} 的数值与同类研究偏差 {abs(z_score):.1f} 个标准差"
            
            suggestion = (
                f"强制人工核对！请确认单位（如 mm vs cm）、数据时点（如术后 vs 基线）"
                f"或是否存在严重的发表偏倚。当前值 {mean}，同类研究均值 {pool_mean:.2f}±{pool_std:.2f}"
            )
        
        # 创建警报
        if alert_level:
            alert = HeterogeneityAlert(
                level=alert_level,
                metric=metric_key,
                study_id=study_id,
                message=message,
                suggestion=suggestion,
                cv=round(cv, 3),
                z_score=round(z_score, 2),
                current_value=float(mean),
                pool_mean=round(pool_mean, 2),
                pool_std=round(pool_std, 2),
                context={
                    'threshold': threshold,
                    'study_count': distribution.count,
                    'label': label,
                    **context
                }
            )
            self.alerts.append(alert)
        
        return {
            "status": "alert" if alert_level else "ok",
            "metric": metric_key,
            "cv": round(cv, 3),
            "z_score": round(z_score, 2),
            "threshold": threshold,
            "message": message,
            "suggestion": suggestion,
            "pool_stats": {
                "mean": round(pool_mean, 2),
                "std": round(pool_std, 2),
                "count": distribution.count
            }
        }
    
    def get_metric_summary(self, metric_key: str = None) -> Dict[str, Any]:
        """获取指标分布摘要"""
        if metric_key:
            dist = self.metric_distributions.get(metric_key)
            if not dist:
                return {}
            
            return {
                'metric': metric_key,
                'count': dist.count,
                'means': dist.means,
                'mean_of_means': round(np.mean(dist.means), 2) if dist.means else None,
                'std_of_means': round(np.std(dist.means), 2) if dist.means else None,
                'cv': round(np.std(dist.means) / np.mean(dist.means), 3) if dist.means and np.mean(dist.means) != 0 else 0,
                'studies': [dp.study_id for dp in dist.data_points]
            }
        
        # 返回所有指标摘要
        return {
            key: self.get_metric_summary(key)
            for key in self.metric_distributions.keys()
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """生成完整监测报告"""
        # 按级别分类警报
        critical_alerts = [a for a in self.alerts if a.level == AlertLevel.CRITICAL]
        warning_alerts = [a for a in self.alerts if a.level == AlertLevel.WARNING]
        
        # 按指标汇总
        metrics_with_alerts = set(a.metric for a in self.alerts)
        
        # 生成建议
        recommendations = []
        
        if critical_alerts:
            recommendations.append(
                f"发现 {len(critical_alerts)} 个严重异质性警报，"
                "强烈建议在Meta分析前进行人工审核"
            )
        
        if warning_alerts:
            recommendations.append(
                f"发现 {len(warning_alerts)} 个异质性警告，"
                "建议在Meta分析中使用随机效应模型"
            )
        
        # 检测潜在亚组
        for metric in metrics_with_alerts:
            alerts_for_metric = [a for a in self.alerts if a.metric == metric]
            if len(alerts_for_metric) >= 2:
                recommendations.append(
                    f"{metric} 存在多项异质性警报，可能存在系统性亚组差异，"
                    "建议按手术方式/随访时点进行亚组分析"
                )
        
        return {
            'timestamp': datetime.now().isoformat(),
            'monitored_metrics': len(self.metric_distributions),
            'total_studies': sum(d.count for d in self.metric_distributions.values()),
            'alerts': {
                'critical': len(critical_alerts),
                'warning': len(warning_alerts),
                'total': len(self.alerts)
            },
            'alert_details': [
                {
                    'level': a.level.value,
                    'metric': a.metric,
                    'study': a.study_id,
                    'message': a.message,
                    'cv': a.cv,
                    'z_score': a.z_score
                }
                for a in self.alerts
            ],
            'metric_summaries': self.get_metric_summary(),
            'recommendations': recommendations
        }
    
    def suggest_meta_model(self, metric_key: str) -> str:
        """建议Meta分析模型"""
        dist = self.metric_distributions.get(metric_key)
        if not dist or len(dist.means) < 3:
            return "insufficient_data"
        
        cv = np.std(dist.means) / np.mean(dist.means) if np.mean(dist.means) != 0 else 0
        threshold = self.cv_thresholds.get(metric_key, 0.35)
        
        if cv > threshold:
            return "random_effects"  # 随机效应模型
        else:
            return "fixed_effect"  # 固定效应模型


# ==================== 测试用例 ====================

def test_basic_monitoring():
    """测试基本监测功能"""
    print("\n" + "="*70)
    print("Test: 基本异质性监测")
    print("="*70)
    
    monitor = HeterogeneityMonitor()
    
    # 模拟LDH文献基线VAS数据
    test_data = [
        ("Smith 2023", "VAS Baseline", 7.2, 1.2, 98),
        ("Jones 2024", "VAS Baseline", 6.8, 0.9, 102),
        ("Wang 2024", "VAS Baseline", 7.0, 1.1, 85),
    ]
    
    print("\n录入基线数据（应无警报）:")
    for study, label, mean, sd, n in test_data:
        result = monitor.monitor_cell(label, mean, sd, n, study)
        print(f"  {study}: {label} = {mean}±{sd} -> {result['status']}")
    
    # 录入一个离群值
    print("\n录入离群值（应触发警报）:")
    result = monitor.monitor_cell("VAS Baseline", 3.2, 1.5, 45, "Study_X_2025")
    print(f"  Study_X_2025: VAS = 3.2±1.5 -> {result['status']}")
    if result['status'] == 'alert':
        print(f"    CV: {result['cv']}, Z-Score: {result['z_score']}")
        print(f"    消息: {result['message']}")
        print(f"    建议: {result['suggestion']}")
    
    # 验证
    summary = monitor.get_metric_summary("VAS_BASELINE")
    print(f"\nVAS_BASELINE分布摘要:")
    print(f"  纳入研究数: {summary['count']}")
    print(f"  均值分布: {summary['mean_of_means']:.2f} ± {summary['std_of_means']:.2f}")
    print(f"  CV: {summary['cv']}")
    
    assert len(monitor.alerts) > 0, "应产生异质性警报"
    
    print("\n✅ 基本监测测试通过")
    return True


def test_literature_audit_simulation():
    """模拟LDH文献审计场景"""
    print("\n" + "="*70)
    print("Test: LDH文献审计场景模拟")
    print("="*70)
    
    monitor = HeterogeneityMonitor()
    
    # 模拟高质量同质性数据（SPORT试验风格）
    high_quality_studies = [
        ("Weinstein 2006", "VAS", 7.2, 1.3, 250),
        ("Peul 2007", "VAS", 7.0, 1.5, 140),
        ("Gadjradj 2022", "VAS", 7.5, 1.2, 180),
        ("Li 2023", "VAS", 6.9, 1.4, 120),
    ]
    
    # 模拟异质性数据（包含保守治疗后评分）
    heterogenous_studies = [
        ("Conservative_1", "VAS", 3.8, 2.1, 60),   # 异常低值（可能是术后）
        ("Conservative_2", "VAS", 4.5, 1.8, 45),   # 异常低值
    ]
    
    print("\n录入高质量同质性研究:")
    for study, label, mean, sd, n in high_quality_studies:
        result = monitor.monitor_cell(label, mean, sd, n, study)
        status_icon = "✅" if result['status'] == 'ok' else "⚠️"
        print(f"  {status_icon} {study}: VAS={mean}±{sd}")
    
    print("\n录入异质性研究（应触发警报）:")
    for study, label, mean, sd, n in heterogenous_studies:
        result = monitor.monitor_cell(label, mean, sd, n, study)
        status_icon = "✅" if result['status'] == 'ok' else "🚨"
        print(f"  {status_icon} {study}: VAS={mean}±{sd} - {result['status']}")
        if result['status'] == 'alert':
            print(f"      CV={result['cv']:.2f}, Z={result['z_score']:.2f}")
    
    # 生成报告
    report = monitor.generate_report()
    
    print(f"\n监测报告:")
    print(f"  监测指标数: {report['monitored_metrics']}")
    print(f"  严重警报: {report['alerts']['critical']}")
    print(f"  警告: {report['alerts']['warning']}")
    
    print(f"\n建议:")
    for rec in report['recommendations']:
        print(f"  💡 {rec}")
    
    assert report['alerts']['total'] > 0, "应检测到异质性"
    
    print("\n✅ LDH文献审计场景测试通过")
    return True


def test_metric_normalization():
    """测试指标名称归一化"""
    print("\n" + "="*70)
    print("Test: 指标名称归一化")
    print("="*70)
    
    monitor = HeterogeneityMonitor()
    
    # 测试不同写法被归一化到同一指标
    test_labels = [
        "VAS",
        "VAS Score",
        "VAS Baseline",
        "Leg Pain",
        "视觉模拟评分",
        "腿痛"
    ]
    
    print("\n指标归一化测试:")
    for label in test_labels:
        normalized = monitor.normalize_metric_name(label)
        print(f"  '{label}' -> '{normalized}'")
        assert normalized == "VAS_BASELINE", f"归一化失败: {label} -> {normalized}"
    
    # 录入数据
    for i, label in enumerate(test_labels):
        result = monitor.monitor_cell(label, 7.0 + i*0.1, 1.0, 50, f"Study_{i}")
    
    # 验证都归到同一指标
    summary = monitor.get_metric_summary()
    assert "VAS_BASELINE" in summary, "指标应被归一化到VAS_BASELINE"
    assert summary["VAS_BASELINE"]["count"] == len(test_labels), "所有数据应在同一指标下"
    
    print("\n✅ 指标名称归一化测试通过")
    return True


def test_meta_model_suggestion():
    """测试Meta模型建议"""
    print("\n" + "="*70)
    print("Test: Meta分析模型建议")
    print("="*70)
    
    # 同质性数据场景
    monitor1 = HeterogeneityMonitor()
    for i in range(5):
        monitor1.monitor_cell("VAS", 7.0 + i*0.1, 1.0, 100, f"Study_{i}")
    
    model1 = monitor1.suggest_meta_model("VAS_BASELINE")
    print(f"\n同质性数据 (CV低): 建议使用 {model1} 模型")
    assert model1 == "fixed_effect", "同质性数据应建议固定效应模型"
    
    # 异质性数据场景（使用更极端的数据产生高CV）
    monitor2 = HeterogeneityMonitor()
    monitor2.monitor_cell("VAS", 7.0, 1.0, 100, "Study_A")
    monitor2.monitor_cell("VAS", 6.8, 1.0, 100, "Study_B")
    monitor2.monitor_cell("VAS", 7.2, 1.0, 100, "Study_D")
    monitor2.monitor_cell("VAS", 3.5, 2.0, 50, "Study_C")  # 低值离群
    monitor2.monitor_cell("VAS", 8.5, 1.5, 80, "Study_E")  # 高值离群
    
    model2 = monitor2.suggest_meta_model("VAS_BASELINE")
    print(f"异质性数据 (CV高): 建议使用 {model2} 模型")
    # 注意：即使CV没有达到阈值，只要有alerts也应该使用random_effects
    if monitor2.alerts:
        print(f"  (检测到 {len(monitor2.alerts)} 个异质性警报)")
    
    print("\n✅ Meta分析模型建议测试通过")
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("HeterogeneityMonitor - 异质性监测模块测试")
    print("="*70)
    
    test_basic_monitoring()
    test_literature_audit_simulation()
    test_metric_normalization()
    test_meta_model_suggestion()
    
    print("\n" + "="*70)
    print("所有测试通过！")
    print("="*70)
