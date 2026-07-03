# arranged-analys

中国体彩排列三、排列五历史数据抓取、训练回测、组合推荐与 Vercel 静态展示项目。

## 项目目标

- 使用中国体彩网官方高速 JSON 接口同步排列三、排列五历史开奖数据
- 构建可复用的数据清洗、特征工程、训练、交叉验证与回测流程
- 提供一套可解释的简单组合推荐框架，并通过静态站点公开展示
- 通过 GitHub Actions 定时刷新数据，再由 Vercel 自动部署最新站点

## 当前能力

- 官方历史开奖接口抓取与本地 CSV 归档
- 抓取失败时自动回退到本地缓存 CSV，避免整站构建中断
- 频次基线预测
- 基于滞后特征与滚动窗口统计的监督学习特征工程
- 时序交叉验证与留后回测
- 多模型基准筛选
  - `logreg`
  - `knn`
  - `random_forest`
  - `extra_trees`
- 位置级预测概率输出
- 组合级回放指标
  - `Top1` 命中率
  - `Top5` 覆盖率
  - `Top10` 覆盖率
  - `Top1` 平均重叠率
  - `Top1` 至少一位命中率
- 基于模型概率、近期频次和弱化规则项的组合排序
- 组合权重自动选择，会根据留后回放结果在候选权重配置里挑当前最稳的一组

## 目录结构

```text
arranged-analys/
├─ .github/
│  └─ workflows/
├─ data/
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

2. 生成历史数据与站点数据

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

## Vercel 部署

当前仓库按静态目录方式部署到 Vercel：

- `outputDirectory`: `docs`
- 推送到 GitHub 默认分支后，Vercel 会自动重新构建并发布
- 只要仓库里的 `docs/` 和 `docs/data/` 更新，线上页面就会同步变化

如果你已经把 GitHub 仓库连接到 Vercel，后续正常 `git push` 即可触发自动更新。

## 自动数据更新

仓库保留了定时任务：

- `.github/workflows/update-data.yml`
  - 支持手动触发
  - 每天定时抓取最新开奖数据
  - 自动运行 `python scripts/build_site.py`
  - 自动提交 `data/raw`、`data/processed`、`docs/data`

因为 Vercel 监听的是 GitHub 仓库，所以这条工作流只要成功把最新数据推回 `main`，Vercel 就会跟着自动部署。

## 当前推荐框架

当前不是“预测中奖”的强模型，而是一套可解释的数据实验流程：

1. 对最近一段历史开奖构造滞后特征和滚动统计特征
2. 用多模型做时序交叉验证和留后回测
3. 按位置级回测表现选当前最稳模型
4. 输出下一期每个位置的候选数字概率
5. 使用多组组合权重配置做留后回放
6. 选出组合级回放表现更稳的权重，再生成当前推荐组合

## 免责声明

本项目仅用于数据分析、建模实验与研究展示，不构成任何投注建议或收益承诺。
