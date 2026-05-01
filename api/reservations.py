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
    customer_name:str = Field(..., min_length=1)
    party_size: int = Field(..., gt=0)
    table_id: int = Field(..., gt=0)
    time: datetime.datetime

class reservationResponse(BaseModel):
    id: int
    party_name: str
    table_ids: List[int, gt=0]
    time: datetime.datetime
    


@router.post("/reservations/{party_id}", response_model=reservationResponse)
def make_reservation(party_name: str, party_size: int, table_id: int, time: datetime.datetime):
    pass


## Find reservation for a table
@router.get("/reservations/{party_id}", response_model=List[CheckoutResponse])
def get_reservation(party_id: int, table_id: int):
    pass

@router.delete("/reservations/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation(party_id: int):
    pass



## POtable_idST reservations/{party_id]}
@router.post("/reservations/{party_id}", response_model=List[CheckoutResponse])
def assign_party(party_id: int, ):
    pass

## GET reservations/{party_id}


## DELETE reservations/{table_id}


