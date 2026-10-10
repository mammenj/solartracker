<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solar & Grid Tracker</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        slate: {
                            950: '#020817'
                        },
                        brand: {
                            50: '#eff6ff',
                            100: '#dbeafe',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        }
                    }
                }
            }
        }

function formatPeriodLabel(startValue) {
    if (!startValue) return 'Period';
    
    // Clean up if the string contains fallback backend object text
    let cleanString = String(startValue);
    if (cleanString.includes('MetereadingObject')) {
        return 'Custom Date'; 
    }

    try {
        const date = new Date(cleanString);
        if (!Number.isNaN(date.getTime())) {
            return date.toLocaleDateString(undefined, { day: '2-digit', month: '2-digit', year: '2-digit' });
        }
    } catch (e) {}
    
    return cleanString.split('T')[0];
}
function initChart() {
    const ctx = document.getElementById('energyChart');
    const emptyState = document.getElementById('chart-empty');
    const chartWrap = document.getElementById('chart-wrap');
    const periods = window.chartData || [];

    console.log("Loaded chartData length:", periods.length);
    console.log("Raw period items:", periods);

    if (!ctx) return;
    if (!periods.length) {
        if (chartWrap) chartWrap.classList.add('hidden');
        if (emptyState) emptyState.classList.remove('hidden');
        return;
    }
    if (chartWrap) chartWrap.classList.remove('hidden');
    if (emptyState) emptyState.classList.add('hidden');

    const labels = periods.map(p => formatPeriodLabel(p.start));
    const importData = periods.map(p => Number(p.import_diff) || 0);
    const exportData = periods.map(p => Number(p.export_diff) || 0);
    const solarData = periods.map(p => Number(p.solar_yield) || 0);
    const consumptionData = periods.map(p => Number(p.consumption) || 0);
    const weeklyImportData = periods.map(p => Number(p.weekly_import) || 0);
    const weeklyExportData = periods.map(p => Number(p.weekly_export) || 0);
    const weeklySolarData = periods.map(p => Number(p.weekly_solar) || 0);
    const weeklyConsumptionData = periods.map(p => Number(p.weekly_consumption) || 0);

    // <-- Moved console.logs here after variables exist
    console.log("Parsed Import Data:", importData);
    console.log("Parsed Solar Data:", solarData);

   // ... rest of your chart initialization code
        
        ////15:07:54
            if (window.energyChartInstance) {
                window.energyChartInstance.destroy();
            }

            const datasets = [
                {
                    label: 'Import',
                    data: importData,
                    borderColor: '#fbbf24',
                    backgroundColor: 'rgba(251, 191, 36, 0.12)',
                    fill: false,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: '#fbbf24'
                },
                {
                    label: 'Import (7d)',
                    data: weeklyImportData,
                    borderColor: '#fbbf24',
                    backgroundColor: 'rgba(251, 191, 36, 0.06)',
                    fill: false,
                    tension: 0.35,
                    pointRadius: 2,
                    pointBackgroundColor: '#fbbf24',
                    borderDash: [6, 6]
                },
                {
                    label: 'Export',
                    data: exportData,
                    borderColor: '#34d399',
                    backgroundColor: 'rgba(52, 211, 153, 0.12)',
                    fill: false,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: '#34d399'
                },
                {
                    label: 'Export (7d)',
                    data: weeklyExportData,
                    borderColor: '#34d399',
                    backgroundColor: 'rgba(52, 211, 153, 0.06)',
                    fill: false,
                    tension: 0.35,
                    pointRadius: 2,
                    pointBackgroundColor: '#34d399',
                    borderDash: [6, 6]
                },
                {
                    label: 'Solar',
                    data: solarData,
                    borderColor: '#fb923c',
                    backgroundColor: 'rgba(251, 146, 60, 0.12)',
                    fill: false,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: '#fb923c'
                },
                {
                    label: 'Solar (7d)',
                    data: weeklySolarData,
                    borderColor: '#fb923c',
                    backgroundColor: 'rgba(251, 146, 60, 0.06)',
                    fill: false,
                    tension: 0.35,
                    pointRadius: 2,
                    pointBackgroundColor: '#fb923c',
                    borderDash: [6, 6]
                },
                {
                    label: 'Consumption',
                    data: consumptionData,
                    borderColor: '#60a5fa',
                    backgroundColor: 'rgba(96, 165, 250, 0.12)',
                    fill: false,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: '#60a5fa'
                },
                {
                    label: 'Consumption (7d)',
                    data: weeklyConsumptionData,
                    borderColor: '#60a5fa',
                    backgroundColor: 'rgba(96, 165, 250, 0.06)',
                    fill: false,
                    tension: 0.35,
                    pointRadius: 2,
                    pointBackgroundColor: '#60a5fa',
                    borderDash: [6, 6]
                }
            ];

            window.energyChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Energy overview by period',
                            color: '#e2e8f0',
                            font: { size: 14, weight: '600' },
                            padding: { top: 8, bottom: 12 }
                        },
                        legend: {
                            position: 'top',
                            labels: {
                                color: '#cbd5e1',
                                font: { size: 12, weight: '500' },
                                padding: 16,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.92)',
                            titleColor: '#f8fafc',
                            bodyColor: '#e2e8f0',
                            borderColor: '#475569',
                            borderWidth: 1,
                            padding: 12,
                            cornerRadius: 8,
                            displayColors: true
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(148, 163, 184, 0.08)',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#94a3b8',
                                font: { size: 11 }
                            }
                        },
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: 'rgba(148, 163, 184, 0.08)',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#94a3b8',
                                font: { size: 11 },
                                callback: function(value) {
                                    return value + ' kWh';
                                }
                            },
                            title: {
                                display: true,
                                text: 'kWh',
                                color: '#94a3b8'
                            }
                        }
                    }
                }
            });
        }
          function switchTab(tabName) {
            document.getElementById('table-tab').classList.add('hidden');
            document.getElementById('chart-tab').classList.add('hidden');

            document.getElementById('table-btn').classList.remove('border-blue-500', 'text-white');
            document.getElementById('chart-btn').classList.remove('border-blue-500', 'text-white');
            document.getElementById('table-btn').classList.add('text-slate-400');
            document.getElementById('chart-btn').classList.add('text-slate-400');

            document.getElementById(tabName + '-btn').classList.remove('text-slate-400');
            document.getElementById(tabName + '-btn').classList.add('border-blue-500', 'text-white');

            document.getElementById(tabName + '-tab').classList.remove('hidden');

            if (tabName === 'chart') {
              setTimeout(() => {
                initChart();
                if (window.energyChartInstance) {
                  window.energyChartInstance.resize(); // Ensures canvas scales properly out of hidden state
                }
              }, 80);
            }
          }


        function switchTab2(tabName) {
            document.getElementById('table-tab').classList.add('hidden');
            document.getElementById('chart-tab').classList.add('hidden');

            document.getElementById('table-btn').classList.remove('border-blue-500', 'text-white');
            document.getElementById('chart-btn').classList.remove('border-blue-500', 'text-white');
            document.getElementById('table-btn').classList.add('text-slate-400');
            document.getElementById('chart-btn').classList.add('text-slate-400');

            document.getElementById(tabName + '-btn').classList.remove('text-slate-400');
            document.getElementById(tabName + '-btn').classList.add('border-blue-500', 'text-white');

            document.getElementById(tabName + '-tab').classList.remove('hidden');

            if (tabName === 'chart') {
                setTimeout(initChart, 80);
            }
        }

