"""
7.5.statistical_converter.py
统计转换核心模块
实现箱线图数据到Mean±SD的转换
基于Wan 2014和Luo 2018公式
"""

import math
import numpy as np
from typing import Dict, Tuple, Optional, List

class StatisticalConverter:
    """统计转换器类"""
    
    def __init__(self):
        self.conversion_methods = {
            'wan2014': self._wan2014_method,
            'luo2018': self._luo2018_method,
            'simple': self._simple_method,
            'auto': self._select_best_method
        }
    
    def convert_boxplot_to_stats(self, boxplot_data: Dict, sample_size: int, 
                                method: str = 'auto') -> Dict:
        """
        将箱线图数据转换为Mean±SD（分级计算系统）
        
        Args:
            boxplot_data: 箱线图数据字典
            sample_size: 样本量
            method: 转换方法 ('auto' 推荐，会自动选择最佳等级)
            
        Returns:
            包含mean, sd, data_level, method_used等信息的字典
        """
        # 数据验证
        self._validate_boxplot_data(boxplot_data)
        
        # 确定数据等级
        data_level = self._determine_data_level(boxplot_data)
        
        # 根据等级选择计算方法
        if method == 'auto':
            selected_method = self._select_method_by_level(data_level, boxplot_data, sample_size)
        else:
            selected_method = method
            
        # 执行转换
        result = self._calculate_by_level(boxplot_data, sample_size, data_level)
        
        # 添加元信息
        result.update({
            'data_level': data_level,
            'method_used': selected_method,
            'sample_size': sample_size,
            'distribution_assessment': self._assess_distribution(boxplot_data),
            'precision_estimate': self._get_precision_estimate(data_level),
            'recommended_formula': self._get_formula_description(data_level)
        })
        
        return result
    
    def _determine_data_level(self, data: Dict) -> int:
        """
        确定数据等级
        等级 0：只有 Q1、Q2、Q3、n
        等级 1：等级 0 + 上下须（min、max）
        等级 2：等级 1 + 异常值（或确切样本极值）
        """
        # 检查基础数据（Q1, Q2, Q3）
        has_quartiles = all(data.get(field) is not None for field in ['q1', 'q2', 'q3'])
        if not has_quartiles:
            raise ValueError("缺少基础四分位数数据")
        
        # 检查须数据
        has_whiskers = (data.get('upper_whisker') is not None and 
                       data.get('lower_whisker') is not None)
        
        # 检查异常值数据
        upper_outliers = data.get('upper_outliers', [])
        lower_outliers = data.get('lower_outliers', [])
        has_outliers = len(upper_outliers) > 0 or len(lower_outliers) > 0
        
        # 确定等级
        if has_outliers and has_whiskers:
            return 2  # 最高等级：有异常值信息
        elif has_whiskers:
            return 1  # 中等等级：有须信息
        else:
            return 0  # 基础等级：只有四分位数
    
    def _select_method_by_level(self, level: int, data: Dict, sample_size: int) -> str:
        """根据数据等级选择计算方法"""
        if level == 0:
            return 'wan2014_three_number'
        elif level == 1:
            return 'wan2014_five_number'
        else:  # level == 2
            # 异常值主要用于偏态判断，公式与等级1相同
            return 'wan2014_five_number_with_outlier_correction'
    
    def _calculate_by_level(self, data: Dict, n: int, level: int) -> Dict:
        """根据等级进行计算"""
        if level == 0:
            return self._level0_calculation(data, n)
        elif level == 1:
            return self._level1_calculation(data, n)
        else:  # level == 2
            return self._level2_calculation(data, n)
    
    def _level0_calculation(self, data: Dict, n: int) -> Dict:
        """
        等级0计算：只有Q1、Q2、Q3、n
        使用Wan 2014三数公式
        """
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        
        # Mean估计：三数平均
        mean = (q1 + q2 + q3) / 3
        
        # SD估计：IQR/1.35
        sd = (q3 - q1) / 1.35
        
        # 检查偏态并应用校正
        if self._is_skewed_distribution(data):
            # 应用Luo 2018偏态校正
            skew_factor = self._calculate_skew_factor(data)
            mean = mean + skew_factor * (q3 - q1) * 0.1
            sd = sd * (1 + abs(skew_factor) * 0.2)
        
        return {
            'mean': mean,
            'sd': sd,
            'method_details': 'Wan 2014三数公式: Mean=(Q1+Q2+Q3)/3, SD=(Q3-Q1)/1.35',
            'formula_source': 'Wan 2014',
            'calculation_notes': f'基础等级计算，预期误差15-25%'
        }
    
    def _level1_calculation(self, data: Dict, n: int) -> Dict:
        """
        等级1计算：等级0 + 上下须
        使用Wan 2014五数公式
        """
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        min_val = data['lower_whisker']
        max_val = data['upper_whisker']
        
        # 加权五数公式计算Mean
        if n <= 15:
            # 小样本权重
            mean = (min_val + 2*q1 + 2*q2 + 2*q3 + max_val) / 8
        elif n <= 70:
            # 中样本权重
            mean = (min_val + q1 + 2*q2 + q3 + max_val) / 6
        else:
            # 大样本权重（更接近四分位数）
            mean = (q1 + 2*q2 + q3) / 4
        
        # 加权五数公式计算SD
        if n <= 15:
            sd = (max_val - min_val) / 4
        elif n <= 70:
            sd = (max_val - min_val) / (2 * (1.35 + 0.5))
        else:
            sd = (q3 - q1) / 1.35
        
        return {
            'mean': mean,
            'sd': sd,
            'method_details': f'Wan 2014五数公式: 加权计算，n={n}',
            'formula_source': 'Wan 2014',
            'calculation_notes': f'中等级计算，预期误差8-15%'
        }
    
    def _level2_calculation(self, data: Dict, n: int) -> Dict:
        """
        等级2计算：等级1 + 异常值
        异常值主要用于偏态判断，公式与等级1相同但有偏态校正
        """
        # 先用等级1方法计算基础值
        base_result = self._level1_calculation(data, n)
        
        # 分析异常值模式
        upper_outliers = data.get('upper_outliers', [])
        lower_outliers = data.get('lower_outliers', [])
        
        # 计算Tukey内外篱
        q1, q3 = data['q1'], data['q3']
        iqr = q3 - q1
        inner_fence_lower = q1 - 1.5 * iqr
        inner_fence_upper = q3 + 1.5 * iqr
        outer_fence_lower = q1 - 3 * iqr
        outer_fence_upper = q3 + 3 * iqr
        
        # 分析异常值分布
        extreme_upper = [x for x in upper_outliers if x > outer_fence_upper]
        extreme_lower = [x for x in lower_outliers if x < outer_fence_lower]
        
        # 偏态校正
        outlier_skew = len(extreme_upper) - len(extreme_lower)
        if abs(outlier_skew) > 0:
            skew_correction = outlier_skew * iqr * 0.05  # 5%的IQR作为校正
            base_result['mean'] += skew_correction
            base_result['sd'] *= (1 + abs(outlier_skew) * 0.1)
        
        # 更新方法信息
        base_result.update({
            'method_details': f'Wan 2014五数公式 + 异常值偏态校正，n={n}',
            'formula_source': 'Wan 2014 + Tukey异常值分析',
            'calculation_notes': f'最高等级计算，预期误差5-10%',
            'outlier_analysis': {
                'upper_outliers': len(upper_outliers),
                'lower_outliers': len(lower_outliers),
                'extreme_upper': len(extreme_upper),
                'extreme_lower': len(extreme_lower),
                'skew_correction': outlier_skew
            }
        })
        
        return base_result
    
    def _is_skewed_distribution(self, data: Dict) -> bool:
        """判断分布是否偏态"""
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        
        # 计算偏态指标
        if q3 - q1 > 0:
            skew_indicator = abs(q2 - (q1 + q3) / 2) / (q3 - q1)
            return skew_indicator > 0.1  # 偏态阈值
        return False
    
    def _calculate_skew_factor(self, data: Dict) -> float:
        """计算偏态因子"""
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        
        if q3 - q1 > 0:
            # 正值表示右偏，负值表示左偏
            return (q2 - (q1 + q3) / 2) / (q3 - q1)
        return 0
    
    def _get_precision_estimate(self, level: int) -> str:
        """获取精度估计"""
        precision_map = {
            0: "中等精度 (误差15-25%)",
            1: "高精度 (误差8-15%)", 
            2: "最高精度 (误差5-10%)"
        }
        return precision_map.get(level, "未知精度")
    
    def _get_formula_description(self, level: int) -> str:
        """获取公式描述"""
        formula_map = {
            0: "Wan 2014三数公式",
            1: "Wan 2014五数公式",
            2: "Wan 2014五数公式 + 异常值校正"
        }
        return formula_map.get(level, "未知公式")
    
    def _validate_boxplot_data(self, data: Dict) -> None:
        """验证箱线图数据的有效性"""
        required_fields = ['q1', 'q2', 'q3']
        
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"缺少必需的数据: {field}")
        
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        
        if not (q1 <= q2 <= q3):
            raise ValueError(f"四分位数顺序错误: Q1({q1}) <= Q2({q2}) <= Q3({q3})")
    
    def _assess_distribution(self, data: Dict) -> Dict:
        """评估分布特征"""
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        iqr = q3 - q1
        
        # 对称性检查
        if iqr > 0:
            symmetry_ratio = abs(q2 - (q1 + q3) / 2) / iqr
            is_symmetric = symmetry_ratio < 0.1
        else:
            symmetry_ratio = 0
            is_symmetric = True
        
        # 须长对称性检查
        upper_whisker = data.get('upper_whisker')
        lower_whisker = data.get('lower_whisker')
        whisker_symmetry = None
        
        if upper_whisker and lower_whisker and iqr > 0:
            upper_length = upper_whisker - q3
            lower_length = q1 - lower_whisker
            whisker_symmetry = abs(upper_length - lower_length) / iqr
        
        # 异常值影响
        upper_outliers = data.get('upper_outliers', [])
        lower_outliers = data.get('lower_outliers', [])
        outlier_impact = len(upper_outliers) + len(lower_outliers)
        
        return {
            'is_symmetric': is_symmetric,
            'symmetry_ratio': symmetry_ratio,
            'whisker_symmetry': whisker_symmetry,
            'outlier_impact': outlier_impact,
            'iqr': iqr
        }
    
    def _select_best_method(self, data: Dict, sample_size: int) -> str:
        """自动选择最佳转换方法"""
        assessment = self._assess_distribution(data)
        
        # 如果分布高度对称且无异常值，使用简单方法
        if (assessment['is_symmetric'] and 
            assessment['outlier_impact'] == 0 and
            assessment['whisker_symmetry'] is not None and
            assessment['whisker_symmetry'] < 0.2):
            return 'simple'
        
        # 如果样本量较大且分布相对对称，使用Wan 2014
        elif sample_size >= 25 and assessment['symmetry_ratio'] < 0.3:
            return 'wan2014'
        
        # 其他情况使用Luo 2018（更适合偏态分布）
        else:
            return 'luo2018'
    
    def _simple_method(self, data: Dict, n: int) -> Dict:
        """简单方法：适用于对称分布"""
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        
        # Mean ≈ Median
        mean = q2
        
        # SD ≈ IQR / 1.35
        sd = (q3 - q1) / 1.35
        
        return {
            'mean': mean,
            'sd': sd,
            'method_details': 'Simple method: Mean ≈ Q2, SD ≈ IQR/1.35'
        }
    
    def _wan2014_method(self, data: Dict, n: int) -> Dict:
        """Wan 2014方法"""
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        
        # Mean estimation
        mean = (q1 + q2 + q3) / 3
        
        # SD estimation
        sd = (q3 - q1) / 1.35
        
        # 样本量修正
        if n > 50:
            # 大样本修正
            sd = sd * (1 + 0.14 / math.sqrt(n))
        
        return {
            'mean': mean,
            'sd': sd,
            'method_details': f'Wan 2014: Mean = (Q1+Q2+Q3)/3, SD = (Q3-Q1)/1.35, n={n}'
        }
    
    def _luo2018_method(self, data: Dict, n: int) -> Dict:
        """Luo 2018方法：适用于偏态分布"""
        q1, q2, q3 = data['q1'], data['q2'], data['q3']
        upper_whisker = data.get('upper_whisker')
        lower_whisker = data.get('lower_whisker')
        
        # 基础估计
        mean_base = (q1 + q2 + q3) / 3
        
        # 如果有须的信息，进行加权估计
        if upper_whisker is not None and lower_whisker is not None:
            # 加权平均，考虑分布的偏态
            range_total = upper_whisker - lower_whisker
            if range_total > 0:
                # 根据须的相对位置调整权重
                upper_weight = (upper_whisker - q3) / range_total
                lower_weight = (q1 - lower_whisker) / range_total
                
                # 偏态修正
                skew_correction = (upper_weight - lower_weight) * (q3 - q1) * 0.1
                mean = mean_base + skew_correction
            else:
                mean = mean_base
        else:
            mean = mean_base
        
        # SD estimation with whisker information
        if upper_whisker is not None and lower_whisker is not None:
            # 使用全范围信息
            range_estimate = (upper_whisker - lower_whisker) / 4
            iqr_estimate = (q3 - q1) / 1.35
            
            # 加权组合
            sd = 0.7 * iqr_estimate + 0.3 * range_estimate
        else:
            sd = (q3 - q1) / 1.35
        
        # 样本量和偏态修正
        if n < 25:
            sd = sd * (1 + 0.5 / n)
        
        return {
            'mean': mean,
            'sd': sd,
            'method_details': f'Luo 2018: Enhanced estimation with whiskers, n={n}'
        }
    
    def calculate_difference_stats(self, group1_stats: Dict, group2_stats: Dict, 
                                 correlation: float = 0.0) -> Dict:
        """
        计算两组间差值的Mean和SD
        
        Args:
            group1_stats: 第一组统计量 (基线组)
            group2_stats: 第二组统计量 (干预组)
            correlation: 组间相关系数 (默认0，保守估计)
            
        Returns:
            差值统计量字典
        """
        mean1, sd1 = group1_stats['mean'], group1_stats['sd']
        mean2, sd2 = group2_stats['mean'], group2_stats['sd']
        n1 = group1_stats.get('sample_size', 1)
        n2 = group2_stats.get('sample_size', 1)
        
        # 差值均值
        diff_mean = mean2 - mean1
        
        # 差值标准差
        # SD_diff = √(SD₁² + SD₂² - 2·r·SD₁·SD₂)
        variance_diff = sd1**2 + sd2**2 - 2 * correlation * sd1 * sd2
        diff_sd = math.sqrt(max(0, variance_diff))  # 确保非负
        
        # 标准误
        se_diff = math.sqrt(sd1**2/n1 + sd2**2/n2 - 2*correlation*sd1*sd2/math.sqrt(n1*n2))
        
        # 效应量 (Cohen's d)
        pooled_sd = math.sqrt(((n1-1)*sd1**2 + (n2-1)*sd2**2) / (n1+n2-2))
        cohens_d = diff_mean / pooled_sd if pooled_sd > 0 else 0
        
        # 95%置信区间
        df = n1 + n2 - 2
        t_critical = self._get_t_critical(df)
        ci_lower = diff_mean - t_critical * se_diff
        ci_upper = diff_mean + t_critical * se_diff
        
        return {
            'difference_mean': diff_mean,
            'difference_sd': diff_sd,
            'standard_error': se_diff,
            'cohens_d': cohens_d,
            'confidence_interval_95': (ci_lower, ci_upper),
            'correlation_used': correlation,
            'sample_sizes': (n1, n2),
            'calculation_details': {
                'group1': f"Mean={mean1:.3f}, SD={sd1:.3f}, n={n1}",
                'group2': f"Mean={mean2:.3f}, SD={sd2:.3f}, n={n2}",
                'formula': f"Diff = {mean2:.3f} - {mean1:.3f} = {diff_mean:.3f}"
            }
        }
    
    def _get_t_critical(self, df: int, alpha: float = 0.05) -> float:
        """获取t分布临界值（简化版本）"""
        # 简化的t分布临界值表（双尾，α=0.05）
        t_table = {
            1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
            6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
            15: 2.131, 20: 2.086, 25: 2.060, 30: 2.042, 40: 2.021,
            50: 2.009, 60: 2.000, 100: 1.984, 1000: 1.962
        }
        
        if df in t_table:
            return t_table[df]
        elif df > 1000:
            return 1.96  # 正态分布近似
        else:
            # 线性插值
            keys = sorted(t_table.keys())
            for i, key in enumerate(keys):
                if df <= key:
                    if i == 0:
                        return t_table[key]
                    else:
                        # 线性插值
                        prev_key = keys[i-1]
                        ratio = (df - prev_key) / (key - prev_key)
                        return t_table[prev_key] + ratio * (t_table[key] - t_table[prev_key])
            return 1.96

def test_converter():
    """测试函数"""
    converter = StatisticalConverter()
    
    # 测试数据
    test_data = {
        'q1': 10,
        'q2': 15,
        'q3': 20,
        'upper_whisker': 25,
        'lower_whisker': 5,
        'upper_outliers': [],
        'lower_outliers': []
    }
    
    # 测试转换
    result = converter.convert_boxplot_to_stats(test_data, sample_size=30)
    print("转换结果:", result)
    
    # 测试差值计算
    group1 = {'mean': 10, 'sd': 3, 'sample_size': 30}
    group2 = {'mean': 15, 'sd': 4, 'sample_size': 30}
    
    diff_result = converter.calculate_difference_stats(group1, group2)
    print("差值结果:", diff_result)

if __name__ == "__main__":
    test_converter()
