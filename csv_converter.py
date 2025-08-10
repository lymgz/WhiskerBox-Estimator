#!/usr/bin/env python3
"""
CSV批量箱线图数据转换工具
支持动态列数和最不利情况分析
"""

import csv
import os
import sys
import json
import pandas as pd
import math
from datetime import datetime
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
    
    def calculate_group_comparison(self, group1_data: Dict, group2_data: Dict, 
                                 confidence_level: float = 0.95) -> Dict:
        """
        计算两组间的差异分析
        基于用户提供的公式：
        ΔMean = Mean₁ - Mean₂
        SD_diff = √(SD₁²/n₁ + SD₂²/n₂)
        CI = ΔMean ± z·SD_diff
        """
        delta_mean = group1_data['mean'] - group2_data['mean']
        
        # 计算差异的标准差
        sd_diff = math.sqrt(
            (group1_data['sd']**2 / group1_data['sample_size']) + 
            (group2_data['sd']**2 / group2_data['sample_size'])
        )
        
        # 计算置信区间
        z_score = self._get_z_score(confidence_level)
        ci_lower = delta_mean - z_score * sd_diff
        ci_upper = delta_mean + z_score * sd_diff
        
        # 计算效应量 (Cohen's d)
        pooled_sd = math.sqrt(
            ((group1_data['sample_size'] - 1) * group1_data['sd']**2 + 
             (group2_data['sample_size'] - 1) * group2_data['sd']**2) / 
            (group1_data['sample_size'] + group2_data['sample_size'] - 2)
        )
        cohens_d = delta_mean / pooled_sd if pooled_sd > 0 else 0
        
        # Hedges' g (偏差校正的Cohen's d)
        correction_factor = 1 - (3 / (4 * (group1_data['sample_size'] + group2_data['sample_size']) - 9))
        hedges_g = cohens_d * correction_factor
        
        # 计算p值 (双尾t检验)
        df = group1_data['sample_size'] + group2_data['sample_size'] - 2
        t_stat = delta_mean / sd_diff if sd_diff > 0 else 0
        p_value = self._calculate_p_value(abs(t_stat), df)
        
        # 判断显著性
        alpha = 1 - confidence_level
        significant = p_value < alpha
        
        return {
            'delta_mean': round(delta_mean, 4),
            'sd_diff': round(sd_diff, 4),
            'ci_lower': round(ci_lower, 4),
            'ci_upper': round(ci_upper, 4),
            'confidence_level': confidence_level,
            'cohens_d': round(cohens_d, 4),
            'hedges_g': round(hedges_g, 4),
            'p_value': round(p_value, 4),
            'significant': significant,
            't_statistic': round(t_stat, 4),
            'degrees_of_freedom': df,
            'interpretation': self._interpret_comparison(delta_mean, ci_lower, ci_upper, significant)
        }
    
    def _get_z_score(self, confidence_level: float) -> float:
        """获取对应置信水平的z分数"""
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576
        }
        return z_scores.get(confidence_level, 1.96)
    
    def _calculate_p_value(self, t_stat: float, df: int) -> float:
        """简化的p值计算（双尾检验）"""
        # 这是一个简化的实现，实际应用中可能需要更精确的统计函数
        if df <= 0:
            return 1.0
        
        # 使用近似公式
        if t_stat == 0:
            return 1.0
        elif t_stat > 4:
            return 0.0001
        elif t_stat > 3:
            return 0.01
        elif t_stat > 2:
            return 0.05
        elif t_stat > 1.5:
            return 0.1
        else:
            return 0.2
    
    def _interpret_comparison(self, delta_mean: float, ci_lower: float, 
                            ci_upper: float, significant: bool) -> str:
        """解释比较结果"""
        if significant:
            if ci_lower > 0:
                return "显著差异：组1显著高于组2"
            elif ci_upper < 0:
                return "显著差异：组1显著低于组2"
            else:
                return "显著差异：但置信区间包含0"
        else:
            return "无显著差异"
    
    def perform_group_comparisons(self, result_data: Dict, comparison_type: str = "all", 
                                confidence_level: float = 0.95) -> Dict:
        """
        执行组间比较分析
        comparison_type: "all", "intervention-baseline", "pairwise"
        """
        results = result_data['results']
        comparisons = []
        
        if comparison_type in ["all", "intervention-baseline"]:
            # 干预组 vs 基线组比较
            baseline_results = results.get('Baseline', results.get('基线组', []))
            intervention_results = results.get('Intervention', results.get('干预组', []))
            
            # 按Case配对比较
            for i, baseline in enumerate(baseline_results):
                if i < len(intervention_results):
                    intervention = intervention_results[i]
                    comparison = self.calculate_group_comparison(
                        intervention, baseline, confidence_level
                    )
                    comparison.update({
                        'comparison_id': f"Intervention_vs_Baseline_{baseline['situation_name']}",
                        'group1_name': 'Intervention',
                        'group2_name': 'Baseline',
                        'case_name': baseline['situation_name'],
                        'group1_data': intervention,
                        'group2_data': baseline
                    })
                    comparisons.append(comparison)
        
        if comparison_type in ["all", "pairwise"]:
            # 同组内Case之间的两两比较
            for group_name, group_results in results.items():
                for i, case1 in enumerate(group_results):
                    for j, case2 in enumerate(group_results[i+1:], i+1):
                        comparison = self.calculate_group_comparison(
                            case1, case2, confidence_level
                        )
                        comparison.update({
                            'comparison_id': f"{group_name}_{case1['situation_name']}_vs_{case2['situation_name']}",
                            'group1_name': f"{group_name}_{case1['situation_name']}",
                            'group2_name': f"{group_name}_{case2['situation_name']}",
                            'case_name': f"{case1['situation_name']}_vs_{case2['situation_name']}",
                            'group1_data': case1,
                            'group2_data': case2
                        })
                        comparisons.append(comparison)
        
        return {
            'comparisons': comparisons,
            'comparison_type': comparison_type,
            'confidence_level': confidence_level,
            'total_comparisons': len(comparisons),
            'significant_comparisons': sum(1 for c in comparisons if c['significant'])
        }
    
    def generate_meta_analysis_formats(self, result_data: Dict, comparison_data: Dict, 
                                     output_dir: str = "results") -> Dict[str, str]:
        """生成多种Meta分析标准格式"""
        self.ensure_results_dir(output_dir)
        saved_files = {}
        
        # 通用Meta分析格式
        universal_data = self._create_universal_meta_format(result_data, comparison_data)
        universal_path = os.path.join(output_dir, "meta_universal.csv")
        universal_path = self.get_available_filename(universal_path)
        
        df_universal = pd.DataFrame(universal_data)
        df_universal.to_csv(universal_path, index=False, encoding='utf-8')
        saved_files['universal'] = universal_path
        
        # RevMan格式
        revman_data = self._create_revman_format(result_data)
        revman_path = os.path.join(output_dir, "meta_revman.csv")
        revman_path = self.get_available_filename(revman_path)
        
        df_revman = pd.DataFrame(revman_data)
        df_revman.to_csv(revman_path, index=False, encoding='utf-8')
        saved_files['revman'] = revman_path
        
        # R Meta包格式
        r_meta_data = self._create_r_meta_format(comparison_data)
        r_path = os.path.join(output_dir, "meta_r.csv")
        r_path = self.get_available_filename(r_path)
        
        df_r = pd.DataFrame(r_meta_data)
        df_r.to_csv(r_path, index=False, encoding='utf-8')
        saved_files['r_meta'] = r_path
        
        return saved_files
    
    def _create_universal_meta_format(self, result_data: Dict, comparison_data: Dict) -> List[Dict]:
        """创建通用Meta分析格式"""
        universal_data = []
        
        for comparison in comparison_data['comparisons']:
            if 'Intervention_vs_Baseline' in comparison['comparison_id']:
                universal_data.append({
                    'Study_ID': comparison['case_name'],
                    'Comparison_Type': 'Intervention-Baseline',
                    'Intervention_Mean': comparison['group1_data']['mean'],
                    'Intervention_SD': comparison['group1_data']['sd'],
                    'Intervention_N': comparison['group1_data']['sample_size'],
                    'Control_Mean': comparison['group2_data']['mean'],
                    'Control_SD': comparison['group2_data']['sd'],
                    'Control_N': comparison['group2_data']['sample_size'],
                    'Mean_Difference': comparison['delta_mean'],
                    'SD_Difference': comparison['sd_diff'],
                    'Effect_Size_Cohens_d': comparison['cohens_d'],
                    'Effect_Size_Hedges_g': comparison['hedges_g'],
                    'SE_Mean_Diff': comparison['sd_diff'],
                    '95_CI_Lower': comparison['ci_lower'],
                    '95_CI_Upper': comparison['ci_upper'],
                    'P_Value': comparison['p_value'],
                    'Significant': 'Yes' if comparison['significant'] else 'No',
                    'Data_Quality_Level': comparison['group1_data']['used_level'],
                    'Conservative_Estimate': 'Yes' if comparison['group1_data'].get('conservative_estimate') else 'No',
                    'Original_Method': comparison['group1_data']['method_used'],
                    'Notes': comparison['interpretation']
                })
        
        return universal_data
    
    def _create_revman_format(self, result_data: Dict) -> List[Dict]:
        """创建RevMan格式"""
        revman_data = []
        results = result_data['results']
        
        baseline_results = results.get('Baseline', results.get('基线组', []))
        intervention_results = results.get('Intervention', results.get('干预组', []))
        
        for i, baseline in enumerate(baseline_results):
            if i < len(intervention_results):
                intervention = intervention_results[i]
                revman_data.append({
                    'Study_ID': baseline['situation_name'],
                    'Intervention_Mean': intervention['mean'],
                    'Intervention_SD': intervention['sd'],
                    'Intervention_N': intervention['sample_size'],
                    'Control_Mean': baseline['mean'],
                    'Control_SD': baseline['sd'],
                    'Control_N': baseline['sample_size']
                })
        
        return revman_data
    
    def _create_r_meta_format(self, comparison_data: Dict) -> List[Dict]:
        """创建R Meta包格式"""
        r_data = []
        
        for comparison in comparison_data['comparisons']:
            if 'Intervention_vs_Baseline' in comparison['comparison_id']:
                r_data.append({
                    'Study': comparison['case_name'],
                    'TE': comparison['delta_mean'],
                    'seTE': comparison['sd_diff'],
                    'n.e': comparison['group1_data']['sample_size'],
                    'n.c': comparison['group2_data']['sample_size'],
                    'mean.e': comparison['group1_data']['mean'],
                    'sd.e': comparison['group1_data']['sd'],
                    'mean.c': comparison['group2_data']['mean'],
                    'sd.c': comparison['group2_data']['sd']
                })
        
        return r_data
    
    def is_file_locked(self, filepath: str) -> bool:
        """检测文件是否被占用"""
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, 'a'):
                return False
        except (IOError, OSError):
            return True
    
    def get_available_filename(self, base_filename: str) -> str:
        """获取可用的文件名，处理文件占用情况"""
        # 分离文件名和扩展名
        name, ext = os.path.splitext(base_filename)
        
        # 首先尝试原始文件名
        if not self.is_file_locked(base_filename):
            return base_filename
        
        # 尝试 _01 到 _99
        for i in range(1, 100):
            suffix = f"_{i:02d}"
            new_filename = f"{name}{suffix}{ext}"
            if not self.is_file_locked(new_filename):
                return new_filename
        
        # 超过99，从_01开始覆盖
        return f"{name}_01{ext}"
    
    def ensure_results_dir(self, output_dir: str = "results") -> str:
        """确保结果目录存在"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir
    
    def save_to_excel(self, result_data: Dict, comparison_data: Dict = None, 
                     output_dir: str = "results", base_filename: str = "iqr_results.xlsx") -> str:
        """保存结果到Excel文件"""
        self.ensure_results_dir(output_dir)
        filepath = os.path.join(output_dir, base_filename)
        final_filepath = self.get_available_filename(filepath)
        
        # 创建Excel写入器
        with pd.ExcelWriter(final_filepath, engine='openpyxl') as writer:
            # Sheet1: 转换结果
            results_data = []
            for group_name, group_results in result_data['results'].items():
                for result in group_results:
                    results_data.append({
                        'Group': group_name,
                        'Case': result['situation_name'],
                        'Mean': round(result['mean'], 4),
                        'SD': round(result['sd'], 4),
                        'Sample_Size': result['sample_size'],
                        'Data_Level': result['used_level'],
                        'Method': result['method_used'],
                        'Conservative_Estimate': 'Yes' if result.get('conservative_estimate') else 'No',
                        'Precision': result.get('precision_estimate', ''),
                        'Formula_Source': result.get('formula_source', '')
                    })
            
            if results_data:
                df_results = pd.DataFrame(results_data)
                df_results.to_excel(writer, sheet_name='转换结果', index=False)
            
            # Sheet2: 组间比较结果 (如果有比较数据)
            if comparison_data and comparison_data['comparisons']:
                comparison_results = []
                for comp in comparison_data['comparisons']:
                    comparison_results.append({
                        'Comparison': f"{comp['group1_name']} vs {comp['group2_name']}",
                        'Case': comp['case_name'],
                        'ΔMean': comp['delta_mean'],
                        'SD_diff': comp['sd_diff'],
                        '95%_CI_Lower': comp['ci_lower'],
                        '95%_CI_Upper': comp['ci_upper'],
                        'Cohens_d': comp['cohens_d'],
                        'Hedges_g': comp['hedges_g'],
                        'P_Value': comp['p_value'],
                        'Significant': 'Yes' if comp['significant'] else 'No',
                        'Interpretation': comp['interpretation']
                    })
                
                df_comparisons = pd.DataFrame(comparison_results)
                df_comparisons.to_excel(writer, sheet_name='组间比较结果', index=False)
            
            # Sheet3: 数据质量分析
            quality_data = []
            for group_name, group_analysis in result_data['analysis'].items():
                quality_data.append({
                    'Group': group_name,
                    'Total_Cases': group_analysis['situation_count'],
                    'Min_Level': group_analysis['min_level'],
                    'Conservative_Strategy': 'Yes' if group_analysis['conservative_strategy'] else 'No',
                    'Precision': self._get_precision_description(group_analysis['min_level'])
                })
            
            if quality_data:
                df_quality = pd.DataFrame(quality_data)
                df_quality.to_excel(writer, sheet_name='数据质量分析', index=False)
            
            # Sheet4: 详细分析
            detail_data = []
            for group_name, group_analysis in result_data['analysis'].items():
                for situation in group_analysis['situations']:
                    detail_data.append({
                        'Group': group_name,
                        'Case': situation['situation_name'],
                        'Available_Data': ', '.join(situation['available_data']),
                        'Original_Level': situation['data_level'],
                        'Used_Level': group_analysis['min_level'],
                        'Conservative_Applied': 'Yes' if situation['data_level'] > group_analysis['min_level'] else 'No'
                    })
            
            if detail_data:
                df_detail = pd.DataFrame(detail_data)
                df_detail.to_excel(writer, sheet_name='详细分析', index=False)
            
            # Sheet5: 摘要信息
            summary = result_data['summary']
            summary_data = [
                {'项目': '总组数', '值': summary['total_groups']},
                {'项目': '总情况数', '值': summary['total_situations']},
                {'项目': '保守估计组数', '值': summary['conservative_groups']},
                {'项目': '整体最低等级', '值': summary['overall_min_level']},
                {'项目': '精度估计', '值': summary['precision_estimate']},
                {'项目': '处理时间', '值': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            ]
            
            # 如果有比较数据，添加比较摘要
            if comparison_data:
                summary_data.extend([
                    {'项目': '总比较数', '值': comparison_data['total_comparisons']},
                    {'项目': '显著比较数', '值': comparison_data['significant_comparisons']},
                    {'项目': '比较类型', '值': comparison_data['comparison_type']},
                    {'项目': '置信水平', '值': f"{comparison_data['confidence_level']*100}%"}
                ])
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='摘要信息', index=False)
            
            # 如果有建议，添加到摘要
            if summary['recommendations']:
                rec_data = [{'建议': rec} for rec in summary['recommendations']]
                df_rec = pd.DataFrame(rec_data)
                df_rec.to_excel(writer, sheet_name='改进建议', index=False)
        
        return final_filepath
    
    def save_to_csv(self, result_data: Dict, output_dir: str = "results", 
                   base_filename: str = "iqr_results_summary.csv") -> str:
        """保存摘要结果到CSV文件"""
        self.ensure_results_dir(output_dir)
        filepath = os.path.join(output_dir, base_filename)
        final_filepath = self.get_available_filename(filepath)
        
        # 准备CSV数据
        csv_data = []
        for group_name, group_results in result_data['results'].items():
            for result in group_results:
                csv_data.append({
                    'Group': group_name,
                    'Case': result['situation_name'],
                    'Mean': round(result['mean'], 4),
                    'SD': round(result['sd'], 4),
                    'Sample_Size': result['sample_size'],
                    'Data_Level': result['used_level'],
                    'Method': result['method_used'],
                    'Conservative_Estimate': 'Yes' if result.get('conservative_estimate') else 'No'
                })
        
        # 写入CSV
        if csv_data:
            df = pd.DataFrame(csv_data)
            df.to_csv(final_filepath, index=False, encoding='utf-8')
        
        return final_filepath
    
    def save_results(self, result_data: Dict, output_dir: str = "results", 
                    base_name: str = "iqr_results", save_csv: bool = True) -> Dict[str, str]:
        """保存所有结果文件"""
        saved_files = {}
        
        # 保存Excel文件
        excel_filename = f"{base_name}.xlsx"
        excel_path = self.save_to_excel(result_data, output_dir, excel_filename)
        saved_files['excel'] = excel_path
        
        # 保存CSV摘要文件
        if save_csv:
            csv_filename = f"{base_name}_summary.csv"
            csv_path = self.save_to_csv(result_data, output_dir, csv_filename)
            saved_files['csv'] = csv_path
        
        return saved_files

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
  python csv_converter.py --convert data.csv --output-dir my_results
  python csv_converter.py --convert data.csv --output-name analysis_2025 --no-csv
        """
    )
    
    parser.add_argument('--generate-template', action='store_true', help='生成CSV模板')
    parser.add_argument('--situations', type=int, default=4, help='模板中的情况数量 (默认: 4)')
    parser.add_argument('--convert', help='转换CSV文件')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    parser.add_argument('--output-dir', default='results', help='输出目录 (默认: results)')
    parser.add_argument('--output-name', default='iqr_results', help='输出文件基础名称 (默认: iqr_results)')
    parser.add_argument('--no-csv', action='store_true', help='不生成CSV摘要文件')
    
    # 组间比较功能
    parser.add_argument('--compare-groups', action='store_true', help='启用组间比较功能')
    parser.add_argument('--comparison-type', choices=['all', 'intervention-baseline', 'pairwise'], 
                       default='intervention-baseline', help='比较类型 (默认: intervention-baseline)')
    parser.add_argument('--confidence-level', type=float, default=0.95, 
                       help='置信水平 (默认: 0.95)')
    parser.add_argument('--meta-analysis-format', action='store_true', 
                       help='生成Meta分析标准格式文件')
    
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
            print(f"处理文件: {args.convert}")
            
            result = converter.convert_csv_data(args.convert, args.verbose)
            
            # 执行组间比较（如果启用）
            comparison_data = None
            if args.compare_groups:
                print(f"\n正在执行组间比较分析...")
                comparison_data = converter.perform_group_comparisons(
                    result, 
                    args.comparison_type, 
                    args.confidence_level
                )
                
                if not args.json:
                    print_comparison_results(comparison_data, args.verbose)
            
            if args.json:
                output_data = result.copy()
                if comparison_data:
                    output_data['comparisons'] = comparison_data
                print(json.dumps(output_data, indent=2, ensure_ascii=False))
            else:
                print_results(result, args.verbose)
            
            # 强制保存结果
            print(f"\n正在保存结果...")
            try:
                # 保存基础结果（包含比较数据）
                excel_filename = f"{args.output_name}.xlsx"
                excel_path = converter.save_to_excel(
                    result, 
                    comparison_data, 
                    args.output_dir, 
                    excel_filename
                )
                
                saved_files = {'excel': excel_path}
                
                # 保存CSV摘要文件
                if not args.no_csv:
                    csv_filename = f"{args.output_name}_summary.csv"
                    csv_path = converter.save_to_csv(result, args.output_dir, csv_filename)
                    saved_files['csv'] = csv_path
                
                # 生成Meta分析格式文件（如果启用）
                if args.meta_analysis_format and comparison_data:
                    meta_files = converter.generate_meta_analysis_formats(
                        result, comparison_data, args.output_dir
                    )
                    saved_files.update(meta_files)
                
                print(f"\n✓ 结果已保存:")
                print(f"  📊 详细结果: {saved_files['excel']}")
                if 'csv' in saved_files:
                    print(f"  📋 摘要结果: {saved_files['csv']}")
                
                if args.meta_analysis_format and comparison_data:
                    print(f"  📈 Meta分析格式:")
                    for format_name, file_path in meta_files.items():
                        print(f"    - {format_name}: {file_path}")
                
                print(f"\n文件说明:")
                print(f"- Excel文件包含完整分析和多个工作表")
                if comparison_data:
                    print(f"- 包含组间比较结果和置信区间分析")
                if 'csv' in saved_files:
                    print(f"- CSV文件为简化摘要，便于导入其他软件")
                if args.meta_analysis_format and comparison_data:
                    print(f"- Meta分析格式文件可直接导入RevMan、R等软件")
                
            except Exception as save_error:
                print(f"⚠️  保存文件时出现问题: {save_error}")
                print(f"结果已在屏幕上显示，请手动保存")
        
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

