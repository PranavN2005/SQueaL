from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/tabs",
    tags=["tabs"],
    dependencies=[Depends(auth.get_api_key)],
)

TAX_RATE = 0.0775  # SLO county sales tax


class TabItemIn(BaseModel):
    item_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class TabItemOut(BaseModel):
    item_name: str
    quantity: int
    unit_price: float
    line_total: float


class TabCreate(BaseModel):
    table_id: int = Field(..., gt=0)
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


class TabSummary(BaseModel):
    tab_id: int
    table_id: int
    status: str
    item_count: int
    subtotal: float


class TabSplitResponse(BaseModel):
    original_tab: TabResponse
    new_tab: TabResponse


def _load_tab(conn, tab_id: int) -> Optional[dict]:
    tab_row = (
        conn.execute(
            sqlalchemy.text(
                """
                SELECT tab_id, table_id
                FROM tabs
                WHERE tab_id = :tab_id
                """
            ),
            {"tab_id": tab_id},
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
    if not items:
        return
    conn.execute(
        sqlalchemy.text(
            """
            INSERT INTO tab_items (tab_id, item_name, quantity, unit_price)
            VALUES (:tab_id, :item_name, :quantity, :unit_price)
            """
        ),
        [
            {
                "tab_id": tab_id,
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in items
        ],
    )


@router.post("/", response_model=TabResponse)
def create_tab(body: TabCreate):
    with db.engine.begin() as conn:
        table_exists = conn.execute(
            sqlalchemy.text("SELECT 1 FROM tables WHERE table_id = :id"),
            {"id": body.table_id},
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
            {"table_id": body.table_id},
        ).scalar_one()

        _insert_items(conn, tab_id, body.items)

        result = _load_tab(conn, tab_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Internal error")
    return TabResponse(**result)


@router.get("/", response_model=List[TabSummary])
def list_tabs(table_id: Optional[int] = None):
    with db.engine.connect() as conn:
        if table_id is not None:
            table_exists = conn.execute(
                sqlalchemy.text("SELECT 1 FROM tables WHERE table_id = :table_id"),
                {"table_id": table_id},
            ).scalar_one_or_none()
            if table_exists is None:
                raise HTTPException(status_code=404, detail="Table not found")

        where_clause = ""
        params: dict = {}
        if table_id is not None:
            where_clause = "WHERE t.table_id = :table_id"
            params["table_id"] = table_id

        query = f"""
            SELECT
                t.tab_id,
                t.table_id,
                t.status,
                COALESCE(SUM(ti.quantity), 0) AS item_count,
                COALESCE(SUM(ti.quantity * ti.unit_price), 0) AS subtotal
            FROM tabs t
            LEFT JOIN tab_items ti ON t.tab_id = ti.tab_id
            {where_clause}
            GROUP BY t.tab_id, t.table_id, t.status
            ORDER BY t.tab_id
        """

        rows = conn.execute(sqlalchemy.text(query), params).mappings().all()

    summaries: List[TabSummary] = []
    for row in rows:
        subtotal_value = row["subtotal"] or 0
        summaries.append(
            TabSummary(
                tab_id=row["tab_id"],
                table_id=row["table_id"],
                status=row["status"],
                item_count=row["item_count"],
                subtotal=float(round(subtotal_value, 2)),
            )
        )

    return summaries


@router.patch("/{tab_id}", response_model=TabResponse)
def update_tab(tab_id: int, body: TabUpdate):
    with db.engine.begin() as conn:
        tab_exists = conn.execute(
            sqlalchemy.text("SELECT 1 FROM tabs WHERE tab_id = :tab_id"),
            {"tab_id": tab_id},
        ).scalar_one_or_none()
        if tab_exists is None:
            raise HTTPException(status_code=404, detail="Tab not found")

        _insert_items(conn, tab_id, body.items_to_add)

        result = _load_tab(conn, tab_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Internal error")
    return TabResponse(**result)


@router.get("/{tab_id}", response_model=TabWithTotalsResponse)
def get_tab(tab_id: int):
    with db.engine.connect() as conn:
        result = _load_tab(conn, tab_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Tab not found")

    subtotal = result["subtotal"]
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)

    return TabWithTotalsResponse(**result, tax=tax, total=total)


@router.post("/{tab_id}/split", response_model=TabSplitResponse)
def split_tab(tab_id: int, body: TabSplitRequest):
    if not body.items_to_move:
        raise HTTPException(status_code=400, detail="items_to_move cannot be empty")

    with db.engine.begin() as conn:
        tab_row = (
            conn.execute(
                sqlalchemy.text(
                    """
                SELECT tab_id, table_id
                FROM tabs
                WHERE tab_id = :tab_id
                """
                ),
                {"tab_id": tab_id},
            )
            .mappings()
            .first()
        )
        if tab_row is None:
            raise HTTPException(status_code=404, detail="Tab not found")

        table_id = tab_row["table_id"]

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
                    detail=("Not enough quantity to move for item"),
                )

        new_tab_id = conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO tabs (table_id, total_price)
                VALUES (:table_id, 0.0)
                RETURNING tab_id
                """
            ),
            {"table_id": table_id},
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

        original = _load_tab(conn, tab_id)
        new_tab = _load_tab(conn, new_tab_id)

    if original is None or new_tab is None:
        raise HTTPException(status_code=500, detail="Internal error")
    return TabSplitResponse(
        original_tab=TabResponse(**original), new_tab=TabResponse(**new_tab)
    )


## New endpoint for deleting an item from a tab(suggested by peer reviews)
@router.delete("/{tab_id}/items/{tab_item_id}", response_model=TabResponse)
def delete_tab_item(tab_id: int, tab_item_id: int):
    with db.engine.begin() as conn:
        tab_exists = conn.execute(
            sqlalchemy.text("SELECT 1 FROM tabs WHERE tab_id = :tab_id"),
            {"tab_id": tab_id},
        ).scalar_one_or_none()
        if tab_exists is None:
            raise HTTPException(status_code=404, detail="Tab not found")

        item = conn.execute(
            sqlalchemy.text(
                """
                SELECT tab_item_id FROM tab_items
                WHERE tab_item_id = :tab_item_id AND tab_id = :tab_id
                """
            ),
            {"tab_item_id": tab_item_id, "tab_id": tab_id},
        ).scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail="Item not found on this tab")

        conn.execute(
            sqlalchemy.text("DELETE FROM tab_items WHERE tab_item_id = :tab_item_id"),
            {"tab_item_id": tab_item_id},
        )

        result = _load_tab(conn, tab_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Internal error")
    return TabResponse(**result)
