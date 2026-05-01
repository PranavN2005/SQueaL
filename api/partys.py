from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
import json
from src.api import auth
from src import database as db
import sqlalchemy
from datetime import datetime, timedelta

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

@router.post("/parties/{party_id}/tabs", response_model=tabsResponse)
def create_party_tab(party_id: int, tab_items: List[foodItem]):
    pass

@router.get("/parties/{party_id}/tabs", response_model=tabsResponse)
def get_party_tabs(party_id: int):
    pass

@router.delete("/parties/{party_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_party(party_id: int):
    pass


