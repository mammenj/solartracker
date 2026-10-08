from datetime import datetime
from pathlib import Path
from typing import Optional
from bottle import Bottle, request, response, run


class MeterReading:
    """Represents a single mandatory cumulative meter reading snapshot."""

    def __init__(
        self,
        date: datetime,
        import_units: float,
        export_units: float,
        solar_units: float,
    ):
        self.date = date
        self.import_units = import_units
        self.export_units = export_units
        self.solar_units = solar_units

    @classmethod
    def from_file_line(cls, line: str) -> Optional["MeterReading"]:
        parts = line.strip().split("|")
        if len(parts) < 4:
            return None
        try:
            date = datetime.strptime(parts[0], "%Y-%m-%d")
            imp = float(parts[1])
            exp = float(parts[2])
            solar = float(parts[3])
            return cls(date, imp, exp, solar)
        except ValueError:
            return None

    def to_file_line(self) -> str:
        return f"{self.date.strftime('%Y-%m-%d')}|{self.import_units:.2f}|{self.export_units:.2f}|{self.solar_units:.2f}\n"


class ReadingPeriod:
    """Calculates deltas and metrics between two consecutive snapshots."""

    def __init__(self, start_reading: MeterReading, end_reading: MeterReading):
        self.start = start_reading
        self.end = end_reading

    @property
    def days(self) -> int:
        return (self.end.date - self.start.date).days

    @property
    def import_diff(self) -> float:
        return self.end.import_units - self.start.import_units

    @property
    def export_diff(self) -> float:
        return self.end.export_units - self.start.export_units

    @property
    def net_balance(self) -> float:
        return self.export_diff - self.import_diff

    @property
    def solar_yield(self) -> float:
        return self.end.solar_units - self.start.solar_units

    @property
    def consumption(self) -> float:
        return (self.solar_yield + self.import_diff) - self.export_diff

    @property
    def avg_daily_consumption(self) -> float:
        return self.consumption / self.days if self.days > 0 else self.consumption


class SolarTracker:
    """Manages reading history state, validation, and calculations."""

    def __init__(self, data_filepath: Path):
        self.filepath = data_filepath
        self.history: list[MeterReading] = []
        self._load_from_file()

    def _load_from_file(self) -> None:
        self.history.clear()
        if not self.filepath.exists():
            return
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                reading = MeterReading.from_file_line(line)
                if reading:
                    self.history.append(reading)
        self.history.sort(key=lambda r: r.date)

    def _save_all_to_file(self) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            for reading in self.history:
                f.write(reading.to_file_line())

    def validate_reading(self, new_reading: MeterReading) -> tuple[bool, str]:
        prior_readings = [r for r in self.history if r.date < new_reading.date]
        if not prior_readings:
            return True, ""

        last = prior_readings[-1]
        if new_reading.import_units < last.import_units:
            return (
                False,
                f"Import reading ({new_reading.import_units:.2f} kWh) cannot be lower than prior reading ({last.import_units:.2f} kWh on {last.date.strftime('%Y-%m-%d')}).",
            )
        if new_reading.export_units < last.export_units:
            return (
                False,
                f"Export reading ({new_reading.export_units:.2f} kWh) cannot be lower than prior reading ({last.export_units:.2f} kWh on {last.date.strftime('%Y-%m-%d')}).",
            )
        if new_reading.solar_units < last.solar_units:
            return (
                False,
                f"Solar reading ({new_reading.solar_units:.2f} kWh) cannot be lower than prior reading ({last.solar_units:.2f} kWh on {last.date.strftime('%Y-%m-%d')}).",
            )

        return True, ""

    def save_or_update_reading(
        self, reading: MeterReading
    ) -> tuple[bool, Optional[ReadingPeriod]]:
        existing_index = next(
            (
                i
                for i, r in enumerate(self.history)
                if r.date.date() == reading.date.date()
            ),
            None,
        )
        is_update = existing_index is not None

        if is_update:
            self.history[existing_index] = reading
        else:
            self.history.append(reading)

        self.history.sort(key=lambda r: r.date)
        self._save_all_to_file()

        idx = self.history.index(reading)
        period = ReadingPeriod(self.history[idx - 1], reading) if idx > 0 else None
        return is_update, period

    def get_periods(self) -> list[ReadingPeriod]:
        return [
            ReadingPeriod(self.history[i - 1], self.history[i])
            for i in range(1, len(self.history))
        ]


# Web App Setup
app = Bottle()
project_root = Path(__file__).resolve().parent.parent.parent
data_file = project_root / "solar_readings.txt"
tracker = SolarTracker(data_file)


def render_table_component() -> str:
    periods = tracker.get_periods()
    if not periods:
        return "<p class='empty-text'>No completed periods available in database.</p>"

    rows = ""
    for p in periods:
        p_str = (
            f"{p.start.date.strftime('%d/%m/%Y')} → {p.end.date.strftime('%d/%m/%Y')}"
        )
        if p.net_balance >= 0:
            net_badge = (
                f"<span class='badge export'>+{p.net_balance:.2f} kWh Net Export</span>"
            )
        else:
            net_badge = f"<span class='badge import'>{abs(p.net_balance):.2f} kWh Net Import</span>"

        rows += f"""
        <tr>
            <td><strong>{p_str}</strong></td>
            <td>{p.days} days</td>
            <td>+{p.import_diff:.2f} kWh</td>
            <td>+{p.export_diff:.2f} kWh</td>
            <td>+{p.solar_yield:.2f} kWh</td>
            <td>{net_badge}</td>
            <td>{p.consumption:.2f} kWh ({p.avg_daily_consumption:.2f}/day)</td>
        </tr>
        """

    return f"""
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
            {rows}
        </tbody>
    </table>
    """


