from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
import json
from src.api import auth
from src import database as db
import sqlalchemy
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/reservations",
    tags=["reservations"],
    dependencies=[Depends(auth.get_api_key)],
)

class reservation(BaseModel):
    reservation_id: int
    customer_name:str
    party_size: int
    table_id: int
    time: datetime.datetime

class reservationResponse(BaseModel):
    id: int
    party_name: str
    table_ids: List[int]
    time: datetime.datetime
    

@router.post("/reservations/{party_id}", response_model=reservationResponse)
def make_reservation(party_name: str, party_size: int, table_id: int, time: datetime.datetime):
    pass


## Find reservation for a table
@router.get("/reservations/{party_id}", response_model=List[CheckoutResponse])
def get_reservation(party_id: int, table_id: int):
    query = sqlalchemy.text("""
        SELECT 
            reservation_id, 
            customer_name, 
            party_size, 
            table_id, 
            time
        FROM reservations
        WHERE table_id = :table_id AND party_id = :party_id
        ORDER BY time
    """)
    with db.engine.connect() as conn:
        conn.execute(query)

@router.delete("/reservations/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation(party_id: int):
    pass

## POtable_idST reservations/{party_id]}
@router.post("/reservations/{party_id}", response_model=List[CheckoutResponse])
def assign_party(party_id: int, ):
    pass


