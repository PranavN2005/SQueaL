from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import datetime
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/parties",
    tags=["parties"],
    dependencies=[Depends(auth.get_api_key)],
)


class PartyCreate(BaseModel):
    name: str
    party_size: int


class Party(BaseModel):
    id: int
    name: str
    party_size: int


class FoodItem(BaseModel):
    name: str
    quantity: int
    unit_price: float


class PartyTab(BaseModel):
    id: int
    party_id: int
    tab_items: List[FoodItem]
    total_price: float
    created_at: str


class TabsResponse(BaseModel):
    tabs: List[PartyTab]


@router.post("/", response_model=Party, status_code=status.HTTP_201_CREATED)
def create_party(body: PartyCreate):
    with db.engine.begin() as conn:
        row = (
            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO parties (name, party_size)
                    VALUES (:name, :party_size)
                    RETURNING party_id, name, party_size
                    """
                ),
                {"name": body.name, "party_size": body.party_size},
            )
            .mappings()
            .first()
        )
        assert row is not None
        return Party(
            id=row["party_id"],
            name=row["name"],
            party_size=row["party_size"],
        )


@router.post("/{party_id}/tabs", response_model=TabsResponse)
def create_party_tab(party_id: int, tab_items: List[FoodItem]):
    with db.engine.begin() as conn:
        party_row = (
            conn.execute(
                sqlalchemy.text(
                    "SELECT party_id, table_id FROM parties WHERE party_id = :party_id"
                ),
                {"party_id": party_id},
            )
            .mappings()
            .first()
        )

        if not party_row:
            raise HTTPException(status_code=404, detail="Party not found")

        table_id = party_row["table_id"]
        total_price = sum(item.quantity * item.unit_price for item in tab_items)

        tab_row = (
            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO tabs (party_id, table_id, total_price)
                    VALUES (:party_id, :table_id, :total_price)
                    RETURNING tab_id, created_at
                    """
                ),
                {
                    "party_id": party_id,
                    "table_id": table_id,
                    "total_price": total_price,
                },
            )
            .mappings()
            .first()
        )
        assert tab_row is not None

        tab_id = tab_row["tab_id"]
        created_at = tab_row["created_at"]

        for item in tab_items:
            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO tab_items (tab_id, item_name, quantity, unit_price)
                    VALUES (:tab_id, :item_name, :quantity, :unit_price)
                    """
                ),
                {
                    "tab_id": tab_id,
                    "item_name": item.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                },
            )

        return TabsResponse(
            tabs=[
                PartyTab(
                    id=tab_id,
                    party_id=party_id,
                    tab_items=tab_items,
                    total_price=total_price,
                    created_at=str(created_at),
                )
            ]
        )


@router.get("/{party_id}/", response_model=Party)
def get_party(party_id: int):
    with db.engine.connect() as conn:
        row = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT party_id, name, party_size
                    FROM parties
                    WHERE party_id = :party_id
                    """
                ),
                {"party_id": party_id},
            )
            .mappings()
            .first()
        )

        if not row:
            raise HTTPException(status_code=404, detail="Party not found")

        return Party(
            id=row["party_id"],
            name=row["name"],
            party_size=row["party_size"],
        )


@router.delete("/{party_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_party(party_id: int):
    with db.engine.begin() as conn:
        conn.execute(
            sqlalchemy.text("DELETE FROM parties WHERE party_id = :party_id"),
            {"party_id": party_id},
        )


@router.get("/{party_id}/tabs", response_model=TabsResponse)
def get_party_tabs(party_id: int):
    with db.engine.connect() as conn:
        rows = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT
                        tabs.tab_id,
                        tabs.party_id,
                        tabs.total_price,
                        tabs.created_at,
                        tab_items.item_name,
                        tab_items.quantity,
                        tab_items.unit_price
                    FROM tabs
                    LEFT JOIN tab_items ON tabs.tab_id = tab_items.tab_id
                    WHERE tabs.party_id = :party_id
                    ORDER BY tabs.tab_id
                    """
                ),
                {"party_id": party_id},
            )
            .mappings()
            .all()
        )

        if not rows:
            raise HTTPException(status_code=404, detail="No tabs found for party")

        tabs_by_id: dict = {}
        for row in rows:
            tid = row["tab_id"]
            if tid not in tabs_by_id:
                tabs_by_id[tid] = {
                    "id": tid,
                    "party_id": row["party_id"],
                    "tab_items": [],
                    "total_price": row["total_price"],
                    "created_at": str(row["created_at"]),
                }
            if row["item_name"] is not None:
                tabs_by_id[tid]["tab_items"].append(
                    FoodItem(
                        name=row["item_name"],
                        quantity=row["quantity"],
                        unit_price=row["unit_price"],
                    )
                )

        return TabsResponse(tabs=[PartyTab(**t) for t in tabs_by_id.values()])


@router.patch("/{party_id}/tabs/{tab_id}", response_model=PartyTab)
def update_party_tab(party_id: int, tab_id: int, tab_items: List[FoodItem]):
    with db.engine.begin() as conn:
        party_row = (
            conn.execute(
                sqlalchemy.text(
                    "SELECT party_id FROM parties WHERE party_id = :party_id"
                ),
                {"party_id": party_id},
            )
            .mappings()
            .first()
        )

        if not party_row:
            raise HTTPException(status_code=404, detail="Party not found")

        total_price = sum(item.quantity * item.unit_price for item in tab_items)

        conn.execute(
            sqlalchemy.text(
                """
                UPDATE tabs
                SET total_price = :total_price
                WHERE tab_id = :tab_id AND party_id = :party_id
                """
            ),
            {"total_price": total_price, "tab_id": tab_id, "party_id": party_id},
        )

        conn.execute(
            sqlalchemy.text("DELETE FROM tab_items WHERE tab_id = :tab_id"),
            {"tab_id": tab_id},
        )

        for item in tab_items:
            conn.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO tab_items (tab_id, item_name, quantity, unit_price)
                    VALUES (:tab_id, :item_name, :quantity, :unit_price)
                    """
                ),
                {
                    "tab_id": tab_id,
                    "item_name": item.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                },
            )

        return PartyTab(
            id=tab_id,
            party_id=party_id,
            tab_items=tab_items,
            total_price=total_price,
            created_at=str(datetime.utcnow()),
        )