document.addEventListener('DOMContentLoaded', function() {
    const tableData = document.querySelectorAll('[data-period]');
    window.chartData = Array.from(tableData).map(row => {
        let rawStart = row.getAttribute('data-start') || '';
        
        // 🛠️ REPLACEMENT STRIPPER LOGIC:
        // If it looks like <libsolar.MetereadingObject at 0x7f...>, we extract clean data
        if (rawStart.includes('MetereadingObject')) {
            // Option A: If your object string contains a readable date text somewhere inside it, extract it here.
            // Option B: If it's a completely blind memory address object representation, fall back safely.
            rawStart = row.getAttribute('data-date') || new Date().toISOString().split('T')[0]; 
        }

        return {
            start: rawStart,
            import_diff: row.getAttribute('data-import'),
            export_diff: row.getAttribute('data-export'),
            solar_yield: row.getAttribute('data-solar'),
            consumption: row.getAttribute('data-consumption'),
            weekly_import: row.getAttribute('data-weekly-import'),
            weekly_export: row.getAttribute('data-weekly-export'),
            weekly_solar: row.getAttribute('data-weekly-solar'),
            weekly_consumption: row.getAttribute('data-weekly-consumption')
        };
    });

    if (!window.chartData.length) {
        const chartEmpty = document.getElementById('chart-empty');
        const chartWrap = document.getElementById('chart-wrap');
        if (chartEmpty) chartEmpty.classList.remove('hidden');
        if (chartWrap) chartWrap.classList.add('hidden');
    } else {
        initChart();
    }
});

///boot
        
 </script>
