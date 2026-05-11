from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import List
from src.api import auth

router = APIRouter(
    prefix="/parties",
    tags=["parties"],
    dependencies=[Depends(auth.get_api_key)],
)

class party(BaseModel):
    id: int
    name: str
    party_size: int


class foodItem(BaseModel):
    id: int
    name: str
    price: float


class partyTab(BaseModel):
    id: int
    party_id: int
    tab_items: List[foodItem]
    total_price: float
    created_at: str


class tabsResponse(BaseModel):
    tabs: List[partyTab]

@router.post("/", response_model=party, status_code=status.HTTP_201_CREATED)
def create_party(party: party):
    with db.engine.begin() as conn:
        result = conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO parties (name, party_size) 
                VALUES (:name, :party_size) 
                RETURNING party_id, name, party_size
                """
            ),
            {"name": party.name, "party_size": party.party_size}
        ).mapping().first()
        
        return party(
            id=result["party_id"],
            name=result["name"],
            party_size=result["party_size"]
        )

@router.post("/{party_id}/tabs", response_model=tabsResponse)
def create_party_tab(party_id: int, tab_items: List[foodItem]):
    with db.engine.begin() as conn:
        party_row = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT party_id, tab_id 
                    FROM parties 
                    WHERE party_id = :party_id
                    """
                ),
                {"party_id": party_id}
            ).mapping().first()
        )

        if not party_row:
            raise HTTPException(status_code=404, detail="Party not found")
        
        table_id = party_row["table_id"]
        total_price = sum(item.price for item in tab_items)
        
        tab_row = conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO tabs (party_id, table_id, total_price) 
                VALUES (:party_id, :table_id, :total_price) 
                RETURNING tab_id, created_at
                """
            ),
            {"party_id": party_id, "table_id": table_id, "total_price": total_price}
        ).mapping().first()
            
        tab_id = tab_row["tab_id"]["tab_id"]
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
                    "unit_price": item.price
                }

                response = partyTab(
                    id=tab_id,
                    party_id=party_id,
                    tab_items=tab_items,
                    total_price=total_price,
                    created_at=created_at
                )
                return tabsResponse(tabs=[response])
            )

@router.get("/{party_id}/", response_model=party)
def get_party(party_id: int):
    with db.engine.connect() as connection:
        row = connection.execute(
            sqlalchemy.text("""
                    SELECT party_id AS id, name, party_size
                    FROM parties
                    WHERE party_id = :party_id
                    """)
                    ,{"party_id": party_id}
        ).mapping().first()

        if not row:
            raise HTTPException(status_code=404, detail="Party not found")

        return party(
            id=row["id"],
            name=row["name"],
            party_size=row["party_size"]
        )
    
@router.delete("/{party_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_party(party_id: int):
    with db.engine.connect() as connection:
        connection.execute(
            db.text("""
                    DELETE FROM parties WHERE id = :party_id
                    """),
            {"party_id": party_id}
        )
    
    
@router.get("/{party_id}/tabs", response_model=tabsResponse)
def get_party_tabs(party_id: int):
    with db.engine.connect() as connection:
        row = connection.execute(
            sqlalchemy.text("""
                    SELECT table_id, tab_id AS tab, 
                           party_id AS Party, total_price AS Total,
                           item_name AS Items, quantity AS Quantity, 
                           unit_price AS ItemPrice,
                           created_at AS Time
                    FROM tabs
                    JOIN tab_items ON tabs.tab_id = tab_items.tab_id
                    WHERE party_id = :party_id
                    """)
                    ,{"party_id": party_id}
        ) 

        if not row:
            raise HTTPException(status_code=404, detail="Party not found")
        
        total_price = sum{ItemPrice * quantity for ItemPrice, quantity in row}

        return partyTab(
            id=tab_id,
            party_id=party_id,
            tab_items=tab_items,
            total_price=total_price,
            created_at=str(datetime.utcnow())
        )

                        

@router.patch("/{party_id}/tabs/{tab_id}", response_model=partyTab)
def update_party_tab(party_id: int, tab_id: int, tab_items: List[foodItem]):
    with db.engine.begin() as conn:
        party_row = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT party_id 
                    FROM parties 
                    WHERE party_id = :party_id
                    """
                ),
                {"party_id": party_id}
            ).mapping().first()
        )

        if not party_row:
            raise HTTPException(status_code=404, detail="Party not found")
        
        total_price = sum(item.price for item in tab_items)
        
        conn.execute(
            sqlalchemy.text(
                """
                UPDATE tabs 
                SET total_price = :total_price 
                WHERE tab_id = :tab_id AND party_id = :party_id
                """
            ),
            {"total_price": total_price, "tab_id": tab_id, "party_id": party_id}
        )
        
        conn.execute(
            sqlalchemy.text(
                """
                DELETE FROM tab_items 
                WHERE tab_id = :tab_id
                """
            ),
            {"tab_id": tab_id}
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
                    "unit_price": item.price
                }
            )
            
        return partyTab(
            id=tab_id,
            party_id=party_id,
            tab_items=tab_items,
            total_price=total_price,
            created_at=str(datetime.utcnow())
        )