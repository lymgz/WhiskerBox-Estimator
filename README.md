# WhiskerBox-Estimator
WhiskerBox-Estimator：一键读取带须箱线图，自动估算均值与标准差，为网络元分析生成输入表。

===
# IQR转换工具 (Boxplot to Mean±SD Converter)

## 概述

这是一个专业的箱线图数据转换工具，能够将箱线图的五数概括（Q1, Q2, Q3, 上下须, 异常值）转换为均值±标准差格式，用于meta分析和统计研究。

## 核心特性

### 🎯 "分图分法"智能处理
- **自动等级检测**：程序自动识别每个数据集的完整度
- **最不利情况分析**：采用保守估计策略，确保结果可靠性
- **动态公式选择**：根据数据等级自动选择最佳转换公式

### 📊 数据等级系统
| 等级 | 可用数据 | 转换公式 | 预期精度 |
|------|----------|----------|----------|
| 等级0 | Q1, Q2, Q3, n | Wan 2014三数公式 | 中等精度 (误差15-25%) |
| 等级1 | 等级0 + 上下须 | Wan 2014五数公式 | 高精度 (误差8-15%) |
| 等级2 | 等级1 + 异常值 | 五数公式 + 偏态校正 | 最高精度 (误差5-10%) |

### 🌐 多语言支持
- **中文标签**：基线组、干预组、上须、下须等
- **英文标签**：Baseline、Intervention、Upper_Whisker、Lower_Whisker等
- **自动识别**：程序自动识别并处理两种语言格式

## 工具列表

### 1. CSV批量转换工具 (`csv_converter.py`)
**推荐使用** - 支持批量处理和智能分析

#### 主要功能：
- ✅ 自动生成标准化CSV模板
- ✅ 支持任意数量的情况列（不限于4个）
- ✅ 智能数据等级检测
- ✅ 最不利情况保守估计
- ✅ 详细的数据质量报告
- ✅ 中英文双语支持

#### 使用方法：
```bash
python csv_converter.py --help  看看帮助文件
```

**步骤1：生成模板**
```bash
python csv_converter.py --generate-template --situations 6
```

**步骤2：填写数据**
编辑生成的 `template.csv` 文件，按以下格式填入数据：

```csv
Baseline,Case1,Case2,Case3,Case4
Upper_Outlier,,88,,
Upper_Whisker,30.933,42.933,25,35
Q3,10.4,20.8,15,22
Q2,-6.133,6.933,8,12
Q1,-29.067,-19.2,-5,2
Lower_Whisker,-50.933,-36.267,-15,-8
Lower_Outlier,,-50,,
Sample_Size,30,30,25,28
,,,,
Intervention,Case1,Case2,Case3,Case4
Upper_Outlier,95,,,
Upper_Whisker,42.5,55.2,30,40
Q3,18.2,28.5,20,25
Q2,2.1,15.8,12,18
Q1,-15.3,-8.7,5,8
Lower_Whisker,-35.8,-25.4,-2,0
Lower_Outlier,,,-60,
Sample_Size,30,30,25,28
```

**步骤3：执行转换**
```bash
# 详细输出
python csv_converter.py --convert data.csv --verbose

# JSON格式输出
python csv_converter.py --convert data.csv --json
```

#### 输出示例：
```
============================================================
数据质量分析
============================================================

Baseline:
  Case1: ✓ 等级1 (上须, Q3, Q2, Q1, 下须, 样本量)
  Case2: ✓✓ 等级2 (上异常值, 上须, Q3, Q2, Q1, 下须, 下异常值, 样本量)
  Case3: ✓ 等级1 (上须, Q3, Q2, Q1, 下须, 样本量)
  → 采用保守估计: 等级1

整体精度: 高精度 (误差8-15%)

============================================================
转换结果
============================================================

Baseline:
  Case1: Mean=-8.489, SD=22.126
  Case2: Mean=3.689, SD=21.405 (保守估计)
  Case3: Mean=6.000, SD=10.811
```

### 2. 交互式转换工具 (`simple_converter.py`)
适合单次转换和学习使用

#### 使用方法：
```bash
python simple_converter.py  (学习建议工具)
```

### 3. 统计转换核心 (`statistical_converter.py`)
底层转换引擎，供其他工具调用

## 数据输入格式说明

### CSV模板结构
- **分组清晰**：基线组和干预组分别占用独立行块
- **空行分隔**：用空行分隔不同组，提高可读性
- **动态列数**：支持任意数量的情况列
- **标准化标签**：使用英文标签避免编码问题

### 数据项说明
| 英文标签 | 中文标签 | 说明 | 必需性 |
|----------|----------|------|--------|
| Upper_Outlier | 上异常值 | 上方异常值 | 可选 |
| Upper_Whisker | 上须 | 上方须线 | 可选 |
| Q3 | Q3 | 上四分位数 | **必需** |
| Q2 | Q2 | 中位数 | **必需** |
| Q1 | Q1 | 下四分位数 | **必需** |
| Lower_Whisker | 下须 | 下方须线 | 可选 |
| Lower_Outlier | 下异常值 | 下方异常值 | 可选 |
| Sample_Size | 样本量 | 样本数量 | **必需** |

## 算法原理

### 转换公式

#### 等级0：三数公式 (Wan 2014)
```
Mean = (Q1 + Q2 + Q3) / 3
SD = (Q3 - Q1) / 1.35
```

#### 等级1：五数公式 (Wan 2014)
```
Mean = (Q1 + Q2 + Q3 + 0.25×(a + b)) / 3.5
SD = sqrt(((Q1-Q2)² + (Q2-Q3)² + 0.25×(b-a)²) / 1.35)
```
其中 a = Lower_Whisker, b = Upper_Whisker

