# api/tables.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
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
    reserved_for: Optional[str] = None


class AssignWaiterBody(BaseModel):
    assigned_waiter_id: int = Field(..., gt=0)


class AssignWaiterResponse(BaseModel):
    table_id: int
    assigned_waiter_id: int


class TableUpdate(BaseModel):
    status: Optional[Literal["open", "occupied", "reserved", "dirty"]] = None
    current_party_size: Optional[int] = Field(None, ge=0)
    reserved_for: Optional[str] = None


def _get_table_row(conn, table_id: int) -> Optional[dict]:
    row = (
        conn.execute(
            sqlalchemy.text(
                """
            SELECT table_id, capacity, status, assigned_waiter_id, current_party_size, reserved_for
            FROM tables
            WHERE table_id = :table_id
            """
            ),
            {"table_id": table_id},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def _employee_exists(conn, employee_id: int) -> bool:
    return (
        conn.execute(
            sqlalchemy.text("SELECT 1 FROM employees WHERE employee_id = :id"),
            {"id": employee_id},
        ).scalar_one_or_none()
        is not None
    )


@router.get("/", response_model=List[TableResponse])
def get_tables():
    query = sqlalchemy.text("""
        SELECT
            table_id,
            capacity,
            status,
            assigned_waiter_id,
            current_party_size,
            reserved_for
        FROM tables
        ORDER BY table_id
    """)

    with db.engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [TableResponse(**row) for row in rows]


@router.get("/{table_id}", response_model=TableResponse)
def get_table(table_id: int):
    with db.engine.connect() as conn:
        table = _get_table_row(conn, table_id)

    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    return TableResponse(**table)


@router.patch("/{table_id}/assigned_waiter", response_model=AssignWaiterResponse)
def patch_assigned_waiter(table_id: int, body: AssignWaiterBody):
    with db.engine.begin() as conn:
        table = _get_table_row(conn, table_id)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
        if not _employee_exists(conn, body.assigned_waiter_id):
            raise HTTPException(status_code=404, detail="Employee not found")

        conn.execute(
            sqlalchemy.text(
                """
                UPDATE tables
                SET assigned_waiter_id = :assigned_waiter_id
                WHERE table_id = :table_id
                """
            ),
            {
                "assigned_waiter_id": body.assigned_waiter_id,
                "table_id": table_id,
            },
        )

    return AssignWaiterResponse(
        table_id=table_id,
        assigned_waiter_id=body.assigned_waiter_id,
    )


@router.patch("/{table_id}", response_model=TableResponse)
def patch_table(table_id: int, body: TableUpdate):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided",
        )

    with db.engine.begin() as conn:
        table = _get_table_row(conn, table_id)
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")

        if (
            "current_party_size" in updates
            and updates["current_party_size"] is not None
        ):
            if updates["current_party_size"] > table["capacity"]:
                raise HTTPException(
                    status_code=400,
                    detail="current_party_size cannot exceed table capacity",
                )

        set_parts: List[str] = []
        params: dict = {"table_id": table_id}
        if "status" in updates:
            set_parts.append("status = :status")
            params["status"] = updates["status"]
        if "current_party_size" in updates:
            set_parts.append("current_party_size = :current_party_size")
            params["current_party_size"] = updates["current_party_size"]
        if "reserved_for" in updates:
            set_parts.append("reserved_for = :reserved_for")
            params["reserved_for"] = updates["reserved_for"]

        conn.execute(
            sqlalchemy.text(
                f"""
                UPDATE tables
                SET {", ".join(set_parts)}
                WHERE table_id = :table_id
                """
            ),
            params,
        )

        updated = _get_table_row(conn, table_id)
    assert updated is not None
    return TableResponse(**updated)


@router.post("/{table_id}/reset", response_model=TableResponse)
def reset_table(table_id: int):
    with db.engine.begin() as conn:
        if _get_table_row(conn, table_id) is None:
            raise HTTPException(status_code=404, detail="Table not found")

        conn.execute(
            sqlalchemy.text(
                """
                UPDATE tables
                SET status = 'open',
                    assigned_waiter_id = NULL,
                    current_party_size = NULL,
                    reserved_for = NULL
                WHERE table_id = :table_id
                """
            ),
            {"table_id": table_id},
        )

        updated = _get_table_row(conn, table_id)
    assert updated is not None
    return TableResponse(**updated)
