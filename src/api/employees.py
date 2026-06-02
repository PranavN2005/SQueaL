from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/employees",
    tags=["employees"],
    dependencies=[Depends(auth.get_api_key)],
)


class EmployeeResponse(BaseModel):
    employee_id: int
    first_name: str
    last_name: str


@router.get(
    "/",
    response_model=List[EmployeeResponse],
    status_code=status.HTTP_200_OK,
)
def get_employees():
    query = sqlalchemy.text("""
        SELECT employee_id, first_name, last_name
        FROM employees
        ORDER BY employee_id
    """)
    with db.engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [EmployeeResponse(**row) for row in rows]


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
)
def get_employee(employee_id: int):
    with db.engine.connect() as conn:
        row = (
            conn.execute(
                sqlalchemy.text(
                    """
                    SELECT employee_id, first_name, last_name
                    FROM employees
                    WHERE employee_id = :employee_id
                    """
                ),
                {"employee_id": employee_id},
            )
            .mappings()
            .first()
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    return EmployeeResponse(**row)
