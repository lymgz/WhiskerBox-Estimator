#!/usr/bin/env python3
"""
CSV批量箱线图数据转换工具
支持动态列数和最不利情况分析
"""

import csv
import os
import sys
import json
from typing import Dict, List, Tuple, Optional
from statistical_converter import StatisticalConverter

class CSVConverter:
    def __init__(self):
        self.converter = StatisticalConverter()
        self.template_filename = "template.csv"
        self.data_filename = "data.csv"
        
    def generate_template(self, situations_count: int = 4) -> str:
        """生成CSV模板文件"""
        template_content = []
        
        # 基线组
        header = ["Baseline"] + [f"Case{i+1}" for i in range(situations_count)]
        template_content.append(header)
        
        data_items = ["Upper_Outlier", "Upper_Whisker", "Q3", "Q2", "Q1", "Lower_Whisker", "Lower_Outlier", "Sample_Size"]
        for item in data_items:
            row = [item] + [""] * situations_count
            template_content.append(row)
        
        # 空行分隔
        template_content.append([""] * (situations_count + 1))
        
        # 干预组
        header = ["Intervention"] + [f"Case{i+1}" for i in range(situations_count)]
        template_content.append(header)
        
        for item in data_items:
            row = [item] + [""] * situations_count
            template_content.append(row)
        
        # 写入文件
        with open(self.template_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(template_content)
        
        return self.template_filename
    
    def read_csv_data(self, filename: str) -> Dict:
        """读取CSV数据并解析"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"找不到文件: {filename}")
        
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        return self._parse_csv_structure(rows)
    
    def _parse_csv_structure(self, rows: List[List[str]]) -> Dict:
        """解析CSV结构，支持动态列数"""
        groups = {}
        current_group = None
        current_data = {}
        
        for row in rows:
            if not row or all(cell.strip() == "" for cell in row):
                # 空行，结束当前组
                if current_group and current_data:
                    groups[current_group] = current_data
                    current_data = {}
                continue
            
            first_cell = row[0].strip()
            
            # 检查是否是组标题 (支持中英文)
            if first_cell in ["基线组", "干预组", "Baseline", "Intervention"] or first_cell.endswith("组"):
                if current_group and current_data:
                    groups[current_group] = current_data
                
                current_group = first_cell
                current_data = {}
                
                # 检测情况数量
                situations = [cell.strip() for cell in row[1:] if cell.strip()]
                current_data['situations'] = situations
                current_data['situation_count'] = len(situations)
                current_data['data'] = {}
                continue
            
            # 数据行 (支持中英文标签)
            chinese_labels = ["上异常值", "上须", "Q3", "Q2", "Q1", "下须", "下异常值", "样本量"]
            english_labels = ["Upper_Outlier", "Upper_Whisker", "Q3", "Q2", "Q1", "Lower_Whisker", "Lower_Outlier", "Sample_Size"]
            
            if current_group and first_cell in chinese_labels + english_labels:
                # 标准化标签为中文（内部处理统一用中文）
                label_mapping = {
                    "Upper_Outlier": "上异常值",
                    "Upper_Whisker": "上须", 
                    "Lower_Whisker": "下须",
                    "Lower_Outlier": "下异常值",
                    "Sample_Size": "样本量"
                }
                normalized_label = label_mapping.get(first_cell, first_cell)
                values = []
                for cell in row[1:]:
                    cell_value = cell.strip()
                    if cell_value:
                        try:
                            values.append(float(cell_value))
                        except ValueError:
                            values.append(None)
                    else:
                        values.append(None)
                
                current_data['data'][normalized_label] = values
        
        # 处理最后一组
        if current_group and current_data:
            groups[current_group] = current_data
        
        return groups
    
    def analyze_data_levels(self, groups: Dict) -> Dict:
        """分析每个情况的数据等级"""
        analysis = {}
        
        for group_name, group_data in groups.items():
            situations_analysis = []
            situation_count = group_data.get('situation_count', 0)
            
            for i in range(situation_count):
                situation_data = self._extract_situation_data(group_data, i)
                level = self._determine_data_level(situation_data)
                
                situations_analysis.append({
                    'situation_index': i + 1,
                    'situation_name': group_data['situations'][i] if i < len(group_data['situations']) else f"情况{i+1}",
                    'data_level': level,
                    'available_data': self._list_available_data(situation_data),
                    'data': situation_data
                })
            
            # 找出最不利情况（最低等级）
            min_level = min([s['data_level'] for s in situations_analysis]) if situations_analysis else 0
            
            analysis[group_name] = {
                'situations': situations_analysis,
                'min_level': min_level,
                'situation_count': situation_count,
                'conservative_strategy': min_level < max([s['data_level'] for s in situations_analysis]) if situations_analysis else False
            }
        
        return analysis
    
    def _extract_situation_data(self, group_data: Dict, situation_index: int) -> Dict:
        """提取特定情况的数据"""
        situation_data = {}
        
        for data_type, values in group_data['data'].items():
            if situation_index < len(values) and values[situation_index] is not None:
                situation_data[data_type] = values[situation_index]
        
        return situation_data
    
    def _determine_data_level(self, situation_data: Dict) -> int:
        """确定数据等级"""
        required_basic = ['Q1', 'Q2', 'Q3', '样本量']
        level1_additions = ['上须', '下须']
        level2_additions = ['上异常值', '下异常值']
        
        # 检查基础数据
        if not all(key in situation_data for key in required_basic):
            return -1  # 数据不完整
        
        # 检查等级1数据
        has_whiskers = any(key in situation_data for key in level1_additions)
        
        # 检查等级2数据
        has_outliers = any(key in situation_data for key in level2_additions)
        
        if has_outliers and has_whiskers:
            return 2
        elif has_whiskers:
            return 1
        else:
            return 0
    
    def _list_available_data(self, situation_data: Dict) -> List[str]:
        """列出可用的数据项"""
        return list(situation_data.keys())
    
    def convert_csv_data(self, filename: str, verbose: bool = False) -> Dict:
        """转换CSV数据"""
        # 读取数据
        groups = self.read_csv_data(filename)
        
        # 分析数据等级
        analysis = self.analyze_data_levels(groups)
        
        # 执行转换
        results = {}
        
        for group_name, group_analysis in analysis.items():
            group_results = []
            min_level = group_analysis['min_level']
            
            if verbose:
                print(f"\n=== {group_name} 分析 ===")
                print(f"检测到 {group_analysis['situation_count']} 个情况")
                print(f"最不利等级: {min_level}")
                if group_analysis['conservative_strategy']:
                    print("⚠️  采用保守估计策略")
            
            for situation in group_analysis['situations']:
                situation_data = situation['data']
                
                if situation_data.get('样本量') is None:
                    if verbose:
                        print(f"跳过 {situation['situation_name']}: 缺少样本量")
                    continue
                
                # 创建箱线图数据
                boxplot_data = self._create_boxplot_data(situation_data, min_level)
                
                # 转换
                try:
                    result = self.converter.convert_boxplot_to_stats(
                        boxplot_data, 
                        int(situation_data['样本量']), 
                        'auto'
                    )
                    
                    result['situation_name'] = situation['situation_name']
                    result['original_level'] = situation['data_level']
                    result['used_level'] = min_level
                    result['conservative_estimate'] = situation['data_level'] > min_level
                    
                    group_results.append(result)
                    
                    if verbose:
                        print(f"{situation['situation_name']}: Mean={result['mean']:.3f}, SD={result['sd']:.3f} (等级{min_level})")
                
                except Exception as e:
                    if verbose:
                        print(f"转换失败 {situation['situation_name']}: {e}")
            
            results[group_name] = group_results
        
        return {
            'results': results,
            'analysis': analysis,
            'summary': self._generate_summary(analysis, results)
        }
    
    def _create_boxplot_data(self, situation_data: Dict, target_level: int) -> Dict:
        """根据目标等级创建箱线图数据"""
        boxplot_data = {
            'q1': situation_data.get('Q1'),
            'q2': situation_data.get('Q2'),
            'q3': situation_data.get('Q3')
        }
        
        if target_level >= 1:
            if '上须' in situation_data:
                boxplot_data['upper_whisker'] = situation_data['上须']
            if '下须' in situation_data:
                boxplot_data['lower_whisker'] = situation_data['下须']
        
        if target_level >= 2:
            outliers = []
            if '上异常值' in situation_data:
                outliers.append(situation_data['上异常值'])
            if '下异常值' in situation_data:
                outliers.append(situation_data['下异常值'])
            if outliers:
                boxplot_data['outliers'] = outliers
        
        return boxplot_data
    
    def _generate_summary(self, analysis: Dict, results: Dict) -> Dict:
        """生成分析摘要"""
        total_situations = sum(group['situation_count'] for group in analysis.values())
        conservative_groups = sum(1 for group in analysis.values() if group['conservative_strategy'])
        
        min_levels = [group['min_level'] for group in analysis.values()]
        overall_min_level = min(min_levels) if min_levels else 0
        
        return {
            'total_groups': len(analysis),
            'total_situations': total_situations,
            'conservative_groups': conservative_groups,
            'overall_min_level': overall_min_level,
            'precision_estimate': self._get_precision_description(overall_min_level),
            'recommendations': self._generate_recommendations(analysis)
        }
    
    def _get_precision_description(self, level: int) -> str:
        """获取精度描述"""
        descriptions = {
            -1: "数据不完整",
            0: "中等精度 (误差15-25%)",
            1: "高精度 (误差8-15%)",
            2: "最高精度 (误差5-10%)"
        }
        return descriptions.get(level, "未知精度")
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        for group_name, group_analysis in analysis.items():
            if group_analysis['conservative_strategy']:
                low_level_situations = [
                    s['situation_name'] for s in group_analysis['situations'] 
                    if s['data_level'] == group_analysis['min_level']
                ]
                recommendations.append(
                    f"{group_name}: 补充{', '.join(low_level_situations)}的须数据可提升整体精度"
                )
        
        return recommendations

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='CSV批量箱线图数据转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用步骤:
  1. 生成模板: python csv_converter.py --generate-template
  2. 填写数据: 编辑 template.csv，保存为 data.csv
  3. 转换数据: python csv_converter.py --convert data.csv
  
示例:
  python csv_converter.py --generate-template --situations 6
  python csv_converter.py --convert data.csv --verbose
  python csv_converter.py --convert data.csv --json
        """
    )
    
    parser.add_argument('--generate-template', action='store_true', help='生成CSV模板')
    parser.add_argument('--situations', type=int, default=4, help='模板中的情况数量 (默认: 4)')
    parser.add_argument('--convert', help='转换CSV文件')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    args = parser.parse_args()
    
    converter = CSVConverter()
    
    try:
        if args.generate_template:
            filename = converter.generate_template(args.situations)
            print(f"✓ 已生成模板文件: {filename}")
            print(f"  支持 {args.situations} 个情况")
            print(f"  请填写数据后保存为 data.csv")
            return
        
        if args.convert:
            print("=== CSV箱线图数据转换工具 ===\n")
            
            result = converter.convert_csv_data(args.convert, args.verbose)
            
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print_results(result, args.verbose)
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

