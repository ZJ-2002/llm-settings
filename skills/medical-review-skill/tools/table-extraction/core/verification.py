#!/usr/bin/env python3
"""
表格逻辑校验器 - Table-Logic-Verify核心实现
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re


@dataclass
class VerificationIssue:
    """校验问题"""
    rule_name: str
    severity: str  # 'critical', 'warning', 'info'
    message: str
    location: str
    details: Dict[str, Any]


class VerificationRule(ABC):
    """校验规则基类"""
    
    @abstractmethod
    def check(self, table_data: Dict) -> List[VerificationIssue]:
        """执行校验"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """规则名称"""
        pass


class SampleSizeConsistencyRule(VerificationRule):
    """样本量一致性校验"""
    
    name = "sample_size_consistency"
    
    def check(self, table_data: Dict) -> List[VerificationIssue]:
        issues = []
        
        # 获取总样本量
        total_n = self._extract_total_n(table_data)
        if not total_n:
            return issues
        
        # 检查各组样本量加和
        group_ns = self._extract_group_ns(table_data)
        if group_ns:
            calculated_total = sum(group_ns.values())
            if calculated_total != total_n:
                issues.append(VerificationIssue(
                    rule_name=self.name,
                    severity='critical',
                    message=f'样本量加和不一致: 各组之和({calculated_total}) != 总计({total_n})',
                    location='table_header',
                    details={
                        'expected_total': total_n,
                        'calculated_total': calculated_total,
                        'group_ns': group_ns
                    }
                ))
        
        # 检查亚组样本量
        subgroup_issues = self._check_subgroup_consistency(table_data, total_n)
        issues.extend(subgroup_issues)
        
        return issues
    
    def _extract_total_n(self, table_data: Dict) -> Optional[int]:
        """提取总样本量"""
        # 从表头或表格元数据中提取
        title = table_data.get('title', '')
        # 匹配 n=XXX 或 N=XXX
        match = re.search(r'[nN]\s*=\s*(\d+)', title)
        if match:
            return int(match.group(1))
        
        # 从第一行/第一列查找
        rows = table_data.get('rows', [])
        for row in rows:
            for cell in row.get('cells', []):
                value = cell.get('value', '')
                match = re.search(r'[nN]\s*=\s*(\d+)', value)
                if match:
                    return int(match.group(1))
        
        return None
    
    def _extract_group_ns(self, table_data: Dict) -> Dict[str, int]:
        """提取各组样本量"""
        group_ns = {}
        rows = table_data.get('rows', [])
        
        for row in rows:
            cells = row.get('cells', [])
            if len(cells) >= 2:
                # 假设第一列是组名，第二列是n值
                group_name = cells[0].get('value', '')
                n_value = cells[1].get('value', '')
                
                # 提取数字
                match = re.search(r'\d+', str(n_value))
                if match and group_name:
                    group_ns[group_name] = int(match.group())
        
        return group_ns
    
    def _check_subgroup_consistency(self, table_data: Dict, total_n: int) -> List[VerificationIssue]:
        """检查亚组一致性"""
        issues = []
        rows = table_data.get('rows', [])
        
        for row_idx, row in enumerate(rows):
            cells = row.get('cells', [])
            for cell_idx, cell in enumerate(cells):
                value = cell.get('value', '')
                
                # 检查是否是百分比行
                if '%' in str(value):
                    # 查找对应的n值
                    n_cell = self._find_corresponding_n(cells, cell_idx)
                    if n_cell:
                        try:
                            n_val = int(re.search(r'\d+', str(n_cell)).group())
                            pct_val = float(str(value).replace('%', ''))
                            
                            # 验证百分比计算
                            expected_pct = (n_val / total_n) * 100
                            if abs(expected_pct - pct_val) > 1.0:  # 允许1%误差
                                issues.append(VerificationIssue(
                                    rule_name=self.name,
                                    severity='warning',
                                    message=f'百分比计算可能错误: 行{row_idx+1}, 列{cell_idx+1}',
                                    location=f'row_{row_idx}_col_{cell_idx}',
                                    details={
                                        'n_value': n_val,
                                        'reported_pct': pct_val,
                                        'calculated_pct': round(expected_pct, 1)
                                    }
                                ))
                        except (ValueError, AttributeError):
                            pass
        
        return issues
    
    def _find_corresponding_n(self, cells: List[Dict], pct_idx: int) -> Optional[str]:
        """找到百分比对应的n值"""
        # 简单的启发式：找前面的数字单元格
        for i in range(pct_idx - 1, -1, -1):
            value = str(cells[i].get('value', ''))
            if re.match(r'^\d+$', value):
                return value
        return None


class PercentageValidityRule(VerificationRule):
    """百分比合理性校验"""
    
    name = "percentage_validity"
    
    def check(self, table_data: Dict) -> List[VerificationIssue]:
        issues = []
        rows = table_data.get('rows', [])
        
        for row_idx, row in enumerate(rows):
            pct_cells = []
            
            for cell_idx, cell in enumerate(row.get('cells', [])):
                value = str(cell.get('value', ''))
                
                # 提取百分比
                if '%' in value:
                    try:
                        pct_val = float(value.replace('%', '').replace('<', '').replace('>', '').strip())
                        pct_cells.append({
                            'value': pct_val,
                            'row': row_idx,
                            'col': cell_idx,
                            'raw': value
                        })
                        
                        # 检查范围
                        if pct_val < 0 or pct_val > 100:
                            issues.append(VerificationIssue(
                                rule_name=self.name,
                                severity='critical',
                                message=f'百分比超出有效范围(0-100%): {value}',
                                location=f'row_{row_idx}_col_{cell_idx}',
                                details={'value': pct_val}
                            ))
                    except ValueError:
                        pass
            
            # 检查同列百分比是否加和为100%
            if len(pct_cells) >= 2:
                total_pct = sum(p['value'] for p in pct_cells)
                if abs(total_pct - 100) > 2.0:  # 允许2%误差
                    # 检查是否可能是累积百分比
                    if not self._is_cumulative_pattern(pct_cells):
                        issues.append(VerificationIssue(
                            rule_name=self.name,
                            severity='warning',
                            message=f'同行百分比之和不等于100%: 总和为{total_pct:.1f}%',
                            location=f'row_{row_idx}',
                            details={
                                'cells': pct_cells,
                                'sum': total_pct
                            }
                        ))
        
        return issues
    
    def _is_cumulative_pattern(self, pct_cells: List[Dict]) -> bool:
        """检查是否是累积百分比模式"""
        if len(pct_cells) < 2:
            return False
        
        values = [p['value'] for p in pct_cells]
        # 如果递增，可能是累积
        if all(values[i] <= values[i+1] for i in range(len(values)-1)):
            return True
        return False


class StatisticPValueRule(VerificationRule):
    """统计量-P值一致性校验"""
    
    name = "statistic_pvalue_consistency"
    
    def check(self, table_data: Dict) -> List[VerificationIssue]:
        issues = []
        rows = table_data.get('rows', [])
        
        for row_idx, row in enumerate(rows):
            stat_value = None
            stat_type = None
            p_value = None
            
            for cell in row.get('cells', []):
                value = str(cell.get('value', ''))
                cell_type = cell.get('type', 'text')
                
                # 提取统计量
                if cell_type in ['t_stat', 'z_stat', 'chi2_stat']:
                    try:
                        stat_value = abs(float(value))
                        stat_type = cell_type
                    except ValueError:
                        pass
                
                # 提取P值
                if cell_type == 'p_value' or 'P' in value.upper():
                    try:
                        p_str = value.replace('<', '').replace('>', '').replace('=', '').strip()
                        p_value = float(p_str)
                    except ValueError:
                        pass
            
            # 检查一致性
            if stat_value and p_value and stat_type:
                is_consistent = self._check_consistency(stat_value, p_value, stat_type)
                if not is_consistent:
                    issues.append(VerificationIssue(
                        rule_name=self.name,
                        severity='warning',
                        message=f'统计量与P值可能不一致: {stat_type}={stat_value}, P={p_value}',
                        location=f'row_{row_idx}',
                        details={
                            'stat_type': stat_type,
                            'stat_value': stat_value,
                            'p_value': p_value
                        }
                    ))
        
        return issues
    
    def _check_consistency(self, stat: float, p: float, stat_type: str) -> bool:
        """检查统计量与P值是否一致"""
        if stat_type in ['t_stat', 'z_stat']:
            # |t|或|Z| > 1.96 应该对应 P < 0.05
            if stat > 3.29 and p >= 0.001:
                return False
            elif stat > 2.58 and p >= 0.01:
                return False
            elif stat > 1.96 and p >= 0.05:
                return False
        
        elif stat_type == 'chi2_stat':
            # 大χ²应对应小P值
            if stat > 10 and p >= 0.01:
                return False
        
        return True


class ConfidenceIntervalRule(VerificationRule):
    """置信区间逻辑校验"""
    
    name = "confidence_interval"
    
    def check(self, table_data: Dict) -> List[VerificationIssue]:
        issues = []
        rows = table_data.get('rows', [])
        
        for row_idx, row in enumerate(rows):
            for cell_idx, cell in enumerate(row.get('cells', [])):
                value = str(cell.get('value', ''))
                
                # 解析CI
                ci = self._parse_ci(value)
                if ci:
                    lower, upper = ci
                    
                    # 检查下限 < 上限
                    if lower >= upper:
                        issues.append(VerificationIssue(
                            rule_name=self.name,
                            severity='critical',
                            message=f'置信区间下限>=上限: [{lower}, {upper}]',
                            location=f'row_{row_idx}_col_{cell_idx}',
                            details={'lower': lower, 'upper': upper}
                        ))
                    
                    # 检查宽度合理性
                    width = upper - lower
                    if width / abs((lower + upper) / 2) > 5:  # 宽度超过中点5倍
                        issues.append(VerificationIssue(
                            rule_name=self.name,
                            severity='info',
                            message=f'置信区间异常宽: 宽度={width:.2f}',
                            location=f'row_{row_idx}_col_{cell_idx}',
                            details={'width': width}
                        ))
        
        return issues
    
    def _parse_ci(self, value: str) -> Optional[tuple]:
        """解析置信区间"""
        # 匹配格式: 0.75 (0.60-0.93) 或 0.75-0.93
        patterns = [
            r'([\d.]+)\s*[-\u2013]\s*([\d.]+)',  # 0.60-0.93
            r'\(\s*([\d.]+)\s*[-\u2013]\s*([\d.]+)\s*\)',  # (0.60-0.93)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, value)
            if match:
                try:
                    lower = float(match.group(1))
                    upper = float(match.group(2))
                    return (lower, upper)
                except ValueError:
                    pass
        
        return None


class TableLogicVerifier:
    """表格逻辑校验器主类"""
    
    def __init__(self):
        self.rules = [
            SampleSizeConsistencyRule(),
            PercentageValidityRule(),
            StatisticPValueRule(),
            ConfidenceIntervalRule()
        ]
    
    def verify(self, table_data: Dict) -> Dict:
        """
        运行完整校验
        
        Returns:
            校验报告
        """
        all_issues = []
        
        for rule in self.rules:
            issues = rule.check(table_data)
            all_issues.extend(issues)
        
        # 分类问题
        critical = [i for i in all_issues if i.severity == 'critical']
        warning = [i for i in all_issues if i.severity == 'warning']
        info = [i for i in all_issues if i.severity == 'info']
        
        # 判定结果
        if critical:
            status = 'failed'
            action = 'needs_human_review'
        elif warning:
            status = 'passed_with_warnings'
            action = 'optional_review'
        else:
            status = 'passed'
            action = 'accept'
        
        return {
            'status': status,
            'action': action,
            'summary': {
                'total_rules': len(self.rules),
                'critical_issues': len(critical),
                'warning_issues': len(warning),
                'info_issues': len(info)
            },
            'issues': [
                {
                    'rule': i.rule_name,
                    'severity': i.severity,
                    'message': i.message,
                    'location': i.location,
                    'details': i.details
                }
                for i in all_issues
            ]
        }


if __name__ == '__main__':
    # 测试
    test_table = {
        'title': 'Patient Baseline Characteristics (n=200)',
        'rows': [
            {
                'cells': [
                    {'value': 'Group', 'type': 'text'},
                    {'value': 'n=98', 'type': 'text'},
                    {'value': 'n=102', 'type': 'text'},
                    {'value': 'P value', 'type': 'text'}
                ]
            },
            {
                'cells': [
                    {'value': 'Age', 'type': 'text'},
                    {'value': '55.2±8.3', 'type': 'text'},
                    {'value': '54.8±9.1', 'type': 'text'},
                    {'value': '0.74', 'type': 'p_value'}
                ]
            },
            {
                'cells': [
                    {'value': 'Male', 'type': 'text'},
                    {'value': '48 (49.0%)', 'type': 'percentage'},
                    {'value': '52 (51.0%)', 'type': 'percentage'},
                    {'value': '0.82', 'type': 'p_value'}
                ]
            }
        ]
    }
    
    verifier = TableLogicVerifier()
    report = verifier.verify(test_table)
    
    print(f"校验状态: {report['status']}")
    print(f"问题统计: {report['summary']}")
    for issue in report['issues']:
        print(f"  [{issue['severity']}] {issue['message']}")
