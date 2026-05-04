from fastapi import FastAPI
from src.api import partys, reservations, employees, tables
from starlette.middleware.cors import CORSMiddleware


description = """
The restaurant hosting application helps staff manage tables, reservations, server assignments, and customer tabs in real time.
"""
tags_metadata = [
    {
        "name": "parties",
        "description": "Manage parties, tabs and party-related actions.",
    },
    {
        "name": "reservations",
        "description": "Create, view and manage reservations for tables.",
    },
    {
        "name": "employees",
        "description": "Employee lookup and assignments (waitstaff, hosts).",
    },
    {"name": "tables", "description": "View and manage table status and assignments."},
]

app = FastAPI(
    title="SQueaL",
    description=description,
    version="0.0.1",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "Danny Kullman",
        "email": "dannykullman@gmail.com",
    },
    openapi_tags=tags_metadata,
)

origins = ["https://potion-exchange.vercel.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(partys.router)
app.include_router(reservations.router)
app.include_router(employees.router)
app.include_router(tables.router)


@app.get("/")
async def root():
    return {"message": "House is open for business!"}