def print_results(result: Dict, verbose: bool = False):
    """打印结果"""
    analysis = result['analysis']
    results = result['results']
    summary = result['summary']
    
    print("=" * 60)
    print("数据质量分析")
    print("=" * 60)
    
    for group_name, group_analysis in analysis.items():
        print(f"\n{group_name}:")
        for situation in group_analysis['situations']:
            level_desc = {-1: "❌ 不完整", 0: "⚠️  等级0", 1: "✓ 等级1", 2: "✓✓ 等级2"}
            print(f"  {situation['situation_name']}: {level_desc.get(situation['data_level'], '?')} "
                  f"({', '.join(situation['available_data'])})")
        
        if group_analysis['conservative_strategy']:
            print(f"  → 采用保守估计: 等级{group_analysis['min_level']}")
    
    print(f"\n整体精度: {summary['precision_estimate']}")
    
    if summary['recommendations']:
        print(f"\n改进建议:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")
    
    print("\n" + "=" * 60)
    print("转换结果")
    print("=" * 60)
    
    for group_name, group_results in results.items():
        print(f"\n{group_name}:")
        for result in group_results:
            conservative_mark = " (保守估计)" if result.get('conservative_estimate') else ""
            print(f"  {result['situation_name']}: Mean={result['mean']:.3f}, "
                  f"SD={result['sd']:.3f}{conservative_mark}")
            if verbose:
                print(f"    方法: {result['method_used']}, 等级: {result['used_level']}")

if __name__ == "__main__":
    main()
