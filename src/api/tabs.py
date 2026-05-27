from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/tables",
    tags=["tabs"],
    dependencies=[Depends(auth.get_api_key)],
)

TAX_RATE = 0.0775  # SLO county sales tax


class TabItemIn(BaseModel):
    item_name: str
    quantity: int
    unit_price: float


class TabItemOut(BaseModel):
    item_name: str
    quantity: int
    unit_price: float
    line_total: float


class TabCreate(BaseModel):
    items: List[TabItemIn]


class TabUpdate(BaseModel):
    items_to_add: List[TabItemIn]


class TabSplitRequest(BaseModel):
    items_to_move: List[TabItemIn]


class TabResponse(BaseModel):
    tab_id: int
    table_id: int
    items: List[TabItemOut]
    subtotal: float


class TabWithTotalsResponse(TabResponse):
    tax: float
    total: float


class TabSplitResponse(BaseModel):
    original_tab: TabResponse
    new_tab: TabResponse


def _load_tab(conn, table_id: int, tab_id: int) -> Optional[dict]:
    tab_row = (
        conn.execute(
            sqlalchemy.text(
                """
                SELECT tab_id, table_id
                FROM tabs
                WHERE tab_id = :tab_id AND table_id = :table_id
                """
            ),
            {"tab_id": tab_id, "table_id": table_id},
        )
        .mappings()
        .first()
    )
    if not tab_row:
        return None

    item_rows = (
        conn.execute(
            sqlalchemy.text(
                """
                SELECT item_name, quantity, unit_price
                FROM tab_items
                WHERE tab_id = :tab_id
                ORDER BY tab_item_id
                """
            ),
            {"tab_id": tab_id},
        )
        .mappings()
        .all()
    )

    items: List[dict] = []
    subtotal = 0.0
    for r in item_rows:
        line_total = round(r["quantity"] * r["unit_price"], 2)
        items.append(
            {
                "item_name": r["item_name"],
                "quantity": r["quantity"],
                "unit_price": r["unit_price"],
                "line_total": line_total,
            }
        )
        subtotal += line_total

    return {
        "tab_id": tab_row["tab_id"],
        "table_id": tab_row["table_id"],
        "items": items,
        "subtotal": round(subtotal, 2),
    }


def _insert_items(conn, tab_id: int, items: List[TabItemIn]) -> None:
    for item in items:
        conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO tab_items (tab_id, item_name, quantity, unit_price)
                VALUES (:tab_id, :item_name, :quantity, :unit_price)
                """
            ),
            {
                "tab_id": tab_id,
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            },
        )


@router.post("/{table_id}/tabs", response_model=TabResponse)
def create_tab(table_id: int, body: TabCreate):
    with db.engine.begin() as conn:
        table_exists = conn.execute(
            sqlalchemy.text("SELECT 1 FROM tables WHERE table_id = :id"),
            {"id": table_id},
        ).scalar_one_or_none()
        if table_exists is None:
            raise HTTPException(status_code=404, detail="Table not found")

        tab_id = conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO tabs (table_id, total_price)
                VALUES (:table_id, 0.0)
                RETURNING tab_id
                """
            ),
            {"table_id": table_id},
        ).scalar_one()

        _insert_items(conn, tab_id, body.items)

        result = _load_tab(conn, table_id, tab_id)
    assert result is not None
    return TabResponse(**result)


@router.patch("/{table_id}/tabs/{tab_id}", response_model=TabResponse)
def update_tab(table_id: int, tab_id: int, body: TabUpdate):
    with db.engine.begin() as conn:
        if _load_tab(conn, table_id, tab_id) is None:
            raise HTTPException(status_code=404, detail="Tab not found for this table")

        _insert_items(conn, tab_id, body.items_to_add)

        result = _load_tab(conn, table_id, tab_id)
    assert result is not None
    return TabResponse(**result)


@router.get("/{table_id}/tabs/{tab_id}", response_model=TabWithTotalsResponse)
def get_tab(table_id: int, tab_id: int):
    with db.engine.connect() as conn:
        result = _load_tab(conn, table_id, tab_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Tab not found for this table")

    subtotal = result["subtotal"]
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)

    return TabWithTotalsResponse(**result, tax=tax, total=total)


@router.post("/{table_id}/tabs/{tab_id}/split", response_model=TabSplitResponse)
def split_tab(table_id: int, tab_id: int, body: TabSplitRequest):
    if not body.items_to_move:
        raise HTTPException(status_code=400, detail="items_to_move cannot be empty")

    with db.engine.begin() as conn:
        tab_row = conn.execute(
            sqlalchemy.text(
                """
                SELECT tab_id, party_id
                FROM tabs
                WHERE tab_id = :tab_id AND table_id = :table_id
                """
            ),
            {"tab_id": tab_id, "table_id": table_id},
        ).mappings().first()
        if tab_row is None:
            raise HTTPException(status_code=404, detail="Tab not found for this table")

        item_rows = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT tab_item_id, item_name, quantity, unit_price
                    FROM tab_items
                    WHERE tab_id = :tab_id
                    ORDER BY tab_item_id
                    """
                ),
                {"tab_id": tab_id},
            )
            .mappings()
            .all()
        )

        available: dict[tuple[str, float], int] = {}
        for row in item_rows:
            key = (row["item_name"], row["unit_price"])
            available[key] = available.get(key, 0) + row["quantity"]

        move_quantities: dict[tuple[str, float], int] = {}
        for item in body.items_to_move:
            if item.quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Item quantity must be greater than zero",
                )
            if item.unit_price < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Item unit_price must be non-negative",
                )
            key = (item.item_name, item.unit_price)
            move_quantities[key] = move_quantities.get(key, 0) + item.quantity

        for (name, unit_price), qty in move_quantities.items():
            if available.get((name, unit_price), 0) < qty:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Not enough quantity to move for item"
                    ),
                )

        new_tab_id = conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO tabs (table_id, party_id, total_price)
                VALUES (:table_id, :party_id, 0.0)
                RETURNING tab_id
                """
            ),
            {"table_id": table_id, "party_id": tab_row["party_id"]},
        ).scalar_one()

        for (name, unit_price), qty_to_move in move_quantities.items():
            remaining = qty_to_move
            for row in item_rows:
                if remaining <= 0:
                    break
                if row["item_name"] != name or row["unit_price"] != unit_price:
                    continue

                if row["quantity"] <= remaining:
                    conn.execute(
                        sqlalchemy.text(
                            """
                            DELETE FROM tab_items
                            WHERE tab_item_id = :tab_item_id
                            """
                        ),
                        {"tab_item_id": row["tab_item_id"]},
                    )
                    remaining -= row["quantity"]
                else:
                    conn.execute(
                        sqlalchemy.text(
                            """
                            UPDATE tab_items
                            SET quantity = :quantity
                            WHERE tab_item_id = :tab_item_id
                            """
                        ),
                        {
                            "quantity": row["quantity"] - remaining,
                            "tab_item_id": row["tab_item_id"],
                        },
                    )
                    remaining = 0

            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO tab_items (tab_id, item_name, quantity, unit_price)
                    VALUES (:tab_id, :item_name, :quantity, :unit_price)
                    """
                ),
                {
                    "tab_id": new_tab_id,
                    "item_name": name,
                    "quantity": qty_to_move,
                    "unit_price": unit_price,
                },
            )

        original = _load_tab(conn, table_id, tab_id)
        new_tab = _load_tab(conn, table_id, new_tab_id)

    assert original is not None
    assert new_tab is not None
    return TabSplitResponse(original_tab=TabResponse(**original), new_tab=TabResponse(**new_tab))
