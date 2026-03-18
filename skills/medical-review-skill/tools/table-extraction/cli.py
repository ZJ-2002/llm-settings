#!/usr/bin/env python3
"""
双轨制表格提取系统 - 命令行接口
"""

import argparse
import json
import sys
from pathlib import Path

# 添加core到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.extractor import DualTrackExtractor


def main():
    parser = argparse.ArgumentParser(
        description='双轨制表格提取系统 - 从PDF提取医学文献表格'
    )
    
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--page', '-p', type=int, help='指定页面（1-based）')
    parser.add_argument('--output', '-o', help='输出JSON文件路径')
    parser.add_argument('--report', '-r', help='输出复核报告路径')
    parser.add_argument('--auto-accept', type=float, default=0.90,
                       help='自动接受阈值（默认0.90）')
    parser.add_argument('--review-threshold', type=float, default=0.70,
                       help='需要复核阈值（默认0.70）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出')
    
    args = parser.parse_args()
    
    # 配置
    config = {
        'auto_accept_threshold': args.auto_accept,
        'review_threshold': args.review_threshold
    }
    
    # 初始化提取器
    print(f"初始化双轨制表格提取系统...")
    print(f"配置: 自动接受阈值={args.auto_accept}, 复核阈值={args.review_threshold}")
    extractor = DualTrackExtractor(config)
    
    # 提取表格
    page = args.page - 1 if args.page else None  # 转换为0-based
    print(f"\n开始提取: {args.pdf_path}")
    if args.page:
        print(f"指定页面: {args.page}")
    
    try:
        tables = extractor.extract_from_pdf(args.pdf_path, page)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 输出结果
    print(f"\n提取完成！共 {len(tables)} 个表格")
    
    for i, table in enumerate(tables):
        print(f"\n{'='*60}")
        print(f"表格 {i+1}: {table.table_id}")
        print(f"  页面: {table.page_num + 1}")
        print(f"  复杂度: {table.complexity_score:.2f}")
        print(f"  整体置信度: {table.confidence_assessment['overall_score']:.2f}")
        print(f"  需要复核: {'是' if table.needs_review else '否'}")
        
        if table.needs_review:
            print(f"  - A级单元格: {table.confidence_assessment['high_confidence_count']}")
            print(f"  - B级单元格: {table.confidence_assessment['medium_confidence_count']}")
            print(f"  - C级单元格: {table.confidence_assessment['low_confidence_count']}")
        
        if table.verification_result:
            status = table.verification_result['status']
            status_icon = '✅' if status == 'passed' else '⚠️' if status == 'passed_with_warnings' else '❌'
            print(f"  校验状态: {status_icon} {status}")
    
    # 保存JSON
    if args.output:
        output_data = {
            'source_pdf': args.pdf_path,
            'extraction_timestamp': tables[0].extraction_timestamp if tables else '',
            'table_count': len(tables),
            'tables': []
        }
        
        for table in tables:
            output_data['tables'].append({
                'table_id': table.table_id,
                'page_num': table.page_num + 1,  # 转换为1-based
                'complexity_score': table.complexity_score,
                'title': table.title,
                'headers': table.headers,
                'rows': table.rows,
                'confidence_assessment': table.confidence_assessment,
                'verification_result': table.verification_result,
                'needs_review': table.needs_review
            })
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {args.output}")
    
    # 保存复核报告
    if args.report:
        reports = []
        for table in tables:
            if table.needs_review:
                report = extractor.generate_review_report(table)
                reports.append(report)
        
        if reports:
            with open(args.report, 'w', encoding='utf-8') as f:
                f.write('\n\n---\n\n'.join(reports))
            print(f"复核报告已保存到: {args.report}")
        else:
            print(f"\n无需复核，未生成报告")
    
    # 详细输出
    if args.verbose:
        print(f"\n{'='*60}")
        print("详细数据:")
        for table in tables:
            print(f"\n表格 {table.table_id}:")
            print(json.dumps({
                'headers': table.headers,
                'rows': table.rows,
                'footnotes': table.footnotes
            }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
