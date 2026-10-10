from datetime import datetime
from pathlib import Path

import bottle
from bottle import Bottle, request, run, template
from libsolar import MeterReading, ReadingPeriod, TotalsDict, EnergyExtrapolator
from libsolar_sqlite import MeterReadingStore

from config import load_config

# Web App Setup
app = Bottle()
BASE_DIR = Path(__file__).resolve().parent
VIEWS_DIR = BASE_DIR / "views"

# Force Bottle to look inside your project's views directory
if str(VIEWS_DIR) not in bottle.TEMPLATE_PATH:
    bottle.TEMPLATE_PATH.insert(0, str(VIEWS_DIR))

# Load configuration
config = load_config()
store = MeterReadingStore(config.db_file)


def get_periods() -> list[ReadingPeriod]:
    """Get all reading periods from the database."""
    readings = store.load_all()
    return [
        ReadingPeriod(readings[i - 1], readings[i]) for i in range(1, len(readings))
    ]


def get_periods_with_weekly() -> list[dict]:
    """Get periods with weekly extrapolated values."""
    periods = get_periods()
    print(
        "number of periods",
    )
    return [
        {
            "period": p,
            "extrapolator": EnergyExtrapolator(p),
            "start": p.start,
            "weekly_import": EnergyExtrapolator(p).weekly_import,
            "weekly_export": EnergyExtrapolator(p).weekly_export,
            "weekly_solar": EnergyExtrapolator(p).weekly_solar_yield,
            "weekly_consumption": EnergyExtrapolator(p).weekly_consumption,
            "weekly_balance": EnergyExtrapolator(p).weekly_net_balance,
            "import_diff": p.import_diff,
            "export_diff": p.export_diff,
            "solar_yield": p.solar_yield,
            "consumption": p.consumption,
        }
        for p in periods
    ]


def get_totals() -> TotalsDict:
    """Calculate totals from all periods."""
    periods = get_periods()
    return {
        "total_days": sum(p.days for p in periods),
        "total_import": sum(p.import_diff for p in periods),
        "total_export": sum(p.export_diff for p in periods),
        "total_solar": sum(p.solar_yield for p in periods),
        "total_balance": sum(p.net_balance for p in periods),
        "total_consumption": sum(p.consumption for p in periods),
    }


def validate_reading(new_reading: MeterReading) -> tuple[bool, str]:
    """Validate a new reading against the last stored reading."""
    readings = store.load_all()
    if not readings:
        return True, ""

    last = readings[-1]
    is_present = any(r.date == new_reading.date for r in readings)
    print("date is is_presenti >>>>>>>>", is_present)
    if is_present:
        return True, "Updating"
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


@app.get("/")
def index():
    today = datetime.now().strftime("%Y-%m-%d")
    periods = get_periods()
    periods_with_weekly = get_periods_with_weekly()
    totals: TotalsDict = get_totals()
    return template(
        "views/index.tpl",
        today=today,
        periods=periods,
        periods_with_weekly=periods_with_weekly,
        totals=totals,
    )


@app.post("/readings")
def add_reading():
    try:
        date_str = request.forms.get("date")
        curr_date = datetime.strptime(date_str, "%Y-%m-%d")
        curr_import = float(request.forms.get("import_units"))
        curr_export = float(request.forms.get("export_units"))
        curr_solar = float(request.forms.get("solar_units"))
    except (ValueError, TypeError):
        return "<div class='alert-error'>❌ Invalid form input format. Please check numeric values.</div>"

    new_reading = MeterReading(curr_date, curr_import, curr_export, curr_solar)
    # removing validation

    is_valid, err_msg = validate_reading(new_reading)
    if not is_valid:
        return f"<div class='alert-error'>❌ {err_msg}</div>"

    is_update = store.save_or_update(new_reading)

    msg = (
        f"✓ Updated record for {curr_date.strftime('%d-%b-%Y')}."
        if is_update
        else f"✓ Recorded reading for {curr_date.strftime('%d-%b-%Y')}"
    )
    periods_with_weekly = get_periods_with_weekly()

    rendered_table = template(
        "table_partial.tpl",
        periods_with_weekly=periods_with_weekly,
        periods=get_periods(),
        totals=get_totals(),
    )

    return f"""
    <div class='alert-success'>{msg}</div>
    <script>
        document.getElementById('history-table').innerHTML = `{rendered_table}`;
    </script>
    """


def main():
    run(app, host=config.host, port=config.port, server=config.server)


if __name__ == "__main__":
    main()
