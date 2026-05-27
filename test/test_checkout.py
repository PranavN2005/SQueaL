from decimal import Decimal

import pytest
import sqlalchemy
from fastapi import HTTPException

from src.database import engine
from src.api.checkout import checkout_tab, CheckoutRequest


def _create_open_tab(items):
    """Create an open tab on table 1 with the given (name, qty, price) items."""
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


def test_checkout_marks_paid_records_payment_and_frees_table():
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


def test_checkout_missing_tab_raises_404():
    with pytest.raises(HTTPException) as exc:
        checkout_tab(9_999_999, CheckoutRequest(payment_method="cash"))
    assert exc.value.status_code == 404


def test_checkout_already_paid_raises_409():
    tab_id = _create_open_tab([("Tea", 1, 2.00)])
    try:
        checkout_tab(tab_id, CheckoutRequest(payment_method="cash"))
        with pytest.raises(HTTPException) as exc:
            checkout_tab(tab_id, CheckoutRequest(payment_method="cash"))
        assert exc.value.status_code == 409
    finally:
        _cleanup(tab_id)


def test_checkout_rejects_negative_tip():
    with pytest.raises(Exception):
        CheckoutRequest(payment_method="cash", tip_amount=Decimal("-1.00"))
