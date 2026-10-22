"""HTTP-level tests for the dashboard and data-entry areas."""

from auth.db import ensure_user_db


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
async def test_user_can_open_dashboard(client, login, user):
    await login(user)
    resp = await client.get("/")
    assert resp.status == 200
    assert "Total Days" in resp.text


async def test_dashboard_alias_route(client, login, user):
    await login(user)
    assert (await client.get("/app/dashboard")).status == 200


async def test_dashboard_partial_for_htmx(client, login, user):
    await login(user)
    resp = await client.get("/app/dashboard/partial", headers={"HX-Request": "true"})
    assert resp.status == 200
    assert "<html" not in resp.text


async def test_periods_table_empty_state(client, login, user):
    await login(user)
    resp = await client.get("/app/dashboard/periods-table")
    assert resp.status == 200
    assert "No records found" in resp.text


async def test_periods_table_lists_a_period_after_two_readings(client, login, user, test_config):
    await login(user)
    await _add_reading(client, "2026-01-01", 0, 0, 0)
    await _add_reading(client, "2026-01-08", 70, 35, 140)

    resp = await client.get("/app/dashboard/periods-table")
    assert resp.status == 200
    assert "01.Jan" in resp.text
    assert "7d" in resp.text


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
async def test_user_can_open_entry_page(client, login, user):
    await login(user)
    resp = await client.get("/app/entry")
    assert resp.status == 200
    assert "Log New Reading" in resp.text


async def test_entry_partial_for_htmx(client, login, user):
    await login(user)
    resp = await client.get("/app/entry/partial", headers={"HX-Request": "true"})
    assert resp.status == 200
    assert "Log New Reading" in resp.text
    assert "<html" not in resp.text


async def test_readings_table_empty_state(client, login, user):
    await login(user)
    resp = await client.get("/app/entry/readings-table")
    assert resp.status == 200
    assert "No readings logged yet." in resp.text


# ---------------------------------------------------------------------------
# Adding readings
# ---------------------------------------------------------------------------
async def test_add_reading_records_and_renders_success(client, login, user):
    await login(user)
    resp = await _add_reading(client, "2026-01-01", 10, 20, 30)
    assert resp.status == 200
    assert "Recorded reading for 01-Jan-2026" in resp.text


async def test_added_reading_appears_in_table(client, login, user):
    await login(user)
    await _add_reading(client, "2026-01-01", 10, 20, 30)

    resp = await client.get("/app/entry/readings-table")
    assert "01/01/2026" in resp.text
    assert "10.00" in resp.text  # import
    assert "20.00" in resp.text  # export
    assert "30.00" in resp.text  # solar


async def test_adding_same_date_updates_existing_reading(client, login, user):
    await login(user)
    await _add_reading(client, "2026-01-01", 10, 20, 30)
    resp = await _add_reading(client, "2026-01-01", 11, 21, 31)

    assert "Updated record for 01-Jan-2026" in resp.text
    assert (await client.get("/app/entry/readings-table")).text.count("01/01/2026") == 1


async def test_reading_below_previous_import_is_rejected(client, login, user):
    await login(user)
    await _add_reading(client, "2026-01-01", 100, 200, 300)
    resp = await _add_reading(client, "2026-01-02", 50, 200, 300)
    assert "Import reading" in resp.text
    assert "cannot be lower than prior reading" in resp.text


async def test_reading_below_previous_export_is_rejected(client, login, user):
    await login(user)
    await _add_reading(client, "2026-01-01", 100, 200, 300)
    resp = await _add_reading(client, "2026-01-02", 100, 150, 300)
    assert "Export reading" in resp.text
    assert "cannot be lower than prior reading" in resp.text


async def test_reading_below_previous_solar_is_rejected(client, login, user):
    await login(user)
    await _add_reading(client, "2026-01-01", 100, 200, 300)
    resp = await _add_reading(client, "2026-01-02", 100, 200, 250)
    assert "Solar reading" in resp.text
    assert "cannot be lower than prior reading" in resp.text


async def test_invalid_reading_input_is_rejected(client, login, user):
    await login(user)
    resp = await client.post(
        "/readings",
        {"date": "not-a-date", "import_units": "x", "export_units": "y", "solar_units": "z"},
    )
    assert resp.status == 200
    assert "Invalid form input format" in resp.text


# ---------------------------------------------------------------------------
# Per-user isolation
# ---------------------------------------------------------------------------
async def test_readings_are_kept_per_user(client, login, user, make_user, new_client):
    await login(user)
    await _add_reading(client, "2026-01-01", 10, 20, 30)

    await make_user("user2", "password123", "User Two", "user", "user2.db")
    other = new_client()
    await other.post("/login", {"username": "user2", "password": "password123"})

    # user1 sees their reading ...
    assert "01/01/2026" in (await client.get("/app/entry/readings-table")).text
    # ... user2 does not (separate database file).
    assert "01/01/2026" not in (await other.get("/app/entry/readings-table")).text


async def test_each_user_gets_their_own_database_file(user, test_config):
    path = await ensure_user_db("user1.db")
    assert path == test_config.data_dir / "user1.db"
    assert path.exists()


async def _add_reading(client, date, import_units, export_units, solar_units):
    return await client.post(
        "/readings",
        {
            "date": date,
            "import_units": str(import_units),
            "export_units": str(export_units),
            "solar_units": str(solar_units),
        },
    )


async def test_dashboard_page_lazy_loads_chart_partial(client, login, user):
    await login(user)
    resp = await client.get("/app/dashboard")
    assert resp.status == 200
    # Chart is fetched on demand, not rendered inline.
    assert 'id="dashboard-chart"' in resp.text
    assert 'hx-get="/app/dashboard/chart"' in resp.text
    assert "Energy Charts" not in resp.text


async def test_dashboard_chart_partial_includes_phase1_fields(client, login, user):
    await login(user)
    await _add_reading(client, "2026-01-01", 0, 0, 0)
    await _add_reading(client, "2026-01-08", 70, 35, 140)

    resp = await client.get("/app/dashboard/chart")
    assert resp.status == 200
    assert "energyChartComponent" in resp.text
    for field in (
        "net_balance",
        "consumption",
        "solar_per_day",
        "self_consumed",
        "grid_dependency_pct",
    ):
        assert field in resp.text, field