% if not readings:
    <div class="px-5 py-8 text-center sm:px-6">
        <p class="text-sm text-slate-400 italic">No periods available in database.</p>
    </div>
% else:
    <div class="p-2 sm:p-5">
        <div class="w-full">
            <div class="w-full overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/90">
                <table class="w-full table-fixed border-collapse text-[11px] text-sm">
                    <thead>
                        <tr class="border-b border-slate-700 bg-slate-800/80">
                            <th class="px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Date</th>
                            <th class="px-3 py-3 text-right text-xs font-medium uppercase tracking-wide text-slate-400">Imported</th>
                            <th class="px-3 py-3 text-right text-xs font-medium uppercase tracking-wide text-slate-400">Exported</th>
                            <th class="px-3 py-3 text-right text-xs font-medium uppercase tracking-wide text-slate-400">Solar</th>
                        </tr>
                    </thead>
                    <tbody>
                        % for r in readings:
                        <tr class="border-b border-slate-700/60 transition-colors hover:bg-slate-800/60">
                            <td class="whitespace-nowrap px-3 py-3 text-slate-100">{{r.date.strftime('%d/%m/%Y')}}</td>
                            <td class="whitespace-nowrap px-3 py-3 text-right font-medium text-amber-400">+{{f"{r.import_units:.2f}"}} kWh</td>
                            <td class="whitespace-nowrap px-3 py-3 text-right font-medium text-emerald-400">+{{f"{r.export_units:.2f}"}} kWh</td>
                            <td class="whitespace-nowrap px-3 py-3 text-right font-medium text-yellow-400">+{{f"{r.solar_units:.2f}"}} kWh</td>
                        </tr>
                        % end
                    </tbody>
                </table>
            </div>
        </div>
    </div>
% end
