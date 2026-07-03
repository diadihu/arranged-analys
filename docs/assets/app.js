const state = {
  currentType: "p3",
  currentPage: 1,
  pageSize: 20,
  searchTerm: "",
  summary: null,
  predictions: null,
  histories: {
    p3: null,
    p5: null,
  },
};

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return response.json();
}

function formatDateTime(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return isoString;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatPercent(value) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatDecimal(value, digits = 3) {
  return value.toFixed(digits);
}

function formatMetricValue(kind, value) {
  if (kind === "percent") {
    return formatPercent(value);
  }
  return formatDecimal(value);
}

function getPrediction() {
  return state.predictions[state.currentType];
}

function getBestBenchmark() {
  const prediction = getPrediction();
  return prediction.benchmark_table.find(
    (item) =>
      item.model_name === prediction.best_model_name &&
      item.feature_config === prediction.best_feature_config,
  );
}

function renderSummary() {
  const summary = state.summary.lotteries[state.currentType];
  const prediction = getPrediction();
  const ruleProfile = prediction.rule_profile;

  document.getElementById("latest-issue").textContent = summary.latest_issue;
  document.getElementById("latest-number").textContent = summary.latest_number;
  document.getElementById("records-count").textContent = summary.records_count.toLocaleString("zh-CN");
  document.getElementById("baseline-prediction").textContent = prediction.baseline_prediction;
  document.getElementById("best-combo-number").textContent = prediction.best_combo.number;
  document.getElementById("best-combo-score").textContent =
    `综合得分 ${prediction.best_combo.combined_score.toFixed(6)} / 权重 ${prediction.combination_profile.name}`;
  document.getElementById("best-model-name").textContent = prediction.best_model_name;
  document.getElementById("best-model-config").textContent = prediction.best_feature_config;
  document.getElementById("holdout-chip").textContent = `留后回测窗口 ${prediction.holdout_size} 期`;
  document.getElementById("prediction-disclaimer").textContent = prediction.disclaimer;
  document.getElementById("rule-profile-chip").textContent =
    `胆码 ${ruleProfile.danma_digits.join("") || "-"} / 独胆 ${ruleProfile.dudan_digits.join("") || "-"} / 频次窗 ${prediction.combination_profile.frequency_window}`;
}

function renderMetrics() {
  const prediction = getPrediction();
  const bestBenchmark = getBestBenchmark();
  const comboBacktest = prediction.combo_backtest;
  const container = document.getElementById("metrics-grid");
  container.innerHTML = "";

  const metricEntries = [
    ["位置平均命中数", prediction.holdout_metrics.mean_position_hits, "number"],
    ["位置命中率", prediction.holdout_metrics.position_accuracy, "percent"],
    ["整组命中率", prediction.holdout_metrics.exact_match_rate, "percent"],
    ["数字重叠率", prediction.holdout_metrics.mean_digit_overlap, "percent"],
    ["至少 1 位命中率", prediction.holdout_metrics.at_least_one_hit_rate, "percent"],
    ["组合 Top1 命中率", comboBacktest.top1_exact_rate, "percent"],
    ["组合 Top5 覆盖率", comboBacktest.top5_exact_rate, "percent"],
    ["组合 Top10 覆盖率", comboBacktest.top10_exact_rate, "percent"],
    ["组合 Top1 平均重叠", comboBacktest.top1_mean_digit_overlap, "number"],
    ["组合 Top1 至少一位命中率", comboBacktest.top1_at_least_one_hit_rate, "percent"],
  ];

  metricEntries.forEach(([label, value, kind]) => {
    const card = document.createElement("article");
    card.className = "metric-box";
    card.innerHTML = `
      <span>${label}</span>
      <strong>${formatMetricValue(kind, value)}</strong>
    `;
    container.appendChild(card);
  });

  if (bestBenchmark) {
    const cvCard = document.createElement("article");
    cvCard.className = "metric-box";
    cvCard.innerHTML = `
      <span>CV 平均命中位数</span>
      <strong>${formatDecimal(bestBenchmark.cv_metrics.mean_position_hits)}</strong>
      <small>${prediction.best_feature_config}</small>
    `;
    container.appendChild(cvCard);
  }

  const sampleCard = document.createElement("article");
  sampleCard.className = "metric-box";
  sampleCard.innerHTML = `
    <span>组合回放样本数</span>
    <strong>${comboBacktest.sample_count}</strong>
    <small>使用留后窗口逐期回放</small>
  `;
  container.appendChild(sampleCard);
}

function renderCandidates() {
  const prediction = getPrediction();
  const container = document.getElementById("position-candidates");
  container.innerHTML = "";

  prediction.positional_candidates.forEach((group, index) => {
    const card = document.createElement("article");
    card.className = "candidate-card";
    const title = document.createElement("h3");
    title.textContent = `第 ${index + 1} 位`;
    card.appendChild(title);

    group.forEach((candidate) => {
      const item = document.createElement("div");
      item.className = "candidate-item";
      item.innerHTML = `
        <div class="candidate-item-head">
          <strong>${candidate.digit}</strong>
          <span>${formatPercent(candidate.probability)}</span>
        </div>
        <div class="bar"><span style="width:${candidate.probability * 100}%"></span></div>
      `;
      card.appendChild(item);
    });

    container.appendChild(card);
  });
}

function renderCombinations() {
  const prediction = getPrediction();
  const container = document.getElementById("recommended-combinations");
  const bestContainer = document.getElementById("best-combination");
  container.innerHTML = "";

  const [best, ...rest] = prediction.recommended_combinations;
  bestContainer.innerHTML = `
    <div class="combination-card-best">
      <span>当前最优组合</span>
      <strong>${best.number}</strong>
      <p>综合得分 ${best.combined_score.toFixed(6)}，模型概率 ${best.ml_probability.toFixed(8)}，频次分 ${best.frequency_score.toFixed(6)}，规则分 ${best.rule_score.toFixed(6)}</p>
      <p class="combination-note">${best.explanation.length ? best.explanation.join("；") : "无额外规则说明"}</p>
    </div>
  `;

  rest.forEach((combination, index) => {
    const card = document.createElement("article");
    card.className = "combination-card";
    card.innerHTML = `
      <span>候选 ${index + 2}</span>
      <strong>${combination.number}</strong>
      <small>综合得分 ${combination.combined_score.toFixed(6)}</small>
      <p class="combination-note">${combination.explanation.length ? combination.explanation.join("；") : "无额外规则说明"}</p>
    `;
    container.appendChild(card);
  });
}

function renderBenchmarkTable() {
  const prediction = getPrediction();
  const tbody = document.getElementById("benchmark-table-body");
  tbody.innerHTML = "";

  prediction.benchmark_table.forEach((benchmark) => {
    const tr = document.createElement("tr");
    const isBest =
      benchmark.model_name === prediction.best_model_name &&
      benchmark.feature_config === prediction.best_feature_config;

    if (isBest) {
      tr.classList.add("is-best-row");
    }

    tr.innerHTML = `
      <td>${benchmark.model_name}</td>
      <td>${benchmark.feature_config}</td>
      <td>${formatDecimal(benchmark.cv_metrics.mean_position_hits)}</td>
      <td>${formatDecimal(benchmark.holdout_metrics.mean_position_hits)}</td>
      <td>${formatPercent(benchmark.holdout_metrics.exact_match_rate)}</td>
      <td>${formatPercent(benchmark.holdout_metrics.mean_digit_overlap)}</td>
      <td>${formatPercent(benchmark.holdout_metrics.at_least_one_hit_rate)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function getFilteredRecords() {
  const records = state.histories[state.currentType].records;
  if (!state.searchTerm) {
    return records;
  }
  return records.filter(
    (record) => record.issue.includes(state.searchTerm) || record.draw_date.includes(state.searchTerm),
  );
}

function renderHistory() {
  const filtered = getFilteredRecords().slice().reverse();
  const totalPages = Math.max(1, Math.ceil(filtered.length / state.pageSize));
  state.currentPage = Math.min(state.currentPage, totalPages);

  const start = (state.currentPage - 1) * state.pageSize;
  const pageItems = filtered.slice(start, start + state.pageSize);
  const tbody = document.getElementById("history-table-body");
  tbody.innerHTML = "";

  pageItems.forEach((record) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${record.draw_date}</td>
      <td>${record.issue}</td>
      <td>${record.number}</td>
      <td><a href="${record.detail_url}" target="_blank" rel="noreferrer">查看</a></td>
    `;
    tbody.appendChild(tr);
  });

  document.getElementById("page-indicator").textContent = `${state.currentPage} / ${totalPages}`;
  document.getElementById("prev-page").disabled = state.currentPage <= 1;
  document.getElementById("next-page").disabled = state.currentPage >= totalPages;
}

function renderAll() {
  renderSummary();
  renderMetrics();
  renderCandidates();
  renderCombinations();
  renderBenchmarkTable();
  renderHistory();
}

function bindEvents() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.currentType = button.dataset.type;
      state.currentPage = 1;
      state.searchTerm = "";
      document.getElementById("history-search").value = "";
      renderAll();
    });
  });

  document.getElementById("history-search").addEventListener("input", (event) => {
    state.searchTerm = event.target.value.trim();
    state.currentPage = 1;
    renderHistory();
  });

  document.getElementById("prev-page").addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage -= 1;
      renderHistory();
    }
  });

  document.getElementById("next-page").addEventListener("click", () => {
    state.currentPage += 1;
    renderHistory();
  });
}

async function bootstrap() {
  try {
    const [summary, predictions, p3History, p5History] = await Promise.all([
      loadJson("./data/summary.json"),
      loadJson("./data/predictions.json"),
      loadJson("./data/p3-history.json"),
      loadJson("./data/p5-history.json"),
    ]);

    state.summary = summary;
    state.predictions = predictions;
    state.histories.p3 = p3History;
    state.histories.p5 = p5History;

    document.getElementById("data-source-name").textContent = summary.data_source.name;
    document.getElementById("updated-at").textContent = formatDateTime(summary.updated_at);
    bindEvents();
    renderAll();
  } catch (error) {
    console.error(error);
    document.body.innerHTML = `
      <div style="padding:40px;font-family:'Segoe UI','Microsoft YaHei',sans-serif">
        <h1>页面加载失败</h1>
        <p>未能读取站点数据，请稍后刷新重试。</p>
      </div>
    `;
  }
}

bootstrap();
