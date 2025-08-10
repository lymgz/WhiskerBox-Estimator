#!/usr/bin/env python3
"""
简洁的箱线图数据转换命令行工具
基于Wan 2014和Luo 2018统计方法
"""

import argparse
import sys
import json
from statistical_converter import StatisticalConverter

def parse_number_list(text):
    """解析数字列表，支持逗号分隔"""
    if not text:
        return []
    try:
        return [float(x.strip()) for x in text.split(',') if x.strip()]
    except ValueError as e:
        raise ValueError(f"无法解析数字列表 '{text}': {e}")

def main():
    parser = argparse.ArgumentParser(
        description='箱线图数据转换为Mean±SD',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基础转换（只有四分位数）
  python simple_converter.py --q1 10,12,9 --q2 15,16,14 --q3 20,21,19 --n1 30 --n2 30

  # 完整转换（包含须）
  python simple_converter.py --q1 10,12 --q2 15,16 --q3 20,21 --upper 25,26 --lower 5,6 --n1 30 --n2 30

  # 单组转换
  python simple_converter.py --q1 10 --q2 15 --q3 20 --n1 30 --single

  # 详细输出
  python simple_converter.py --q1 10,12 --q2 15,16 --q3 20,21 --n1 30 --n2 30 --verbose
        """
    )
    
    # 必需参数
    parser.add_argument('--q1', required=True, help='Q1四分位数，逗号分隔多个值')
    parser.add_argument('--q2', required=True, help='Q2中位数，逗号分隔多个值')
    parser.add_argument('--q3', required=True, help='Q3四分位数，逗号分隔多个值')
    parser.add_argument('--n1', type=int, required=True, help='第一组样本量')
    
    # 可选参数
    parser.add_argument('--n2', type=int, help='第二组样本量（两组比较时需要）')
    parser.add_argument('--upper', help='上须，逗号分隔多个值')
    parser.add_argument('--lower', help='下须，逗号分隔多个值')
    parser.add_argument('--upper-outliers', help='上异常值，逗号分隔')
    parser.add_argument('--lower-outliers', help='下异常值，逗号分隔')
    
    # 模式选项
    parser.add_argument('--single', action='store_true', help='单组转换模式')
    parser.add_argument('--method', choices=['auto', 'wan2014', 'luo2018', 'simple'], 
                       default='auto', help='转换方法（默认：auto）')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    args = parser.parse_args()
    
    try:
        # 解析输入数据
        q1_list = parse_number_list(args.q1)
        q2_list = parse_number_list(args.q2)
        q3_list = parse_number_list(args.q3)
        
        # 验证数据长度一致性
        if not (len(q1_list) == len(q2_list) == len(q3_list)):
            raise ValueError("Q1、Q2、Q3的数据数量必须相同")
        
        if len(q1_list) == 0:
            raise ValueError("至少需要一组数据")
        
        # 解析可选数据
        upper_list = parse_number_list(args.upper) if args.upper else []
        lower_list = parse_number_list(args.lower) if args.lower else []
        upper_outliers = parse_number_list(args.upper_outliers) if args.upper_outliers else []
        lower_outliers = parse_number_list(args.lower_outliers) if args.lower_outliers else []
        
        # 创建转换器
        converter = StatisticalConverter()
        
        # 处理数据
        if args.single or args.n2 is None:
            # 单组模式
            process_single_group(converter, q1_list, q2_list, q3_list, upper_list, lower_list,
                                upper_outliers, lower_outliers, args.n1, args.method, args.verbose, args.json)
        else:
            # 两组比较模式
            if len(q1_list) != 2:
                raise ValueError("两组比较模式需要恰好2组数据")
            
            process_two_groups(converter, q1_list, q2_list, q3_list, upper_list, lower_list,
                             upper_outliers, lower_outliers, args.n1, args.n2, args.method, args.verbose, args.json)
            
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

def create_boxplot_data(q1, q2, q3, upper=None, lower=None, upper_outliers=None, lower_outliers=None):
    """创建箱线图数据字典"""
    data = {
        'q1': q1,
        'q2': q2,
        'q3': q3
    }
    
    if upper is not None:
        data['upper_whisker'] = upper
    if lower is not None:
        data['lower_whisker'] = lower
    if upper_outliers:
        data['upper_outliers'] = upper_outliers
    if lower_outliers:
        data['lower_outliers'] = lower_outliers
    
    return data

def process_single_group(converter, q1_list, q2_list, q3_list, upper_list, lower_list,
                        upper_outliers, lower_outliers, n, method, verbose, json_output):
    """处理单组数据"""
    results = []
    
    for i in range(len(q1_list)):
        # 获取当前组数据
        upper = upper_list[i] if i < len(upper_list) else None
        lower = lower_list[i] if i < len(lower_list) else None
        
        # 创建箱线图数据
        boxplot_data = create_boxplot_data(
            q1_list[i], q2_list[i], q3_list[i], upper, lower, upper_outliers, lower_outliers
        )
        
        # 转换
        result = converter.convert_boxplot_to_stats(boxplot_data, n, method)
        result['group_index'] = i + 1
        results.append(result)
    
    # 输出结果
    if json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_single_group_results(results, verbose)

def process_two_groups(converter, q1_list, q2_list, q3_list, upper_list, lower_list,
                      upper_outliers, lower_outliers, n1, n2, method, verbose, json_output):
    """处理两组比较数据"""
    # 处理第一组
    boxplot1 = create_boxplot_data(
        q1_list[0], q2_list[0], q3_list[0],
        upper_list[0] if upper_list else None,
        lower_list[0] if lower_list else None,
        upper_outliers, lower_outliers
    )
    
    # 处理第二组
    boxplot2 = create_boxplot_data(
        q1_list[1], q2_list[1], q3_list[1],
        upper_list[1] if len(upper_list) > 1 else None,
        lower_list[1] if len(lower_list) > 1 else None,
        upper_outliers, lower_outliers
    )
    
    # 转换
    result1 = converter.convert_boxplot_to_stats(boxplot1, n1, method)
    result2 = converter.convert_boxplot_to_stats(boxplot2, n2, method)
    
    # 计算差值
    diff_result = converter.calculate_difference_stats(result1, result2)
    
    # 输出结果
    if json_output:
        output = {
            'group1': result1,
            'group2': result2,
            'difference': diff_result
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_two_group_results(result1, result2, diff_result, verbose)

def print_single_group_results(results, verbose):
    """打印单组结果"""
    print("=" * 60)
    print("单组转换结果")
    print("=" * 60)
    
    for result in results:
        print(f"\n组 {result['group_index']}:")
        print(f"  Mean: {result['mean']:.3f}")
        print(f"  SD:   {result['sd']:.3f}")
        print(f"  等级: {result['data_level']} ({result['precision_estimate']})")
        print(f"  方法: {result['method_used']}")
        
        if verbose:
            print(f"  详细: {result.get('method_details', 'N/A')}")
            if 'distribution_assessment' in result:
                dist = result['distribution_assessment']
                print(f"  分布: 对称性={dist['is_symmetric']}, IQR={dist['iqr']:.3f}")

def print_two_group_results(result1, result2, diff_result, verbose):
    """打印两组比较结果"""
    print("=" * 60)
    print("两组比较结果")
    print("=" * 60)
    
    print(f"\n基线组 (n={result1['sample_size']}):")
    print(f"  Mean: {result1['mean']:.3f}")
    print(f"  SD:   {result1['sd']:.3f}")
    print(f"  等级: {result1['data_level']} ({result1['precision_estimate']})")
    
    print(f"\n干预组 (n={result2['sample_size']}):")
    print(f"  Mean: {result2['mean']:.3f}")
    print(f"  SD:   {result2['sd']:.3f}")
    print(f"  等级: {result2['data_level']} ({result2['precision_estimate']})")
    
    print(f"\n差值分析:")
    print(f"  差值Mean: {diff_result['difference_mean']:.3f}")
    print(f"  差值SD:   {diff_result['difference_sd']:.3f}")
    print(f"  效应量:   {diff_result['cohens_d']:.3f}")
    print(f"  95%CI:    ({diff_result['confidence_interval_95'][0]:.3f}, {diff_result['confidence_interval_95'][1]:.3f})")
    
    if verbose:
        print(f"\n详细信息:")
        print(f"  基线组方法: {result1.get('method_details', 'N/A')}")
        print(f"  干预组方法: {result2.get('method_details', 'N/A')}")
        print(f"  计算公式: {diff_result['calculation_details']['formula']}")

if __name__ == "__main__":
    main()
