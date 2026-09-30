from datetime import date, timedelta

from app.services.catalog_service import ensure_seed_catalog, get_active_versions
from app.services.market_data_service import upsert_market_bar


def _seed_bars(db_session, ticker="MSFT", count=35):
    start = date(2026, 1, 1)
    for index in range(count):
        upsert_market_bar(
            db_session,
            ticker=ticker,
            price_date=start + timedelta(days=index),
            close_price=90.0 + index,
        )
    db_session.commit()


def test_dashboard_renders(app_client):
    response = app_client.get("/")

    assert response.status_code == 200
    assert "Laboratorio de estrategias" in response.text


def test_models_page_renders_seed_catalog(app_client):
    response = app_client.get("/models")

    assert response.status_code == 200
    assert "Catalogo de modelos" in response.text
    assert "Naive Drift" in response.text


def test_create_run_redirects(db_session, app_client):
    ensure_seed_catalog(db_session)
    version = get_active_versions(db_session)[0]
    _seed_bars(db_session)

    response = app_client.post(
        "/runs",
        data={
            "ticker": "msft",
            "mode": "backtest",
            "horizon_days": "1",
            "period": "1y",
            "version_ids": str(version.id),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/runs/")


def test_predictions_page_and_apis(db_session, app_client):
    ensure_seed_catalog(db_session)
    version = get_active_versions(db_session)[0]
    _seed_bars(db_session)
    app_client.post(
        "/runs",
        data={
            "ticker": "MSFT",
            "mode": "backtest",
            "horizon_days": "1",
            "period": "1y",
            "version_ids": str(version.id),
        },
    )

    assert app_client.get("/predictions").status_code == 200
    assert app_client.get("/api/metrics").status_code == 200
    assert app_client.get("/api/history/MSFT").json()
    assert app_client.get("/api/models").json()
    runs = app_client.get("/api/runs").json()
    assert runs
    assert app_client.get(f"/api/runs/{runs[0]['id']}/predictions").json()


def test_legacy_prediction_form_redirects(app_client):
    response = app_client.get("/predictions/new", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/runs/new"
