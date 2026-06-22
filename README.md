# arranged-analys

体彩排列三、排列五历史数据整理、分析建模与未来开奖模式研究项目。

## 项目目标

- 统一沉淀排列三、排列五历史开奖数据
- 建立清洗、特征工程、实验建模的标准流程
- 提供可复用的数据挖掘与基线预测代码
- 为后续更复杂的时序建模、组合分析、回测评估预留结构

## 当前初始化内容

- Python 项目基础结构
- 数据目录分层
- 历史开奖 CSV 读取器
- 基础特征工程入口
- 一个可运行的频次基线预测器
- 测试骨架

## 目录结构

```text
arranged-analys/
├─ data/
│  ├─ external/
│  ├─ processed/
│  └─ raw/
├─ scripts/
├─ src/
│  └─ arranged_analys/
│     ├─ data/
│     ├─ features/
│     └─ models/
└─ tests/
```

## 建议数据格式

历史开奖数据建议统一为 CSV，至少包含以下字段：

```csv
draw_date,lottery_type,issue,d1,d2,d3,d4,d5
2026-01-01,p3,2026001,1,2,3,,
2026-01-01,p5,2026001,1,2,3,4,5
```

说明：

- `lottery_type`：`p3` 表示排列三，`p5` 表示排列五
- `d1 ~ d5`：对应开奖数字位
- 排列三仅使用 `d1 ~ d3`

你可以把数据文件放在 `data/raw/` 下，例如：

- `data/raw/p3_history.csv`
- `data/raw/p5_history.csv`

## 快速开始

1. 创建虚拟环境并安装依赖

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

2. 准备历史数据 CSV

3. 运行基线预测示例

```powershell
python .\scripts\run_baseline.py --file .\data\raw\p3_history.csv --type p3
python .\scripts\run_baseline.py --file .\data\raw\p5_history.csv --type p5
```

## 后续建议

- 增加数据采集脚本，自动同步历史开奖数据
- 引入遗漏值、和值、跨度、奇偶比、大小比等特征
- 加入时间窗口训练与滚动回测
- 增加分类模型、序列模型与组合评分机制
- 输出实验报告与可视化分析结果

## 免责声明

本项目仅用于数据分析、建模实验与研究，不构成任何中奖承诺或投资建议。
