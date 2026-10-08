from datetime import datetime
from pathlib import Path

import bottle
from bottle import Bottle, request, run, template
from libsolar import MeterReading, SolarTracker

# Web App Setup
app = Bottle()
# Resolve project root and views directory relative to main.py
BASE_DIR = Path(__file__).resolve().parent
VIEWS_DIR = BASE_DIR / "views"

# Force Bottle to look inside your project's views directory
if str(VIEWS_DIR) not in bottle.TEMPLATE_PATH:
    bottle.TEMPLATE_PATH.insert(0, str(VIEWS_DIR))


project_root = Path(__file__).resolve().parent
if not (project_root / "solar_readings.txt").exists():
    project_root = project_root.parent.parent  # handle src/ layout if applicable

data_file = project_root / "solar_readings.txt"
tracker = SolarTracker(data_file)


@app.get("/")
def index():
    today = datetime.now().strftime("%Y-%m-%d")
    periods = tracker.get_periods()
    totals = tracker.get_totals()
    return template("views/index.tpl", today=today, periods=periods, totals=totals)


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

    msg = (
        f"✓ Updated record for {curr_date.strftime('%d-%b-%Y')}."
        if is_update
        else f"✓ Recorded reading for {curr_date.strftime('%d-%b-%Y')}."
    )

    # Re-render the table partial using the template
    rendered_table = template("table_partial.tpl", periods=tracker.get_periods())

    return f"""
    <div class='alert-success'>{msg}</div>
    <script>
        document.getElementById('history-table').innerHTML = `{rendered_table}`;
    </script>
    """


def main():
    run(app, host="0.0.0.0", port=8080, debug=True, reloader=True)


if __name__ == "__main__":
    main()
