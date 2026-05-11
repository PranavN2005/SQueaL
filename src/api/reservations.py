from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
