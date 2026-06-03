from fastapi import FastAPI
from src.api import reservations, employees, tables, tabs, checkout
from starlette.middleware.cors import CORSMiddleware


description = """
The restaurant hosting application helps staff manage tables, reservations, server assignments, and customer tabs in real time.
"""
tags_metadata = [
    {
        "name": "reservations",
        "description": "Create, view and manage reservations for tables.",
    },
    {
        "name": "employees",
        "description": "Employee lookup and assignments (waitstaff, hosts).",
    },
    {"name": "tables", "description": "View and manage table status and assignments."},
    {"name": "tabs", "description": "Create and update tabs for tables."},
    {"name": "checkout", "description": "Pay and close out a tab."},
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

origins = ["*"] #removed leftover stuff we got from potion shop Lol

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(reservations.router)
app.include_router(employees.router)
app.include_router(tables.router)
app.include_router(tabs.router)
app.include_router(checkout.router)


@app.get("/")
async def root():
    return {"message": "Restaurant is open for business!"}
