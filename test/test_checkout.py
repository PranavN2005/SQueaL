from decimal import Decimal
import os

import pytest
import sqlalchemy
from fastapi import HTTPException
from dotenv import find_dotenv, load_dotenv
from sqlalchemy.engine import Engine

if not os.getenv("RENDER"):
    load_dotenv(dotenv_path="default.env", override=False)
load_dotenv(dotenv_path=find_dotenv(".env"), override=True)

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("PGCONNECT_TIMEOUT", "3")

DB_URL_CONFIGURED = bool(os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL"))
DB_SKIP_REASON = "Postgres URL not configured - skipping checkout DB tests"
DB_REACHABLE = False


def _db_reachable(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        return True
    except Exception:
        return False


if DB_URL_CONFIGURED:
    from src.database import engine as db_engine

    DB_REACHABLE = _db_reachable(db_engine)
    if not DB_REACHABLE:
        DB_SKIP_REASON = "Postgres not reachable - skipping checkout DB tests"


requires_db = pytest.mark.skipif(not DB_REACHABLE, reason=DB_SKIP_REASON)


def test_checkout_integration_environment_detected():
    assert DB_SKIP_REASON or DB_REACHABLE


def _create_open_tab(items):
    """Create an open tab on table 1 with the given (name, qty, price) items."""
    from src.database import engine

    with engine.begin() as conn:
        tab_id = conn.execute(
            sqlalchemy.text(
                "INSERT INTO tabs (table_id, total_price, status) "
                "VALUES (1, 0, 'open') RETURNING tab_id"
            )
        ).scalar_one()
        for name, qty, price in items:
            conn.execute(
                sqlalchemy.text(
                    "INSERT INTO tab_items (tab_id, item_name, quantity, unit_price) "
                    "VALUES (:t, :n, :q, :p)"
                ),
                {"t": tab_id, "n": name, "q": qty, "p": price},
            )
    return tab_id


def _cleanup(tab_id):
    from src.database import engine

    with engine.begin() as conn:
        conn.execute(
            sqlalchemy.text("DELETE FROM payments WHERE tab_id = :t"), {"t": tab_id}
        )
        conn.execute(
            sqlalchemy.text("DELETE FROM tab_items WHERE tab_id = :t"), {"t": tab_id}
        )
        conn.execute(
            sqlalchemy.text("DELETE FROM tabs WHERE tab_id = :t"), {"t": tab_id}
        )
        conn.execute(
            sqlalchemy.text(
                "UPDATE tables SET status = 'open', current_party_size = NULL, "
                "reserved_for = NULL WHERE table_id = 1"
            )
        )


@requires_db
def test_checkout_marks_paid_records_payment_and_frees_table():
    from src.api.checkout import CheckoutRequest, checkout_tab
    from src.database import engine

    tab_id = _create_open_tab([("Coke", 2, 3.50), ("Burger", 1, 12.00)])
    try:
        resp = checkout_tab(
            tab_id, CheckoutRequest(payment_method="card", tip_amount=Decimal("5.00"))
        )

        # subtotal 19.00, tax 1.47 (19.00*0.0775), tip 5.00, total 25.47
        assert resp.subtotal == Decimal("19.00")
        assert resp.tax == Decimal("1.47")
        assert resp.tip == Decimal("5.00")
        assert resp.total == Decimal("25.47")
        assert resp.tab_status == "paid"
        assert resp.table_status == "dirty"

        with engine.connect() as conn:
            assert (
                conn.execute(
                    sqlalchemy.text("SELECT status FROM tabs WHERE tab_id = :t"),
                    {"t": tab_id},
                ).scalar_one()
                == "paid"
            )
            pay = (
                conn.execute(
                    sqlalchemy.text(
                        "SELECT total, payment_method FROM payments WHERE tab_id = :t"
                    ),
                    {"t": tab_id},
                )
                .mappings()
                .first()
            )
            assert pay is not None
            assert pay["total"] == Decimal("25.47")
            assert pay["payment_method"] == "card"
            assert (
                conn.execute(
                    sqlalchemy.text("SELECT status FROM tables WHERE table_id = 1")
                ).scalar_one()
                == "dirty"
            )
    finally:
        _cleanup(tab_id)


@requires_db
def test_checkout_missing_tab_raises_404():
    from src.api.checkout import CheckoutRequest, checkout_tab

    with pytest.raises(HTTPException) as exc:
        checkout_tab(9_999_999, CheckoutRequest(payment_method="cash"))
    assert exc.value.status_code == 404


@requires_db
def test_checkout_already_paid_raises_409():
    from src.api.checkout import CheckoutRequest, checkout_tab

    tab_id = _create_open_tab([("Tea", 1, 2.00)])
    try:
        checkout_tab(tab_id, CheckoutRequest(payment_method="cash"))
        with pytest.raises(HTTPException) as exc:
            checkout_tab(tab_id, CheckoutRequest(payment_method="cash"))
        assert exc.value.status_code == 409
    finally:
        _cleanup(tab_id)


@requires_db
def test_checkout_rejects_negative_tip():
    from src.api.checkout import CheckoutRequest

    with pytest.raises(Exception):
        CheckoutRequest(payment_method="cash", tip_amount=Decimal("-1.00"))
