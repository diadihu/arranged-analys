# arranged-analys

中国体彩排列三、排列五历史数据抓取、训练回测、组合推荐与 GitHub Pages 展示项目。

## 项目目标

- 使用中国体彩网官方高速 JSON 接口同步排列三、排列五历史开奖数据
- 构建可复用的数据清洗、特征工程、训练、交叉验证与回测流程
- 提供一套可解释的简单推荐框架，并通过静态站点公开展示
- 通过 GitHub Actions 自动更新数据，并由 GitHub Pages 直接发布 `main/docs`

## 当前能力

- 官方历史开奖接口抓取与本地 CSV 归档
- 频次基线预测
- 基于滞后特征和滚动窗口统计的监督学习特征工程
- 时序交叉验证与留后回测
- 多模型基准筛选
  - `logreg`
  - `knn`
  - `random_forest`
  - `extra_trees`
- 基于模型概率、近期频次、胆码/独胆、和值尾数的组合排序
- GitHub Pages 静态站点展示历史开奖、回测指标、模型排行与推荐组合

## 目录结构

```text
arranged-analys/
├─ .github/
│  └─ workflows/
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

## 本地启动

1. 安装依赖

```powershell
pip install -e .
```

2. 构建历史数据与站点数据

```powershell
python .\scripts\build_site.py
```

脚本会更新这些内容：

- `data/raw/p3_history.csv`
- `data/raw/p5_history.csv`
- `data/processed/*.json`
- `docs/data/*.json`

3. 本地预览静态站点

```powershell
python -m http.server 8000 --directory .\docs
```

浏览器访问 [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## GitHub Pages 发布方式

推荐使用最稳定的静态目录发布方式：

1. 打开仓库 `Settings`
2. 打开 `Pages`
3. 在 `Build and deployment -> Source` 里选择 `Deploy from a branch`
4. Branch 选择 `main`
5. Folder 选择 `/docs`

这样之后：

- 站点静态文件直接来自仓库里的 `docs/`
- 每次 `main` 分支更新后，GitHub Pages 自动重新发布
- 不再依赖 `actions/deploy-pages` 的后端部署队列

项目 Pages 地址通常是：

`https://diadihu.github.io/arranged-analys/`

## 自动数据更新

仓库当前保留一条工作流：

- `.github/workflows/update-data.yml`
  - 支持手动触发
  - 每天定时抓取最新开奖数据
  - 自动运行 `python scripts/build_site.py`
  - 自动提交 `data/raw`、`data/processed`、`docs/data`

由于 Pages 直接发布 `main/docs`，所以这条工作流只要把最新数据提交回 `main`，站点就会自动更新。

## 当前推荐框架

当前不是“预测中奖”的强模型，而是一个可解释的数据实验框架，流程如下：

1. 对最近一段历史开奖构造滞后特征和滚动统计特征
2. 用多模型做时序交叉验证和留后回测
3. 按回测命中位数、整组命中率、数字重叠率等指标挑选当前最优模型
4. 输出下一期每一位的候选数字概率
5. 结合近期频次与简单规则对组合重新排序

## 免责声明

本项目仅用于数据分析、建模实验与研究展示，不构成任何投注建议或收益承诺。
