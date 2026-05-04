# api/tables.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/tables",
    tags=["tables"],
    dependencies=[Depends(auth.get_api_key)],
)

class TableResponse(BaseModel):
    table_id: int
    capacity: int
    status: str
    assigned_waiter_id: Optional[int] = None
    current_party_size: Optional[int] = None
    

@router.get("/", response_model=List[TableResponse])
def get_tables():
    query = sqlalchemy.text("""
        SELECT
            table_id,
            capacity,
            status,
            assigned_waiter_id,
            current_party_size
        FROM tables
        ORDER BY table_id
    """)

    with db.engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [TableResponse(**row) for row in rows]