def print_comparison_results(comparison_data: Dict, verbose: bool = False):
    """打印组间比较结果"""
    print("\n" + "=" * 60)
    print("组间比较分析")
    print("=" * 60)
    
    print(f"\n比较类型: {comparison_data['comparison_type']}")
    print(f"置信水平: {comparison_data['confidence_level']*100}%")
    print(f"总比较数: {comparison_data['total_comparisons']}")
    print(f"显著比较数: {comparison_data['significant_comparisons']}")
    
    if comparison_data['comparisons']:
        print(f"\n详细比较结果:")
        print("-" * 80)
        
        for comp in comparison_data['comparisons']:
            print(f"\n📊 {comp['group1_name']} vs {comp['group2_name']} ({comp['case_name']})")
            print(f"   ΔMean = {comp['delta_mean']:.4f}")
            print(f"   SD_diff = {comp['sd_diff']:.4f}")
            print(f"   95% CI: [{comp['ci_lower']:.4f}, {comp['ci_upper']:.4f}]")
            print(f"   Cohen's d = {comp['cohens_d']:.4f}")
            print(f"   P值 = {comp['p_value']:.4f}")
            
            # 显著性标记
            if comp['significant']:
                print(f"   ✓ {comp['interpretation']}")
            else:
                print(f"   ○ {comp['interpretation']}")
            
            if verbose:
                print(f"   详细信息:")
                print(f"     - Hedges' g = {comp['hedges_g']:.4f}")
                print(f"     - t统计量 = {comp['t_statistic']:.4f}")
                print(f"     - 自由度 = {comp['degrees_of_freedom']}")
                print(f"     - 组1数据: Mean={comp['group1_data']['mean']:.3f}, SD={comp['group1_data']['sd']:.3f}, N={comp['group1_data']['sample_size']}")
                print(f"     - 组2数据: Mean={comp['group2_data']['mean']:.3f}, SD={comp['group2_data']['sd']:.3f}, N={comp['group2_data']['sample_size']}")
    
    print("\n" + "=" * 60)
    print("比较结果摘要")
    print("=" * 60)
    
    # 按显著性分组显示
    significant_comps = [c for c in comparison_data['comparisons'] if c['significant']]
    non_significant_comps = [c for c in comparison_data['comparisons'] if not c['significant']]
    
    if significant_comps:
        print(f"\n✓ 显著差异 ({len(significant_comps)}个):")
        for comp in significant_comps:
            direction = "↑" if comp['delta_mean'] > 0 else "↓"
            print(f"  {direction} {comp['case_name']}: ΔMean={comp['delta_mean']:.3f} (p={comp['p_value']:.3f})")
    
    if non_significant_comps:
        print(f"\n○ 无显著差异 ({len(non_significant_comps)}个):")
        for comp in non_significant_comps:
            print(f"    {comp['case_name']}: ΔMean={comp['delta_mean']:.3f} (p={comp['p_value']:.3f})")

if __name__ == "__main__":
    main()
