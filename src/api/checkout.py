"""POST /tabs/{tab_id}/checkout -- atomic pay-and-close for a tab."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/tabs",
    tags=["checkout"],
    dependencies=[Depends(auth.get_api_key)],
)

TAX_RATE = Decimal("0.0775")  # SLO county sales tax
_CENTS = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENTS, rounding=ROUND_HALF_UP)


class CheckoutRequest(BaseModel):
    payment_method: str = Field(..., min_length=1)
    tip_amount: Decimal = Field(default=Decimal("0"), ge=0)


class CheckoutResponse(BaseModel):
    payment_id: int
    tab_id: int
    table_id: Optional[int] = None
    subtotal: Decimal
    tax: Decimal
    tip: Decimal
    total: Decimal
    payment_method: str
    paid_at: datetime
    tab_status: str
    table_status: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: int
    tab_id: int
    subtotal: Decimal
    tax: Decimal
    tip: Decimal
    total: Decimal
    payment_method: str
    paid_at: datetime


@router.post("/{tab_id}/checkout", response_model=CheckoutResponse)
def checkout_tab(tab_id: int, body: CheckoutRequest):
    with db.engine.begin() as conn:
        # Lock the tab row so a concurrent checkout / add-item / split serializes here.
        tab = (
            conn.execute(
                sqlalchemy.text(
                    "SELECT tab_id, table_id, status FROM tabs "
                    "WHERE tab_id = :tab_id FOR UPDATE"
                ),
                {"tab_id": tab_id},
            )
            .mappings()
            .first()
        )
        if tab is None:
            raise HTTPException(status_code=404, detail="Tab not found")
        if tab["status"] != "open":
            raise HTTPException(
                status_code=409,
                detail=f"Tab is not open (status: {tab['status']})",
            )

        # Recompute the bill from the line items, inside the locked transaction.
        item_rows = (
            conn.execute(
                sqlalchemy.text(
                    "SELECT quantity, unit_price FROM tab_items WHERE tab_id = :tab_id"
                ),
                {"tab_id": tab_id},
            )
            .mappings()
            .all()
        )
        subtotal = Decimal("0.00")
        for r in item_rows:
            subtotal += _money(Decimal(str(r["unit_price"])) * r["quantity"])
        subtotal = _money(subtotal)
        tax = _money(subtotal * TAX_RATE)
        tip = _money(body.tip_amount)
        total = _money(subtotal + tax + tip)

        payment = (
            conn.execute(
                sqlalchemy.text(
                    "INSERT INTO payments "
                    "(tab_id, subtotal, tax, tip, total, payment_method) "
                    "VALUES (:tab_id, :subtotal, :tax, :tip, :total, :pm) "
                    "RETURNING payment_id, paid_at"
                ),
                {
                    "tab_id": tab_id,
                    "subtotal": subtotal,
                    "tax": tax,
                    "tip": tip,
                    "total": total,
                    "pm": body.payment_method,
                },
            )
            .mappings()
            .one()
        )

        conn.execute(
            sqlalchemy.text(
                "UPDATE tabs SET status = 'paid', closed_at = now() "
                "WHERE tab_id = :tab_id"
            ),
            {"tab_id": tab_id},
        )

        table_status: Optional[str] = None
        if tab["table_id"] is not None:
            conn.execute(
                sqlalchemy.text(
                    "UPDATE tables SET status = 'dirty', current_party_size = NULL, "
                    "reserved_for = NULL WHERE table_id = :table_id"
                ),
                {"table_id": tab["table_id"]},
            )
            table_status = "dirty"

    return CheckoutResponse(
        payment_id=payment["payment_id"],
        tab_id=tab_id,
        table_id=tab["table_id"],
        subtotal=subtotal,
        tax=tax,
        tip=tip,
        total=total,
        payment_method=body.payment_method,
        paid_at=payment["paid_at"],
        tab_status="paid",
        table_status=table_status,
    )


@router.get("/{tab_id}/payment", response_model=PaymentResponse)
def get_payment(tab_id: int):
    with db.engine.connect() as conn:
        payment = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT payment_id, tab_id, subtotal, tax, tip, total,
                           payment_method, paid_at
                    FROM payments
                    WHERE tab_id = :tab_id
                    """
                ),
                {"tab_id": tab_id},
            )
            .mappings()
            .first()
        )

        if payment is None:
            tab_exists = conn.execute(
                sqlalchemy.text("SELECT 1 FROM tabs WHERE tab_id = :tab_id"),
                {"tab_id": tab_id},
            ).scalar_one_or_none()
            if tab_exists is None:
                raise HTTPException(status_code=404, detail="Tab not found")
            raise HTTPException(
                status_code=404,
                detail="Payment not found for this tab",
            )

    return PaymentResponse(**payment)
