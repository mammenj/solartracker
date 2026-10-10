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

        function initChart() {
            const ctx = document.getElementById('energyChart');
            if (!ctx) return;

            // Parse data from the page
            const periods = window.chartData || [];
            
            if (periods.length === 0) return;

            const labels = periods.map(p => `${p.start.split('T')[0]}`);
            const importData = periods.map(p => parseFloat(p.import_diff));
            const exportData = periods.map(p => parseFloat(p.export_diff));
            const solarData = periods.map(p => parseFloat(p.solar_yield));
            const consumptionData = periods.map(p => parseFloat(p.consumption));

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Import (kWh)',
                            data: importData,
                            backgroundColor: 'rgba(251, 191, 36, 0.8)',
                            borderColor: 'rgba(251, 191, 36, 1)',
                            borderWidth: 1,
                            borderRadius: 4
                        },
                        {
                            label: 'Export (kWh)',
                            data: exportData,
                            backgroundColor: 'rgba(16, 185, 129, 0.8)',
                            borderColor: 'rgba(16, 185, 129, 1)',
                            borderWidth: 1,
                            borderRadius: 4
                        },
                        {
                            label: 'Solar Generation (kWh)',
                            data: solarData,
                            backgroundColor: 'rgba(251, 146, 60, 0.8)',
                            borderColor: 'rgba(251, 146, 60, 1)',
                            borderWidth: 1,
                            borderRadius: 4
                        },
                        {
                            label: 'Consumption (kWh)',
                            data: consumptionData,
                            backgroundColor: 'rgba(59, 130, 246, 0.8)',
                            borderColor: 'rgba(59, 130, 246, 1)',
                            borderWidth: 1,
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                color: '#cbd5e1',
                                font: { size: 12, weight: '500' },
                                padding: 15,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.8)',
                            titleColor: '#e2e8f0',
                            bodyColor: '#cbd5e1',
                            borderColor: '#475569',
                            borderWidth: 1,
                            padding: 12,
                            cornerRadius: 8
                        }
                    },
                    scales: {
                        x: {
                            stacked: false,
                            grid: {
                                color: 'rgba(71, 85, 105, 0.1)',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#94a3b8',
                                font: { size: 11 }
                            }
                        },
                        y: {
                            stacked: false,
                            grid: {
                                color: 'rgba(71, 85, 105, 0.1)',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#94a3b8',
                                font: { size: 11 }
                            }
                        }
                    }
                }
            });
        }

        function switchTab(tabName) {
            // Hide all tab contents
            document.getElementById('table-tab').classList.add('hidden');
            document.getElementById('chart-tab').classList.add('hidden');

            // Remove active state from all tabs
            document.getElementById('table-btn').classList.remove('border-blue-500', 'text-white');
            document.getElementById('chart-btn').classList.remove('border-blue-500', 'text-white');

            // Add active state to clicked tab
            document.getElementById(tabName + '-btn').classList.add('border-blue-500', 'text-white');

            // Show selected tab content
            document.getElementById(tabName + '-tab').classList.remove('hidden');

            // Initialize chart when tab is switched
            if (tabName === 'chart') {
                setTimeout(initChart, 100);
            }
        }

        document.addEventListener('DOMContentLoaded', function() {
            // Initialize chart data from the page
            const tableData = document.querySelectorAll('[data-period]');
            window.chartData = Array.from(tableData).map(row => ({
                start: row.getAttribute('data-start'),
                import_diff: row.getAttribute('data-import'),
                export_diff: row.getAttribute('data-export'),
                solar_yield: row.getAttribute('data-solar'),
                consumption: row.getAttribute('data-consumption')
            }));
        });
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
            <!-- Form Card -->
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
                                    class="rounded-xl border border-slate-600 bg-slate-950/80 px-3 py-2.5 text-sm text-white shadow-inner shadow-slate-950/40 transition placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
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
                                    class="rounded-xl border border-slate-600 bg-slate-950/80 px-3 py-2.5 text-sm text-white shadow-inner shadow-slate-950/40 transition placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
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
                                    class="rounded-xl border border-slate-600 bg-slate-950/80 px-3 py-2.5 text-sm text-white shadow-inner shadow-slate-950/40 transition placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
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
                                    class="rounded-xl border border-slate-600 bg-slate-950/80 px-3 py-2.5 text-sm text-white shadow-inner shadow-slate-950/40 transition placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                                />
                            </div>
                        </div>

                        <div class="flex justify-start">
                            <button
                                type="submit"
                                class="rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-900/30 transition hover:from-blue-400 hover:to-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:ring-offset-2 focus:ring-offset-slate-950"
                            >
                                Save Reading
                            </button>
                        </div>
                    </form>
                </div>
            </section>

            <div id="feedback" class="min-h-[1rem]"></div>

            <!-- Tabs Section -->
            <section class="overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-xl shadow-slate-950/30">
                <!-- Tab Buttons -->
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

                <!-- Table Tab Content -->
                <div id="table-tab" class="p-5 sm:p-6">
                    <h2 class="mb-4 text-lg font-semibold text-white">Period Breakdown</h2>
                    <p class="mb-4 text-sm text-slate-400">Review your recent energy history</p>
                    <div id="history-table">
                        % include('table_partial.tpl', periods=periods)
                    </div>
                </div>

                <!-- Chart Tab Content -->
                <div id="chart-tab" class="hidden p-5 sm:p-6">
                    <h2 class="mb-4 text-lg font-semibold text-white">Energy Analysis</h2>
                    <p class="mb-6 text-sm text-slate-400">Visual representation of your energy metrics</p>
                    <div class="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
                        <canvas id="energyChart" height="80"></canvas>
                    </div>
                </div>

                <!-- Hidden data attributes for chart -->
                % for p in periods:
                <div data-period="true" data-start="{{p.start}}" data-import="{{p.import_diff}}" data-export="{{p.export_diff}}" data-solar="{{p.solar_yield}}" data-consumption="{{p.consumption}}" class="hidden"></div>
                % end
            </section>
        </main>
    </div>
</body>
</html>
