% if not periods:
    <p class="empty-text">No completed periods available in database.</p>
% else:
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Period</th>
                    <th>Duration</th>
                    <th>Import (+)</th>
                    <th>Export (+)</th>
                    <th>Solar Gen</th>
                    <th>Grid Balance</th>
                    <th>Consumption</th>
                </tr>
            </thead>
            <tbody>
                % for p in periods:
                <tr>
                    <td><strong>{{p.start.date.strftime('%d/%m/%Y')}} → {{p.end.date.strftime('%d/%m/%Y')}}</strong></td>
                    <td>{{p.days}} days</td>
                    <td>+{{f"{p.import_diff:.2f}"}} kWh</td>
                    <td>+{{f"{p.export_diff:.2f}"}} kWh</td>
                    <td>+{{f"{p.solar_yield:.2f}"}} kWh</td>
                    <td>
                        % if p.net_balance >= 0:
                            <span class="badge export">+{{f"{p.net_balance:.2f}"}} kWh Net Export</span>
                        % else:
                            <span class="badge import">{{f"{abs(p.net_balance):.2f}"}} kWh Net Import</span>
                        % end
                    </td>
                    <td>{{f"{p.consumption:.2f}"}} kWh ({{f"{p.avg_daily_consumption:.2f}"}}/day)</td>
                </tr>
                % end
            </tbody>
            <tfoot>
              <tr class="total-row">
                <th>Total</th>
                <th>{{ "%.2f" % totals['total_days']}}</th>
                <th>{{ "%.2f" % totals['total_import']}}</th>
                <th>{{ "%.2f" % totals['total_export']}}</th>
                <th>{{ "%.2f" % totals['total_solar']}}</th>
                <th>{{ "%.2f" % totals['total_balance']}}</th>
                <th>{{ "%.2f" % totals['total_consumption']}}</th>
              </tr>
            </tfoot>
        </table>
    </div>
% end

