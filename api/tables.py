
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
import json
from src.api import auth
from src import database as db
import sqlalchemy

## GET  /tables/{table_id}}/tabs

## POST /tables/{table_id}}/tabs

## DELETE /tables/{table_id}/tabs

router = APIRouter(
    prefix="/tables",
    tags=["tables"],
    dependencies=[Depends(auth.get_api_key)],
)

class table_id(BaseModel):
    id: int
    name: str
    capacity: int
    is_available: bool

@router.get("/tables/", response_model=List[table])
def get_tables():
    pass

@router.get("/tables/{table_id}", response_model=table)
def get_table(table_id: int):
    pass