</head>
<body class="min-h-screen bg-slate-950 text-slate-100 antialiased">
    <div class="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <header class="mb-8 rounded-2xl border border-slate-700 bg-slate-900/80 p-5 shadow-xl shadow-slate-950/30 backdrop-blur-sm">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <p class="text-xs font-medium uppercase tracking-[0.18em] text-blue-400">Energy dashboard</p>
                    <h1 class="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">☀️ Solar & Grid Meter Tracker</h1>
                </div>
                <div class="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
                    Live overview
                </div>
            </div>
        </header>

        <main class="space-y-8">
            <section class="overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-xl shadow-slate-950/30">
                <div class="border-b border-slate-700 bg-slate-800/80 px-5 py-4 sm:px-6">
                    <h2 class="text-lg font-semibold text-white">Add new reading</h2>
                    <p class="mt-1 text-sm text-slate-400">Track cumulative energy consumption and generation</p>
                </div>

                <div class="p-5 sm:p-6">
                    <form hx-post="/readings" hx-target="#feedback" hx-swap="innerHTML" class="space-y-5">
                        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                            <div class="flex flex-col gap-2">
                                <label for="date" class="text-sm font-medium text-slate-300">Reading Date</label>
                                <input
                                    type="date"
                                    id="date"
                                    name="date"
                                    value="{{today}}"
                                    required
                                    class="rounded-xl border border-slate-600 bg-slate-950/80 px-3 py-2.5 text-sm text-white shadow-inner shadow-slate-950/40 transition placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/20"
                                />
                            </div>

                            <div class="flex flex-col gap-2">
                                <label for="import_units" class="text-sm font-medium text-slate-300">Cumulative Import (kWh)</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    id="import_units"
                                    name="import_units"
                                    placeholder="0.00"
                                    required
                                    class="rounded-xl border border-slate-600 bg-slate-950/80 px-3 py-2.5 text-sm text-white shadow-inner shadow-slate-950/40 transition placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/20"
                                />
                            </div>

                            <div class="flex flex-col gap-2">
                                <label for="export_units" class="text-sm font-medium text-slate-300">Cumulative Export (kWh)</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    id="export_units"
                                    name="export_units"
                                    placeholder="0.00"
                                    required
                                    class="rounded-xl border border-slate-600 bg-slate-950/80 px-3 py-2.5 text-sm text-white shadow-inner shadow-slate-950/40 transition placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/20"
                                />
                            </div>

                            <div class="flex flex-col gap-2">
                                <label for="solar_units" class="text-sm font-medium text-slate-300">Cumulative Solar (kWh)</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    id="solar_units"
                                    name="solar_units"
                                    placeholder="0.00"
                                    required
                                    class="rounded-xl border border-slate-600 bg-slate-950/80 px-3 py-2.5 text-sm text-white shadow-inner shadow-slate-950/40 transition placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/20"
                                />
                            </div>
                        </div>

                        <div class="flex justify-start">
                            <button
                                type="submit"
                                class="rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-900/30 transition hover:from-blue-400 hover:to-blue-500 active:scale-95"
                            >
                                Save Reading
                            </button>
                        </div>
                    </form>
                </div>
            </section>

            <div id="feedback" class="min-h-[1rem]"></div>

            <section class="overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-xl shadow-slate-950/30">
                <div class="border-b border-slate-700 bg-slate-800/50 px-5 py-4 sm:px-6">
                    <div class="flex gap-4">
                        <button
                            id="table-btn"
                            onclick="switchTab('table')"
                            class="border-b-2 border-blue-500 px-4 py-2 text-sm font-medium text-white transition hover:text-slate-300"
                        >
                            📊 Data Table
                        </button>
                        <button
                            id="chart-btn"
                            onclick="switchTab('chart')"
                            class="border-b-2 border-transparent px-4 py-2 text-sm font-medium text-slate-400 transition hover:text-slate-300"
                        >
                            📈 Chart
                        </button>
                    </div>
                </div>

                <div id="table-tab" class="p-5 sm:p-6">
                    <h2 class="mb-4 text-lg font-semibold text-white">Period Breakdown</h2>
                    <p class="mb-4 text-sm text-slate-400">Review your recent energy history</p>
                    <div id="history-table">
                        % include('table_partial.tpl', periods=periods)
                    </div>
                </div>

                <div id="chart-tab" class="hidden p-5 sm:p-6">
                    <div id="chart-wrap" class="rounded-xl border border-slate-700 bg-slate-800/50 p-4 sm:p-6">
                        <canvas id="energyChart" height="220"></canvas>
                    </div>
                    <!-- ADD THIS DEBUG BOX -->
    <div id="debug-box" class="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs font-mono text-amber-200">
        <strong>Debug Info:</strong> <span id="debug-text">Loading data...</span>
    </div>
    <!-- ------------------ -->
                    <div id="chart-empty" class="hidden rounded-xl border border-dashed border-slate-600 bg-slate-800/40 p-8 text-center">
                        <p class="text-base font-medium text-slate-200">No energy data available yet.</p>
                        <p class="mt-2 text-sm text-slate-400">Add a reading to generate your chart.</p>
                    </div>
                </div>
% for p in periods_with_weekly:

<div data-period="true" 
     data-start="{{ p['start'].date}}" 
     data-import="{{p['import_diff']}}"
     data-export="{{p['export_diff']}}"
     data-solar="{{p['solar_yield']}}"
     data-consumption="{{p['consumption']}}"
     data-weekly-import="{{p['weekly_import']}}"
     data-weekly-export="{{p['weekly_export']}}"
     data-weekly-solar="{{p['weekly_solar']}}"
     data-weekly-consumption="{{p['weekly_consumption']}}"
     class="hidden"></div>
% end
                
            </section>
        </main>
    </div>
</body>
</html>
