# arranged-analys

体彩排列三、排列五历史数据整理、官方接口抓取展示、分析建模与未来开奖模式研究项目。

## 项目目标

- 统一沉淀排列三、排列五历史开奖数据
- 通过中国体彩网官方 JSON 接口自动抓取并更新历史开奖数据
- 建立清洗、特征工程、实验建模的标准流程
- 提供可复用的数据挖掘与基线预测代码
- 通过 GitHub Pages 对外展示历史数据和最新预测结果
- 为后续更复杂的时序建模、组合分析、回测评估预留结构

## 当前初始化内容

- Python 项目基础结构
- 中国体彩网官方 JSON 接口抓取器
- 历史 CSV 与前端 JSON 生成
- 一个可运行的频次基线预测器
- GitHub Pages 静态站点
- GitHub Actions 自动同步与部署
- 测试骨架

## 目录结构

```text
arranged-analys/
├─ data/
│  ├─ external/
│  ├─ processed/
│  └─ raw/
├─ docs/
├─ scripts/
├─ src/
│  └─ arranged_analys/
│     ├─ data/
│     ├─ features/
│     └─ models/
└─ tests/
```

## 快速开始

1. 生成历史数据和站点资源

```powershell
python .\scripts\build_site.py
```

在首次本地运行前，建议先安装依赖：

```powershell
pip install -e .
```

脚本会自动完成：

- 抓取排列三历史数据到 `data/raw/p3_history.csv`
- 抓取排列五历史数据到 `data/raw/p5_history.csv`
- 生成前端 JSON 到 `docs/data/`
- 生成预测摘要到 `data/processed/`

2. 本地预览静态站点

如果本地有 Python：

```powershell
python -m http.server 8000 --directory .\docs
```

然后访问 `http://localhost:8000`。

## GitHub Pages 部署

仓库内已提供两个工作流：

- `.github/workflows/update-data.yml`
  - 每天自动同步一次最新历史数据
  - 也支持在 GitHub Actions 页面手动执行
- `.github/workflows/deploy-pages.yml`
  - 在 `main` 分支有提交时自动部署 `docs/`

还需要在 GitHub 仓库页面手动做一次设置：

1. 进入 `Settings`
2. 打开 `Pages`
3. 在 `Source` 中选择 `GitHub Actions`

完成后，站点地址通常是：

`https://diadihu.github.io/arranged-analys/`

## 当前预测逻辑

目前是一个简单、可解释的基线框架：

- 取最近一段历史窗口
- 分别统计每一位数字的出现频次
- 每位最高频数字组成主推荐号码
- 再把每位高频候选做组合，输出若干实验性推荐

## 后续建议

- 增加历史数据断点续抓和数据源容错
- 引入遗漏值、和值、跨度、奇偶比、大小比等特征
- 加入滚动窗口回测，评估不同窗口长度
- 增加多模型打分与组合排序
- 增加走势图、冷热号、遗漏统计等前端分析模块

## 当前官方接口说明

当前接入的是中国体彩网页面脚本实际调用的官方接口：

- 历史分页接口：`getHistoryPageListV1.qry`

由于官方接口有风控拦截，普通 `requests/urllib` 在部分环境会返回 `403` 或 `567`，当前项目使用 `curl-cffi` 以浏览器指纹方式访问官方接口。

当前实现策略：

- 每次从官方 JSON 接口刷新最新历史页
- 再与仓库内已有历史归档合并

这样可以稳定保持“最新数据来自官方接口”，同时避免官方深翻页请求在无浏览器会话环境下被 WAF 拦截。

## 免责声明

本项目仅用于数据分析、建模实验与研究，不构成任何中奖承诺或投资建议。
