from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/reservations",
    tags=["reservations"],
    dependencies=[Depends(auth.get_api_key)],
)


class ReservationCreate(BaseModel):
    customer_name: str
    table_id: int
    party_size: int
    reservation_time: str


class ReservationResponse(BaseModel):
    reservation_id: int
    customer_name: str
    table_id: int
    party_size: int
    reservation_time: str
    status: str


@router.get("/", response_model=List[ReservationResponse])
def get_reservations(status: Optional[str] = None, table_id: Optional[int] = None):
    query = (
        "SELECT reservation_id, customer_name, table_id, party_size, "
        "reservation_time, status FROM reservations"
    )
    filters = []
    params: dict = {}
    if status:
        filters.append("status = :status")
        params["status"] = status
    if table_id is not None:
        filters.append("table_id = :table_id")
        params["table_id"] = table_id
    if filters:
        query = f"{query} WHERE {' AND '.join(filters)}"
    query = f"{query} ORDER BY reservation_time"

    with db.engine.connect() as conn:
        rows = conn.execute(sqlalchemy.text(query), params).mappings().all()

    return [ReservationResponse(**row) for row in rows]


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(reservation_id: int):
    with db.engine.connect() as conn:
        row = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT reservation_id, customer_name, table_id, party_size,
                           reservation_time, status
                    FROM reservations
                    WHERE reservation_id = :reservation_id
                    """
                ),
                {"reservation_id": reservation_id},
            )
            .mappings()
            .first()
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    return ReservationResponse(**row)


@router.post("/", response_model=ReservationResponse)
def create_reservation(body: ReservationCreate):
    with db.engine.begin() as conn:
        table_exists = conn.execute(
            sqlalchemy.text("SELECT 1 FROM tables WHERE table_id = :table_id"),
            {"table_id": body.table_id},
        ).scalar_one_or_none()
        if table_exists is None:
            raise HTTPException(status_code=404, detail="Table not found")

        reservation_id = conn.execute(
            sqlalchemy.text(
                """
                INSERT INTO reservations
                    (customer_name, table_id, party_size, reservation_time, status)
                VALUES
                    (:customer_name, :table_id, :party_size, :reservation_time, 'reserved')
                RETURNING reservation_id
                """
            ),
            body.model_dump(),
        ).scalar_one()

        conn.execute(
            sqlalchemy.text(
                """
                UPDATE tables
                SET status = 'reserved', reserved_for = :customer_name
                WHERE table_id = :table_id
                """
            ),
            {"customer_name": body.customer_name, "table_id": body.table_id},
        )

    return ReservationResponse(
        reservation_id=reservation_id,
        customer_name=body.customer_name,
        table_id=body.table_id,
        party_size=body.party_size,
        reservation_time=body.reservation_time,
        status="reserved",
    )
