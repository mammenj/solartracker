<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solar & Grid Tracker</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.tailwindcss.com"></script>
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

            <section class="overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-xl shadow-slate-950/30">
                <div class="border-b border-slate-700 bg-slate-800/80 px-5 py-4 sm:px-6">
                    <h2 class="text-lg font-semibold text-white">Period breakdown</h2>
                    <p class="mt-1 text-sm text-slate-400">Review your recent energy history</p>
                </div>

                <div id="history-table" class="overflow-x-auto">
                    % include('table_partial.tpl', periods=periods)
                </div>
            </section>
        </main>
    </div>
</body>
</html>