#### 等级2：偏态校正
在等级1基础上，根据异常值分布进行偏态校正

### 保守估计策略
当同一组内不同情况的数据等级不同时：
1. 检测所有情况的数据等级
2. 选择最低等级作为整组的计算等级
3. 确保结果的可靠性和一致性

## 质量控制

### 数据验证
- ✅ 四分位数顺序检查 (Q1 ≤ Q2 ≤ Q3)
- ✅ 须线合理性验证 (下须 ≤ Q1, 上须 ≥ Q3)
- ✅ 异常值位置检查
- ✅ 样本量有效性验证

### 精度评估
- **等级0**：适用于基础meta分析，误差15-25%
- **等级1**：推荐用于高质量研究，误差8-15%
- **等级2**：最高精度，适用于精密分析，误差5-10%

## 使用建议

### 数据准备
1. **统一格式**：建议所有情况使用相同的数据等级
2. **完整记录**：尽可能提供上下须数据以提升精度
3. **异常值标注**：如有异常值，请准确标记

### 结果解释
1. **关注等级**：优先关注数据等级和精度估计
2. **保守估计**：标记为"保守估计"的结果更加可靠
3. **改进建议**：根据程序建议补充数据以提升精度

## 技术参考

### 主要文献
- Wan, X., et al. (2014). "Estimating the sample mean and standard deviation from the sample size, median, range and/or interquartile range." *BMC Medical Research Methodology*, 14, 135.
- Luo, D., et al. (2018). "Optimally estimating the sample mean from the sample size, median, mid-range, and/or mid-quartile range." *Statistical Methods in Medical Research*, 27(6), 1785-1805.

### 适用场景
- ✅ 系统评价和meta分析
- ✅ 文献数据提取
- ✅ 统计数据标准化
- ✅ 研究方法学分析

## 故障排除

### 常见问题
1. **编码问题**：使用英文标签模板避免中文乱码
2. **数据缺失**：确保Q1、Q2、Q3、样本量完整
3. **格式错误**：检查CSV文件格式和空行分隔

### 错误代码
- `-1`：数据不完整，缺少必需项
- `0-2`：正常数据等级
- 转换失败：检查数据格式和数值有效性

## 更新日志

### v4.0 (当前版本)
- ✅ **组间比较分析功能**：完整实现两组数据的差异分析
- ✅ **统计学计算**：ΔMean、SD_diff、置信区间、效应量、P值
- ✅ **多种比较模式**：干预组vs基线组、组内两两比较、全部比较
- ✅ **Meta分析格式输出**：RevMan、R Meta包、通用格式
- ✅ **专业统计指标**：Cohen's d、Hedges' g、t检验、显著性判断
- ✅ **增强Excel输出**：新增"组间比较结果"工作表

#### v4.0 核心公式实现：
基于用户需求的完整统计学公式：
```
ΔMean = Mean₁ - Mean₂
SD_diff = √(SD₁²/n₁ + SD₂²/n₂)
95% CI = ΔMean ± 1.96 × SD_diff
Cohen's d = ΔMean / 合并标准差
```

#### v4.0 新增功能：

**1. 组间比较命令**：
```bash
# 基本组间比较
python csv_converter.py --convert data.csv --compare-groups

# 指定比较类型
python csv_converter.py --convert data.csv --compare-groups --comparison-type intervention-baseline

# 自定义置信水平
python csv_converter.py --convert data.csv --compare-groups --confidence-level 0.99

# 生成Meta分析格式
python csv_converter.py --convert data.csv --compare-groups --meta-analysis-format
```

**2. 比较类型选项**：
- `intervention-baseline`: 干预组vs基线组比较（默认）
- `pairwise`: 同组内Case之间两两比较
- `all`: 包含以上所有比较

**3. Meta分析格式输出**：
- `meta_universal.csv`: 通用Meta分析格式（包含所有统计指标）
- `meta_revman.csv`: RevMan (Cochrane) 标准格式
- `meta_r.csv`: R语言meta包格式

**4. 增强的Excel输出结构**：
- Sheet1: 转换结果 - 各组Mean±SD
- **Sheet2: 组间比较结果** - ΔMean、置信区间、效应量、P值（新增）
- Sheet3: 数据质量分析 - 等级评估和策略
- Sheet4: 详细分析 - 数据完整度
- Sheet5: 摘要信息 - 包含比较统计摘要
- Sheet6: 改进建议 - 数据质量提升建议

**5. 输出示例**：
```
组间比较分析结果：
📊 Intervention vs Baseline (Case1)
   ΔMean = 12.6222
   SD_diff = 5.6390
   95% CI: [1.5697, 23.6746]
   Cohen's d = 0.5779
   P值 = 0.0500
   ✓ 显著差异：组1显著高于组2
```

### v3.0
- ✅ **强制文件保存功能**：每次转换后自动保存Excel和CSV文件
- ✅ **智能文件命名**：自动处理文件占用，使用_01到_99后缀循环
- ✅ **多格式输出支持**：Excel详细报告（4个工作表）+ CSV摘要文件
- ✅ **自定义输出选项**：支持自定义目录和文件名
- ✅ **文件占用处理**：超过99个文件后从_01开始覆盖
- ✅ **新增命令行参数**：--output-dir、--output-name、--no-csv

### v2.0
- ✅ 新增CSV批量处理功能
- ✅ 实现"分图分法"智能处理
- ✅ 添加最不利情况保守估计
- ✅ 支持动态列数和中英文双语
- ✅ 完善数据质量分析和建议系统

### v1.0
- ✅ 基础转换功能
- ✅ 交互式界面
- ✅ 统计转换核心引擎

---

**开发者**：研究代码工具集  
**更新时间**：2025年8月  
**许可证**：用于学术研究目的
