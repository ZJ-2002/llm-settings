#!/usr/bin/env python3
"""
置信度评估器 - 评估提取数据的置信度
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re


class ConfidenceLevel(Enum):
    """置信度等级"""
    HIGH = "A"      # >=90%
    MEDIUM = "B"    # 70-90%
    LOW = "C"       # <70%


@dataclass
class ConfidenceAssessment:
    """置信度评估结果"""
    score: float
    level: ConfidenceLevel
    factors: Dict[str, float]
    needs_review: bool
    review_reason: Optional[str]


class ConfidenceAssessor:
    """置信度评估器"""
    
    # 置信度阈值
    HIGH_THRESHOLD = 0.90
    MEDIUM_THRESHOLD = 0.70
    
    def __init__(self):
        """初始化评估器"""
        self.weights = {
            'ocr_quality': 0.30,
            'numeric_reasonableness': 0.25,
            'format_compliance': 0.25,
            'context_consistency': 0.20
        }
    
    def assess_cell(self, value: str, cell_type: str = 'text', 
                   context: Optional[Dict] = None) -> ConfidenceAssessment:
        """评估单个单元格的置信度"""
        factors = {}
        
        # 因素1: OCR质量
        factors['ocr_quality'] = self._assess_ocr_quality(value)
        
        # 因素2: 数值合理性
        if cell_type in ['number', 'percentage', 'p_value', 'ci']:
            factors['numeric_reasonableness'] = self._assess_numeric_reasonableness(value, cell_type)
        else:
            factors['numeric_reasonableness'] = 1.0
        
        # 因素3: 格式规范性
        factors['format_compliance'] = self._assess_format_compliance(value, cell_type)
        
        # 因素4: 上下文一致性
        factors['context_consistency'] = self._assess_context_consistency(value, context) if context else 0.8
        
        # 计算加权总分
        total_score = sum(factors[name] * self.weights[name] for name in factors)
        
        # 确定等级
        if total_score >= self.HIGH_THRESHOLD:
            level = ConfidenceLevel.HIGH
            needs_review = False
        elif total_score >= self.MEDIUM_THRESHOLD:
            level = ConfidenceLevel.MEDIUM
            needs_review = True
        else:
            level = ConfidenceLevel.LOW
            needs_review = True
        
        review_reason = self._generate_review_reason(factors, level)
        
        return ConfidenceAssessment(
            score=round(total_score, 3),
            level=level,
            factors=factors,
            needs_review=needs_review,
            review_reason=review_reason
        )
    
    def _assess_ocr_quality(self, text: str) -> float:
        """评估OCR质量"""
        if not text:
            return 0.0
        
        score = 1.0
        
        # 检测乱码字符
        weird_chars = len([c for c in text if ord(c) > 127 and not c.isalpha()])
        score -= weird_chars * 0.05
        
        # 检测异常长的数字
        long_numbers = re.findall(r'\d{6,}', text)
        score -= len(long_numbers) * 0.1
        
        # 检测大小写混乱
        if re.search(r'[a-z][A-Z][a-z]', text):
            score -= 0.15
        
        return max(score, 0.0)
    
    def _assess_numeric_reasonableness(self, text: str, num_type: str) -> float:
        """评估数值合理性"""
        score = 1.0
        
        try:
            if num_type == 'percentage':
                # 去除%和空格
                val_str = text.replace('%', '').replace('<', '').replace('>', '').strip()
                val = float(val_str)
                if val < 0 or val > 100:
                    score -= 0.5
                if val > 1000:  # 明显错误
                    score -= 0.3
                    
            elif num_type == 'p_value':
                val_str = text.replace('<', '').replace('>', '').replace('=', '').strip()
                val = float(val_str)
                if val < 0 or val > 1:
                    score -= 0.6
                    
            elif num_type == 'number':
                val = float(text.replace(',', ''))
                if abs(val) > 1e9:
                    score -= 0.2
                    
        except (ValueError, TypeError):
            score -= 0.4
        
        return max(score, 0.0)
    
    def _assess_format_compliance(self, text: str, cell_type: str) -> float:
        """评估格式规范性"""
        score = 1.0
        
        if cell_type == 'percentage':
            if '%' not in text and not text.replace('.', '').isdigit():
                score -= 0.2
                
        elif cell_type == 'p_value':
            if not re.match(r'[<>=]?\s*0\.\d+', text):
                score -= 0.15
                
        elif cell_type == 'ci':
            if '-' not in text and 'to' not in text.lower():
                score -= 0.2
        
        return max(score, 0.0)
    
    def _assess_context_consistency(self, value: str, context: Dict) -> float:
        """评估上下文一致性"""
        # 简化的上下文检查
        return 0.85
    
    def _generate_review_reason(self, factors: Dict, level: ConfidenceLevel) -> Optional[str]:
        """生成复核原因"""
        if level == ConfidenceLevel.HIGH:
            return None
        
        reasons = []
        if factors.get('ocr_quality', 1.0) < 0.7:
            reasons.append('OCR质量低')
        if factors.get('numeric_reasonableness', 1.0) < 0.7:
            reasons.append('数值可能不合理')
        if factors.get('format_compliance', 1.0) < 0.7:
            reasons.append('格式不规范')
        
        return '；'.join(reasons) if reasons else '置信度不足'


if __name__ == '__main__':
    # 测试
    assessor = ConfidenceAssessor()
    
    test_cases = [
        ('48', 'number'),
        ('48.5%', 'percentage'),
        ('<0.001', 'p_value'),
        ('1.23 (0.98-1.54)', 'ci'),
        ('abc123', 'text'),
    ]
    
    for value, cell_type in test_cases:
        result = assessor.assess_cell(value, cell_type)
        print(f"{value} ({cell_type}): {result.level.value}级 (得分: {result.score})")
