/* Energy chart component for the dashboard.
 *
 * Defined as a static file (loaded in base.html) so it exists before Alpine
 * evaluates the lazy-loaded /app/dashboard/chart partial.
 */
function energyChartComponent(rawChartData) {
  return {
    rawPoints: rawChartData || [],
    limit: 12,
    view: "flow",
    tabs: [
      { id: "flow", label: "Energy Flow" },
      { id: "daily", label: "Daily Rates" },
      { id: "net", label: "Net Balance" },
      { id: "split", label: "Solar Split" },
      { id: "cumulative", label: "Cumulative" },
    ],

    init() {
      this.renderChart();
    },

    getFilteredData() {
      if (!this.rawPoints.length) return [];
      const lim = parseInt(this.limit, 10);
      if (lim === 0 || this.rawPoints.length <= lim) {
        return this.rawPoints;
      }
      return this.rawPoints.slice(-lim);
    },

    cumulative(arr) {
      let s = 0;
      return arr.map((v) => (s += v || 0));
    },

    buildDatasets(points) {
      if (this.view === "flow") {
        return [
          {
            label: "Solar Gen (kWh)",
            data: points.map((p) => p.solar_gen),
            backgroundColor: "#f59e0b",
            borderRadius: 4,
            barPercentage: 0.7,
            categoryPercentage: 0.6,
          },
          {
            label: "Export (kWh)",
            data: points.map((p) => p.export),
            backgroundColor: "#10b981",
            borderRadius: 4,
            barPercentage: 0.7,
            categoryPercentage: 0.6,
          },
          {
            label: "Import (kWh)",
            data: points.map((p) => p.import),
            backgroundColor: "#ef4444",
            borderRadius: 4,
            barPercentage: 0.7,
            categoryPercentage: 0.6,
          },
          {
            type: "line",
            label: "Self-Sufficiency (%)",
            data: points.map((p) => p.self_sufficiency_pct),
            borderColor: "#10b981",
            backgroundColor: "#10b981",
            borderWidth: 2.5,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: "#0f172a",
            pointBorderColor: "#10b981",
            pointBorderWidth: 2,
            tension: 0.35,
            yAxisID: "y1",
          },
          {
            type: "line",
            label: "Self-Consumption (%)",
            data: points.map((p) => p.self_consumption_pct),
            borderColor: "#F5E027",
            backgroundColor: "#F5E027",
            borderWidth: 2.5,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: "#0f172a",
            pointBorderColor: "#F5E027",
            pointBorderWidth: 2,
            tension: 0.35,
            yAxisID: "y1",
          },
        ];
      }

      if (this.view === "daily") {
        return [
          { label: "Solar/day", data: points.map((p) => p.solar_per_day), backgroundColor: "#f59e0b", borderRadius: 4, barPercentage: 0.7, categoryPercentage: 0.6 },
          { label: "Import/day", data: points.map((p) => p.import_per_day), backgroundColor: "#ef4444", borderRadius: 4, barPercentage: 0.7, categoryPercentage: 0.6 },
          { label: "Export/day", data: points.map((p) => p.export_per_day), backgroundColor: "#10b981", borderRadius: 4, barPercentage: 0.7, categoryPercentage: 0.6 },
          { label: "Consumption/day", data: points.map((p) => p.consumption_per_day), backgroundColor: "#06b6d4", borderRadius: 4, barPercentage: 0.7, categoryPercentage: 0.6 },
        ];
      }

      if (this.view === "net") {
        const net = points.map((p) => p.net_balance);
        return [
          { type: "bar", label: "Net balance (kWh)", data: net, backgroundColor: net.map((v) => (v >= 0 ? "#10b981" : "#ef4444")), borderRadius: 4, barPercentage: 0.7, categoryPercentage: 0.6 },
          { type: "line", label: "Cumulative net (kWh)", data: this.cumulative(net), borderColor: "#f59e0b", backgroundColor: "#f59e0b", borderWidth: 2.5, pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: "#0f172a", pointBorderColor: "#f59e0b", pointBorderWidth: 2, tension: 0.35 },
        ];
      }

      if (this.view === "split") {
        return [
          { label: "Self-consumed solar", data: points.map((p) => p.self_consumed), backgroundColor: "#f59e0b", stack: "solar", borderRadius: 4, barPercentage: 0.7, categoryPercentage: 0.6 },
          { label: "Exported solar", data: points.map((p) => p.export), backgroundColor: "#10b981", stack: "solar", borderRadius: 4, barPercentage: 0.7, categoryPercentage: 0.6 },
          { label: "Grid import", data: points.map((p) => p.import), backgroundColor: "#ef4444", borderRadius: 4, barPercentage: 0.7, categoryPercentage: 0.6 },
        ];
      }

      return [
        { type: "line", label: "Solar (cumulative)", data: this.cumulative(points.map((p) => p.solar_gen)), borderColor: "#f59e0b", borderWidth: 2, pointRadius: 2, pointHoverRadius: 4, tension: 0.3, fill: false },
        { type: "line", label: "Export (cumulative)", data: this.cumulative(points.map((p) => p.export)), borderColor: "#10b981", borderWidth: 2, pointRadius: 2, pointHoverRadius: 4, tension: 0.3, fill: false },
        { type: "line", label: "Import (cumulative)", data: this.cumulative(points.map((p) => p.import)), borderColor: "#ef4444", borderWidth: 2, pointRadius: 2, pointHoverRadius: 4, tension: 0.3, fill: false },
        { type: "line", label: "Consumption (cumulative)", data: this.cumulative(points.map((p) => p.consumption)), borderColor: "#06b6d4", borderWidth: 2, pointRadius: 2, pointHoverRadius: 4, tension: 0.3, fill: false },
      ];
    },

    chartTitle() {
      return {
        flow: "Energy Flow - Grid Balance",
        daily: "Daily rates (kWh/day)",
        net: "Net grid balance (kWh)",
        split: "Solar: self-consumed vs exported (kWh)",
        cumulative: "Cumulative energy (kWh)",
      }[this.view];
    },

    renderChart() {
      const dataPoints = this.getFilteredData();
      const scales = {
        x: {
          ticks: { color: "#64748b", font: { size: 10 } },
          grid: { color: "#1e293b" },
        },
        y: {
          ticks: { color: "#64748b", font: { size: 10 } },
          grid: { color: "#1e293b" },
        },
      };

      if (this.view === "flow") {
        scales.y1 = {
          type: "linear",
          position: "right",
          min: 0,
          max: 100,
          ticks: {
            color: "#10b981",
            font: { size: 10, family: "monospace" },
            callback: (val) => val + "%",
          },
          title: {
            display: true,
            color: "#10b981",
            font: { size: 11, family: "monospace", weight: "bold" },
          },
          grid: { drawOnChartArea: false },
          border: { dash: [4, 4] },
        };
      }

      const config = {
        type: "bar",
        data: {
          labels: dataPoints.map((p) => p.label),
          datasets: this.buildDatasets(dataPoints),
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: {
                color: "#94a3b8",
                font: { size: 11, family: "sans-serif" },
                boxWidth: 12,
              },
            },
            title: {
              display: true,
              text: this.chartTitle(),
              color: "#94a3b8",
              font: { size: 12, family: "sans-serif" },
              padding: { bottom: 8 },
            },
            tooltip: {
              mode: "index",
              intersect: false,
              backgroundColor: "#0f172a",
              titleColor: "#f8fafc",
              bodyColor: "#cbd5e1",
              borderColor: "#334155",
              borderWidth: 1,
            },
          },
          scales,
        },
      };

      // The chart is stored on the canvas element, which is reachable from
      // every Alpine scope (the tab buttons live in an x-for child scope, so
      // this.$el is not the component root there). Keeping it off Alpine state
      // also avoids Chart.js internals passing through Alpine's reactive proxy.
      const canvas = this.$refs.chartCanvas;
      if (canvas._chart) {
        const chart = canvas._chart;
        chart.data = config.data;
        chart.options = config.options;
        chart.update();
        return;
      }

      canvas._chart = new Chart(canvas.getContext("2d"), config);
    },

    updateChart() {
      this.renderChart();
    },
  };
}
