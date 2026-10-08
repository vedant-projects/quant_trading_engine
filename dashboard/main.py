"""Local read-only Streamlit monitoring dashboard."""

import os
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

from app.schemas.backtest import BacktestReport

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
REPORT_DIRECTORY = Path(os.getenv("REPORT_DIRECTORY", "reports"))


def api_get(
    path: str,
    parameters: dict[str, Any] | None = None,
) -> Any:
    """Read an API endpoint without displaying raw exception details."""
    try:
        response = httpx.get(
            f"{API_BASE}{path}",
            params=parameters,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        st.warning("API request unavailable. Check services and migrations.")
        return None


def show_api_table(
    path: str,
    parameters: dict[str, Any] | None = None,
) -> None:
    """Display a successful list response as a table."""
    rows = api_get(path, parameters)

    if isinstance(rows, list):
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
        )


def main() -> None:
    """Render the local monitoring interface."""
    st.set_page_config(
        page_title="Personal Quant Engine",
        layout="wide",
    )

    st.title("Personal Quant Trading Engine")
    st.caption(
        "Local historical simulation and read-only monitoring. "
        "Broker execution is disabled."
    )

    if st.button("Refresh"):
        st.rerun()

    overview, records, reports = st.tabs(
        ["Overview", "Persisted records", "Backtest reports"]
    )

    with overview:
        health = api_get("/health")
        readiness = api_get("/health/ready")

        if health is not None:
            st.json(health)

        if readiness is not None:
            st.json(readiness)

        account_id = st.text_input(
            "Account ID for latest persisted valuation",
            placeholder="simulation-<job UUID>",
        )

        if account_id:
            snapshot = api_get(
                "/api/v1/portfolio/latest",
                {"account_id": account_id},
            )

            if snapshot is not None:
                columns = st.columns(3)
                columns[0].metric("Equity", snapshot["equity"])
                columns[1].metric("Cash", snapshot["cash"])
                columns[2].metric(
                    "Gross exposure",
                    snapshot["gross_exposure"],
                )
                st.json(snapshot)

    with records:
        selection = st.selectbox(
            "Record type",
            ["strategies", "signals", "orders", "trades"],
        )
        show_api_table(
            f"/api/v1/{selection}",
            {"limit": 100},
        )

    with reports:
        files = sorted(
            REPORT_DIRECTORY.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        if not files:
            st.info("No report artifacts yet. Run a historical job.")
            return

        selected = st.selectbox(
            "Report",
            files,
            format_func=lambda path: path.stem,
        )

        try:
            report = BacktestReport.model_validate_json(
                selected.read_text(encoding="utf-8")
            )
        except (ValueError, OSError):
            st.error("The selected report could not be validated.")
            return

        st.write(
            f"Strategy: {report.strategy_id} | "
            f"Symbol: {report.symbol} | Currency: {report.currency}"
        )

        metrics = report.metrics
        columns = st.columns(3)

        columns[0].metric(
            "Total return",
            f"{metrics.total_return:.2%}",
        )
        columns[1].metric(
            "Maximum drawdown",
            f"{metrics.max_drawdown:.2%}",
        )
        columns[2].metric(
            "Sharpe",
            "Undefined" if metrics.sharpe is None else f"{metrics.sharpe:.3f}",
        )

        frame = pd.DataFrame(
            [
                {
                    "timestamp": point.timestamp,
                    "equity": point.equity,
                }
                for point in report.equity_curve
            ]
        )

        st.plotly_chart(
            px.line(frame, x="timestamp", y="equity"),
            use_container_width=True,
        )
        st.json(metrics.model_dump(mode="json"))

        for note in report.notes:
            st.caption(note)


if __name__ == "__main__":
    main()
