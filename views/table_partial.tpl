% if not periods:
    <div class="px-5 py-8 text-center sm:px-6">
        <p class="text-sm text-slate-400 italic">No completed periods available in database.</p>
    </div>
% else:
    <div class="overflow-x-auto">
        <table class="w-full text-sm">
            <thead>
                <tr class="border-b border-slate-700 bg-slate-800/50">
                    <th class="px-4 py-3 text-left font-semibold text-slate-300">Period</th>
                    <th class="px-4 py-3 text-left font-semibold text-slate-300">Duration</th>
                    <th class="px-4 py-3 text-right font-semibold text-slate-300">Import</th>
                    <th class="px-4 py-3 text-right font-semibold text-slate-300">Export</th>
                    <th class="px-4 py-3 text-right font-semibold text-slate-300">Solar Gen</th>
                    <th class="px-4 py-3 text-left font-semibold text-slate-300">Balance</th>
                    <th class="px-4 py-3 text-right font-semibold text-slate-300">Consumption</th>
                </tr>
            </thead>
            <tbody>
                % for p in periods:
                <tr class="border-b border-slate-700/50 transition hover:bg-slate-800/30">
                    <td class="whitespace-nowrap px-4 py-3 text-slate-100">{{p.start.date.strftime('%d/%m/%Y')}}-{{p.end.date.strftime('%d/%m/%Y')}}</td>
                    <td class="whitespace-nowrap px-4 py-3 text-slate-400">{{p.days}} days</td>
                    <td class="whitespace-nowrap px-4 py-3 text-right text-amber-400">+{{f"{p.import_diff:.2f}"}} kWh</td>
                    <td class="whitespace-nowrap px-4 py-3 text-right text-emerald-400">+{{f"{p.export_diff:.2f}"}} kWh</td>
                    <td class="whitespace-nowrap px-4 py-3 text-right text-yellow-400">+{{f"{p.solar_yield:.2f}"}} kWh</td>
                    <td class="px-4 py-3">
                        % if p.net_balance >= 0:
                            <span class="inline-flex items-center gap-1 rounded-lg bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-300">
                                <span class="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                                +{{f"{p.net_balance:.2f}"}} kWh Net Export
                            </span>
                        % else:
                            <span class="inline-flex items-center gap-1 rounded-lg bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-300">
                                <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                                {{f"{abs(p.net_balance):.2f}"}} kWh Net Import
                            </span>
                        % end
                    </td>
                    <td class="whitespace-nowrap px-4 py-3 text-right text-slate-300">{{f"{p.consumption:.2f}"}} kWh<br/><span class="text-xs text-slate-500">{{f"{p.avg_daily_consumption:.2f}"}}/day</span></td>
                </tr>
                % end
            </tbody>
            <tfoot>
                <tr class="border-t-2 border-slate-600 bg-slate-800/80 font-semibold text-slate-100">
                    <td class="px-4 py-3">Total</td>
                    <td class="px-4 py-3">{{ "%.2f" % totals['total_days']}} days</td>
                    <td class="px-4 py-3 text-right text-amber-400">{{ "%.2f" % totals['total_import']}} kWh</td>
                    <td class="px-4 py-3 text-right text-emerald-400">{{ "%.2f" % totals['total_export']}} kWh</td>
                    <td class="px-4 py-3 text-right text-yellow-400">{{ "%.2f" % totals['total_solar']}} kWh</td>
                    <td class="px-4 py-3">
                        % if totals['total_balance'] >= 0:
                            <span class="inline-flex items-center gap-1 rounded-lg bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-300">
                                <span class="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                                +{{ "%.2f" % totals['total_balance']}} kWh
                            </span>
                        % else:
                            <span class="inline-flex items-center gap-1 rounded-lg bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-300">
                                <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                                {{ "%.2f" % abs(totals['total_balance'])}} kWh
                            </span>
                        % end
                    </td>
                    <td class="px-4 py-3 text-right">{{ "%.2f" % totals['total_consumption']}} kWh</td>
                </tr>
            </tfoot>
        </table>
    </div>
% end
