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


@router.delete("/{reservation_id}", status_code=204)
def cancel_reservation(reservation_id: int):
    with db.engine.begin() as conn:
        reservation = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT reservation_id, customer_name, table_id, status
                    FROM reservations
                    WHERE reservation_id = :reservation_id
                    """
                ),
                {"reservation_id": reservation_id},
            )
            .mappings()
            .first()
        )
        if reservation is None:
            raise HTTPException(status_code=404, detail="Reservation not found")
        if reservation["status"] == "cancelled":
            raise HTTPException(
                status_code=409, detail="Reservation is already cancelled"
            )

        conn.execute(
            sqlalchemy.text(
                "UPDATE reservations SET status = 'cancelled' "
                "WHERE reservation_id = :reservation_id"
            ),
            {"reservation_id": reservation_id},
        )

        table = (
            conn.execute(
                sqlalchemy.text(
                    "SELECT status, reserved_for FROM tables WHERE table_id = :table_id"
                ),
                {"table_id": reservation["table_id"]},
            )
            .mappings()
            .first()
        )
        if (
            table is not None
            and table["status"] == "reserved"
            and table["reserved_for"] == reservation["customer_name"]
        ):
            conn.execute(
                sqlalchemy.text(
                    "UPDATE tables SET status = 'open', reserved_for = NULL "
                    "WHERE table_id = :table_id"
                ),
                {"table_id": reservation["table_id"]},
            )


@router.post("/", response_model=ReservationResponse)
def create_reservation(body: ReservationCreate):
    with db.engine.begin() as conn:
        capacity = conn.execute(
            sqlalchemy.text("SELECT capacity FROM tables WHERE table_id = :table_id"),
            {"table_id": body.table_id},
        ).scalar_one_or_none()
        if capacity is None:
            raise HTTPException(status_code=404, detail="Table not found")

        if body.party_size > capacity:
            raise HTTPException(
                status_code=400,
                detail="party_size cannot exceed table capacity",
            )

        conflict = conn.execute(
            sqlalchemy.text(
                """
                SELECT 1 FROM reservations
                WHERE table_id = :table_id
                  AND reservation_time = :reservation_time
                  AND status = 'reserved'
                """
            ),
            {
                "table_id": body.table_id,
                "reservation_time": body.reservation_time,
            },
        ).scalar_one_or_none()
        if conflict is not None:
            raise HTTPException(
                status_code=409,
                detail="Table is already reserved for this time",
            )

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
