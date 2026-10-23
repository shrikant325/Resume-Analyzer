document.addEventListener("DOMContentLoaded", function () {
  // File input filename preview for the drag-and-drop-styled upload box.
  document.querySelectorAll("input[type='file']").forEach(function (input) {
    input.addEventListener("change", function () {
      var label = document.querySelector("[data-file-label]");
      if (label && input.files.length) {
        label.textContent = input.files[0].name;
      }
    });
  });

  // Animate every score ring's circular progress on load.
  document.querySelectorAll("[data-score-ring]").forEach(function (el) {
    var score = parseFloat(el.getAttribute("data-score-ring")) || 0;
    var circle = el.querySelector("circle.ring-progress");
    if (!circle) return;
    var radius = circle.r.baseVal.value;
    var circumference = 2 * Math.PI * radius;
    circle.style.strokeDasharray = circumference;
    circle.style.strokeDashoffset = circumference;
    requestAnimationFrame(function () {
      circle.style.strokeDashoffset = circumference - (Math.min(score, 100) / 100) * circumference;
    });
  });
});

var CHART_COLORS = {
  brand: "#3652e0",
  success: "#0f9d6e",
  warning: "#d97706",
  danger: "#dc2626",
  grid: "#e3e7f1",
};

function renderBarChart(canvasId, labels, data, colors) {
  var ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === "undefined") return null;
  return new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{ data: data, backgroundColor: colors || CHART_COLORS.brand, borderRadius: 6, maxBarThickness: 46 }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100, grid: { color: CHART_COLORS.grid }, ticks: { callback: function (v) { return v + "%"; } } },
        x: { grid: { display: false } },
      },
    },
  });
}

function renderDoughnutChart(canvasId, labels, data, colors) {
  var ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === "undefined") return null;
  return new Chart(ctx, {
    type: "doughnut",
    data: { labels: labels, datasets: [{ data: data, backgroundColor: colors, borderWidth: 0 }] },
    options: { responsive: true, cutout: "68%", plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } } } },
  });
}

function renderLineChart(canvasId, labels, data) {
  var ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === "undefined") return null;
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        data: data, borderColor: CHART_COLORS.brand, backgroundColor: "rgba(54,82,224,0.08)",
        fill: true, tension: 0.35, pointBackgroundColor: CHART_COLORS.brand, pointRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, max: 100, grid: { color: CHART_COLORS.grid } }, x: { grid: { display: false } } },
    },
  });
}
