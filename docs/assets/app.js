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

function renderSummary() {
  const summary = state.summary.lotteries[state.currentType];
  const prediction = state.predictions[state.currentType];
  document.getElementById("latest-issue").textContent = summary.latest_issue;
  document.getElementById("latest-number").textContent = summary.latest_number;
  document.getElementById("records-count").textContent = summary.records_count.toLocaleString("zh-CN");
  document.getElementById("primary-prediction").textContent = prediction.primary_prediction;
  document.getElementById("window-size-chip").textContent = `预测窗口 ${prediction.window_size} 期`;
  document.getElementById("prediction-disclaimer").textContent = prediction.disclaimer;
}

function renderCandidates() {
  const prediction = state.predictions[state.currentType];
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
          <span>${(candidate.ratio * 100).toFixed(2)}%</span>
        </div>
        <div class="bar"><span style="width:${candidate.ratio * 100}%"></span></div>
      `;
      card.appendChild(item);
    });

    container.appendChild(card);
  });
}

function renderCombinations() {
  const prediction = state.predictions[state.currentType];
  const container = document.getElementById("recommended-combinations");
  container.innerHTML = "";

  prediction.recommended_combinations.forEach((combination, index) => {
    const card = document.createElement("article");
    card.className = "combination-card";
    card.innerHTML = `
      <span>推荐 ${index + 1}</span>
      <strong>${combination.number}</strong>
      <span>分数 ${combination.score.toFixed(6)}</span>
    `;
    container.appendChild(card);
  });
}

function getFilteredRecords() {
  const records = state.histories[state.currentType].records;
  if (!state.searchTerm) {
    return records;
  }
  return records.filter((record) =>
    record.issue.includes(state.searchTerm) || record.draw_date.includes(state.searchTerm),
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
  renderCandidates();
  renderCombinations();
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
