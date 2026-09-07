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

- Vercel 项目的 Root Directory 为 `docs`
- 推送到 GitHub 默认分支后，Vercel 会自动重新构建并发布
- 只要仓库里的 `docs/` 和 `docs/data/` 更新，线上页面就会同步变化

如果你已经把 GitHub 仓库连接到 Vercel，后续正常 `git push` 即可触发自动更新。

## 自动数据更新

中国体彩网官方接口会对 GitHub Hosted Runner 和 Vercel Function 等云出口返回 `HTTP 567`。因此生产更新采用“本机抓取和训练、GitHub 保存结果、Vercel 自动发布”的链路，数据源仍是中国体彩网官方接口。

仓库提供本地同步发布脚本：

```powershell
.\scripts\sync-and-publish.ps1
```

脚本会：

1. 对 `main` 执行 `git pull --ff-only`
2. 从官方接口增量追赶排列三、排列五历史开奖
3. 发现新期开奖后重新训练、交叉验证、回测并生成策略
4. 只暂存 `data/raw`、`data/processed`、`docs/data` 中的已知产物
5. 自动提交并推送，随后由 Vercel Git 集成发布

没有新期开奖时脚本不会训练、提交或触发无意义部署。可用以下命令只检查本机依赖：

```powershell
.\scripts\sync-and-publish.ps1 -CheckOnly
```

云端工作流 `.github/workflows/update-data.yml` 保留为手动网络诊断，不再定时运行，避免每天产生已知的 `HTTP 567` 失败记录。实际定时任务在北京时间 21:47、23:47 和次日 06:47 从本机执行上述脚本，以吸收开奖发布时间和网络波动。

同步逻辑具备以下保护：

- 逐页追赶直到与本地历史期号重叠，避免停更后漏期
- 官方接口失败时直接失败，不把旧缓存误报为更新成功
- 互斥锁阻止多个计划任务并发运行
- 策略明确记录其所依据的最后一期，避免把旧策略当成最新预测

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