@app.get("/")
def index():
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Solar & Grid Tracker</title>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <style>
            :root {{
                --bg: #121418;
                --card-bg: #1e222a;
                --border: #2e3440;
                --text: #e5e9f0;
                --text-muted: #8892b0;
                --accent: #d08770;
                --green: #a3be8c;
                --blue: #81a1c1;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 2rem 1rem;
            }}
            .container {{
                max-width: 960px;
                margin: 0 auto;
            }}
            h1 {{
                font-size: 1.5rem;
                letter-spacing: 0.5px;
                margin-bottom: 1.5rem;
                color: #fff;
            }}
            .card {{
                background: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 2rem;
            }}
            .form-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 1rem;
            }}
            .field-group {{
                display: flex;
                flex-direction: column;
                gap: 0.4rem;
            }}
            label {{
                font-size: 0.85rem;
                color: var(--text-muted);
            }}
            input {{
                background: var(--bg);
                border: 1px solid var(--border);
                color: #fff;
                padding: 0.6rem;
                border-radius: 4px;
                font-size: 0.95rem;
            }}
            input:focus {{
                outline: 1px solid var(--blue);
            }}
            button {{
                background: var(--blue);
                color: #121418;
                font-weight: 600;
                border: none;
                padding: 0.75rem 1.25rem;
                border-radius: 4px;
                cursor: pointer;
                margin-top: 1rem;
                font-size: 0.95rem;
            }}
            button:hover {{
                opacity: 0.9;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 0.5rem;
            }}
            th, td {{
                text-align: left;
                padding: 0.75rem 0.5rem;
                border-bottom: 1px solid var(--border);
                font-size: 0.9rem;
            }}
            th {{
                color: var(--text-muted);
                font-weight: 500;
            }}
            .badge {{
                display: inline-block;
                padding: 0.2rem 0.5rem;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: 600;
            }}
            .badge.export {{
                background: rgba(163, 190, 140, 0.2);
                color: var(--green);
            }}
            .badge.import {{
                background: rgba(208, 135, 112, 0.2);
                color: var(--accent);
            }}
            .alert-error {{
                background: rgba(191, 97, 106, 0.2);
                color: #bf616a;
                padding: 0.75rem;
                border-radius: 4px;
                margin-bottom: 1rem;
            }}
            .alert-success {{
                background: rgba(163, 190, 140, 0.2);
                color: var(--green);
                padding: 0.75rem;
                border-radius: 4px;
                margin-bottom: 1rem;
            }}
            .empty-text {{
                color: var(--text-muted);
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>☀️ Solar & Grid Meter Tracker</h1>

            <div class="card">
                <form hx-post="/readings" hx-target="#feedback" hx-swap="innerHTML">
                    <div class="form-grid">
                        <div class="field-group">
                            <label>Reading Date</label>
                            <input type="date" name="date" value="{today}" required />
                        </div>
                        <div class="field-group">
                            <label>Cumulative Import (kWh)</label>
                            <input type="number" step="0.01" name="import_units" placeholder="0.00" required />
                        </div>
                        <div class="field-group">
                            <label>Cumulative Export (kWh)</label>
                            <input type="number" step="0.01" name="export_units" placeholder="0.00" required />
                        </div>
                        <div class="field-group">
                            <label>Cumulative Solar (kWh)</label>
                            <input type="number" step="0.01" name="solar_units" placeholder="0.00" required />
                        </div>
                    </div>
                    <button type="submit">Save Reading</button>
                </form>
            </div>

            <div id="feedback"></div>

            <div class="card">
                <h2 style="font-size: 1.1rem; margin-top: 0;">Period Breakdown</h2>
                <div id="history-table">
                    {render_table_component()}
                </div>
            </div>
        </div>
    </body>
    </html>
    """


@app.post("/readings")
def add_reading():
    try:
        date_str = request.forms.get("date")
        curr_date = datetime.strptime(date_str, "%Y-%m-%d")
        curr_import = float(request.forms.get("import_units"))
        curr_export = float(request.forms.get("export_units"))
        curr_solar = float(request.forms.get("solar_units"))
    except ValueError, TypeError:
        return "<div class='alert-error'>❌ Invalid form input format. Please check numeric values.</div>"

    new_reading = MeterReading(curr_date, curr_import, curr_export, curr_solar)

    is_valid, err_msg = tracker.validate_reading(new_reading)
    if not is_valid:
        return f"<div class='alert-error'>❌ {err_msg}</div>"

    is_update, period = tracker.save_or_update_reading(new_reading)
    response.headers["HX-Trigger"] = "reloadHistory"

    msg = (
        f"✓ Updated record for {curr_date.strftime('%d-%b-%Y')}."
        if is_update
        else f"✓ Recorded reading for {curr_date.strftime('%d-%b-%Y')}."
    )

    return f"""
    <div class='alert-success'>
        {msg}
    </div>
    <script>
        document.getElementById('history-table').innerHTML = `{render_table_component()}`;
    </script>
    """


def main():
    run(app, host="127.0.0.1", port=8080, debug=True, reloader=True)


if __name__ == "__main__":
    main()
