<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solar & Grid Tracker</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        :root {
            --bg: #121418;
            --card-bg: #1e222a;
            --border: #2e3440;
            --text: #e5e9f0;
            --text-muted: #8892b0;
            --accent: #d08770;
            --green: #a3be8c;
            --blue: #81a1c1;
        }

        * {
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 1rem;
        }

        .container {
            max-width: 1024px;
            margin: 0 auto;
        }

        h1 {
            font-size: 1.4rem;
            letter-spacing: 0.5px;
            margin-bottom: 1.25rem;
            color: #fff;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
        }

        /* Responsive Form Layout */
        .form-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1rem;
        }

        @media (min-width: 600px) {
            .form-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (min-width: 900px) {
            .form-grid {
                grid-template-columns: repeat(4, 1fr);
            }
        }

        .field-group {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        label {
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        input {
            background: var(--bg);
            border: 1px solid var(--border);
            color: #fff;
            padding: 0.65rem;
            border-radius: 4px;
            font-size: 0.95rem;
            width: 100%;
        }

        input:focus {
            outline: 1px solid var(--blue);
        }

        button {
            background: var(--blue);
            color: #121418;
            font-weight: 600;
            border: none;
            padding: 0.75rem 1.25rem;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 1.25rem;
            font-size: 0.95rem;
            width: 100%;
        }

        @media (min-width: 600px) {
            button {
                width: auto;
            }
        }

        button:hover {
            opacity: 0.9;
        }

        /* Responsive Table Container */
        .table-wrapper {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 0.5rem;
            min-width: 680px; /* Prevents squishing on small screens */
        }

        th, td {
            text-align: left;
            padding: 0.75rem 0.6rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.88rem;
            white-space: nowrap;
        }

        th {
            color: var(--text-muted);
            font-weight: 500;
        }

        .badge {
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .badge.export {
            background: rgba(163, 190, 140, 0.2);
            color: var(--green);
        }

        .badge.import {
            background: rgba(208, 135, 112, 0.2);
            color: var(--accent);
        }

        .alert-error {
            background: rgba(191, 97, 106, 0.2);
            color: #bf616a;
            padding: 0.75rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }

        .alert-success {
            background: rgba(163, 190, 140, 0.2);
            color: var(--green);
            padding: 0.75rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }

        .empty-text {
            color: var(--text-muted);
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>☀️ Solar & Grid Meter Tracker</h1>

        <div class="card">
            <form hx-post="/readings" hx-target="#feedback" hx-swap="innerHTML">
                <div class="form-grid">
                    <div class="field-group">
                        <label for="date">Reading Date</label>
                        <input type="date" id="date" name="date" value="{{today}}" required />
                    </div>
                    <div class="field-group">
                        <label for="import_units">Cumulative Import (kWh)</label>
                        <input type="number" step="0.01" id="import_units" name="import_units" placeholder="0.00" required />
                    </div>
                    <div class="field-group">
                        <label for="export_units">Cumulative Export (kWh)</label>
                        <input type="number" step="0.01" id="export_units" name="export_units" placeholder="0.00" required />
                    </div>
                    <div class="field-group">
                        <label for="solar_units">Cumulative Solar (kWh)</label>
                        <input type="number" step="0.01" id="solar_units" name="solar_units" placeholder="0.00" required />
                    </div>
                </div>
                <button type="submit">Save Reading</button>
            </form>
        </div>

        <div id="feedback"></div>

        <div class="card">
            <h2 style="font-size: 1.1rem; margin-top: 0;">Period Breakdown</h2>
            <div id="history-table">
                % include('table_partial.tpl', periods=periods)
            </div>
        </div>
    </div>
</body>
</html>

