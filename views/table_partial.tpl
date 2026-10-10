% if not periods:
    <div class="px-5 py-8 text-center sm:px-6">
        <p class="text-sm text-slate-400 italic">No completed periods available in database.</p>
    </div>
% else:
    <div class="p-3 sm:p-5">
        <div class="hidden md:block">
            <div class="overflow-hidden rounded-xl border border-slate-700 bg-slate-900/90">
                <table class="w-full border-collapse text-sm">
                    <thead>
                        <tr class="border-b border-slate-700 bg-slate-800/80">
                            <th class="px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Period</th>
                            <th class="px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Duration</th>
                            <th class="px-3 py-3 text-right text-xs font-medium uppercase tracking-wide text-slate-400">Import</th>
                            <th class="px-3 py-3 text-right text-xs font-medium uppercase tracking-wide text-slate-400">Export</th>
                            <th class="px-3 py-3 text-right text-xs font-medium uppercase tracking-wide text-slate-400">Solar</th>
                            <th class="px-3 py-3 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Grid Balance</th>
                            <th class="px-3 py-3 text-right text-xs font-medium uppercase tracking-wide text-slate-400">Consumption</th>
                        </tr>
                    </thead>
                    <tbody>
                        % for p in periods:
                        <tr class="border-b border-slate-700/60 transition-colors hover:bg-slate-800/60">
                            <td class="whitespace-nowrap px-3 py-3 text-slate-100">{{p.start.date.strftime('%d/%m/%Y')}} - {{p.end.date.strftime('%d/%m/%Y')}}</td>
                            <td class="whitespace-nowrap px-3 py-3 text-slate-400">{{p.days}} days</td>
                            <td class="whitespace-nowrap px-3 py-3 text-right font-medium text-amber-400">+{{f"{p.import_diff:.2f}"}} kWh</td>
                            <td class="whitespace-nowrap px-3 py-3 text-right font-medium text-emerald-400">+{{f"{p.export_diff:.2f}"}} kWh</td>
                            <td class="whitespace-nowrap px-3 py-3 text-right font-medium text-yellow-400">+{{f"{p.solar_yield:.2f}"}} kWh</td>
                            <td class="px-3 py-3">
                                % if p.net_balance >= 0:
                                    <span class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">
                                        <span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                                        +{{f"{p.net_balance:.2f}"}} kWh
                                    </span>
                                % else:
                                    <span class="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-300">
                                        <span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                                        {{f"{abs(p.net_balance):.2f}"}} kWh
                                    </span>
                                % end
                            </td>
                            <td class="whitespace-nowrap px-3 py-3 text-right text-slate-200">
                                {{f"{p.consumption:.2f}"}} kWh
                                <div class="mt-1 text-[11px] text-slate-500">{{f"{p.avg_daily_consumption:.2f}"}}/day</div>
                            </td>
                        </tr>
                        % end
                    </tbody>
                    <tfoot>
                        <tr class="border-t border-slate-600 bg-slate-800/90 text-slate-100">
                            <td class="px-3 py-3 font-semibold">Total</td>
                            <td class="px-3 py-3 font-semibold">{{ "%.2f" % totals['total_days']}} days</td>
                            <td class="px-3 py-3 text-right font-semibold text-amber-400">{{ "%.2f" % totals['total_import']}} kWh</td>
                            <td class="px-3 py-3 text-right font-semibold text-emerald-400">{{ "%.2f" % totals['total_export']}} kWh</td>
                            <td class="px-3 py-3 text-right font-semibold text-yellow-400">{{ "%.2f" % totals['total_solar']}} kWh</td>
                            <td class="px-3 py-3">
                                % if totals['total_balance'] >= 0:
                                    <span class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">
                                        <span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                                        +{{ "%.2f" % totals['total_balance']}} kWh
                                    </span>
                                % else:
                                    <span class="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-300">
                                        <span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                                        {{ "%.2f" % abs(totals['total_balance'])}} kWh
                                    </span>
                                % end
                            </td>
                            <td class="px-3 py-3 text-right font-semibold">{{ "%.2f" % totals['total_consumption']}} kWh</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

        <div class="space-y-3 md:hidden">
            % for p in periods:
            <div class="rounded-xl border border-slate-700 bg-slate-900/80 p-4 shadow-sm shadow-slate-950/10">
                <div class="mb-3 flex items-center justify-between border-b border-slate-700 pb-2">
                    <span class="text-sm font-semibold text-slate-100">{{p.start.date.strftime('%d/%m/%Y')}} - {{p.end.date.strftime('%d/%m/%Y')}}</span>
                    <span class="text-xs text-slate-500">{{p.days}}d</span>
                </div>

                <div class="space-y-2 text-sm">
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Import</span>
                        <span class="font-medium text-amber-400">+{{f"{p.import_diff:.2f}"}} kWh</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Export</span>
                        <span class="font-medium text-emerald-400">+{{f"{p.export_diff:.2f}"}} kWh</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Solar</span>
                        <span class="font-medium text-yellow-400">+{{f"{p.solar_yield:.2f}"}} kWh</span>
                    </div>
                    <div class="flex items-center justify-between border-t border-slate-700 pt-2">
                        <span class="text-slate-400">Grid Balance</span>
                        % if p.net_balance >= 0:
                            <span class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-1 text-[11px] font-medium text-emerald-300">
                                <span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                                +{{f"{p.net_balance:.2f}"}} kWh
                            </span>
                        % else:
                            <span class="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2 py-1 text-[11px] font-medium text-amber-300">
                                <span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                                {{f"{abs(p.net_balance):.2f}"}} kWh
                            </span>
                        % end
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Consumption</span>
                        <div class="text-right">
                            <div class="font-medium text-slate-200">{{f"{p.consumption:.2f}"}} kWh</div>
                            <div class="text-[11px] text-slate-500">{{f"{p.avg_daily_consumption:.2f}"}}/day</div>
                        </div>
                    </div>
                </div>
            </div>
            % end

            <div class="rounded-xl border-2 border-slate-600 bg-slate-800/90 p-4">
                <div class="mb-2 text-sm font-semibold text-slate-100">Total</div>
                <div class="space-y-2 text-sm">
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Duration</span>
                        <span class="font-medium text-slate-200">{{ "%.2f" % totals['total_days']}} days</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Import</span>
                        <span class="font-medium text-amber-400">{{ "%.2f" % totals['total_import']}} kWh</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Export</span>
                        <span class="font-medium text-emerald-400">{{ "%.2f" % totals['total_export']}} kWh</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Solar</span>
                        <span class="font-medium text-yellow-400">{{ "%.2f" % totals['total_solar']}} kWh</span>
                    </div>
                    <div class="flex items-center justify-between border-t border-slate-700 pt-2">
                        <span class="text-slate-400">Grid Balance</span>
                        % if totals['total_balance'] >= 0:
                            <span class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-1 text-[11px] font-medium text-emerald-300">
                                <span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                                +{{ "%.2f" % totals['total_balance']}} kWh
                            </span>
                        % else:
                            <span class="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2 py-1 text-[11px] font-medium text-amber-300">
                                <span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                                {{ "%.2f" % abs(totals['total_balance'])}} kWh
                            </span>
                        % end
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Consumption</span>
                        <span class="font-medium text-slate-200">{{ "%.2f" % totals['total_consumption']}} kWh</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
% end
