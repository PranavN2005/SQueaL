from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import List
from src.api import auth

router = APIRouter(
    prefix="/employees",
    tags=["employees"],
    dependencies=[Depends(auth.get_api_key)],
)


class employee(BaseModel):
    employee_id: int
    FirstName: str
    LastName: str


@router.get(
    "/employee/{employee_id}",
    response_model=List[employee],
    status_code=status.HTTP_200_OK,
)
def get_employee(employee_id: int):
    pass
