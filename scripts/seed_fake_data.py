import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from faker import Faker

# how many rows of each
N_EMPLOYEES = 40
N_FOOD_ITEMS = 200
N_TABLES = 50
N_RESERVATIONS = 80_000
N_TABS = 100_000

# 3 year fake history
END = datetime(2026, 6, 1)
START = END - timedelta(days=365 * 3)

fake = Faker()
BATCH = 5000


def random_dt():
    delta = (END - START).total_seconds()
    return START + timedelta(seconds=random.uniform(0, delta))


def insert_batch(cur, sql, rows):
    for i in range(0, len(rows), BATCH):
        cur.executemany(sql, rows[i : i + BATCH])


def make_employees(cur):
    rows = []
    for i in range(1, N_EMPLOYEES + 1):
        rows.append((i, fake.first_name(), fake.last_name()))
    insert_batch(
        cur,
        "INSERT INTO employees (employee_id, first_name, last_name) VALUES (%s, %s, %s)",
        rows,
    )


def make_food_items(cur):
    rows = []
    for i in range(1, N_FOOD_ITEMS + 1):
        name = fake.word().capitalize() + " " + fake.word().capitalize()
        price = round(random.uniform(5, 40), 2)
        rows.append((i, name, price))
    insert_batch(
        cur,
        "INSERT INTO food_items (food_item_id, name, price) VALUES (%s, %s, %s)",
        rows,
    )


def make_tables(cur):
    rows = []
    for i in range(1, N_TABLES + 1):
        cap = random.choices([2, 4, 6, 8], weights=[40, 40, 15, 5])[0]
        occupied = random.random() < 0.3
        status = "occupied" if occupied else "open"
        waiter = random.randint(1, N_EMPLOYEES) if occupied else None
        psize = random.randint(1, cap) if occupied else None
        rows.append((i, cap, status, waiter, psize, None))
    insert_batch(
        cur,
        """
        INSERT INTO tables
            (table_id, capacity, status, assigned_waiter_id, current_party_size, reserved_for)
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
        rows,
    )


def make_reservations(cur):
    rows = []
    for i in range(1, N_RESERVATIONS + 1):
        res_time = random_dt()
        created = max(START, res_time - timedelta(days=random.randint(0, 30)))
        psize = random.choices([2, 3, 4, 5, 6, 8], weights=[40, 20, 25, 8, 5, 2])[0]
        status = random.choices(
            ["reserved", "seated", "cancelled"], weights=[55, 35, 10]
        )[0]
        rows.append(
            (
                i,
                fake.first_name() + " " + fake.last_name(),
                psize,
                random.randint(1, N_TABLES),
                res_time.isoformat(),
                created,
                status,
            )
        )
    insert_batch(
        cur,
        """
        INSERT INTO reservations
            (reservation_id, customer_name, party_size, table_id, reservation_time, created_at, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """,
        rows,
    )


def make_tabs(cur):
    rows = []
    tab_info = []
    for i in range(1, N_TABS + 1):
        created = random_dt()
        status = random.choices(["paid", "open", "void"], weights=[88, 7, 5])[0]
        total = round(random.uniform(15, 150), 2)
        if status in ("paid", "void"):
            closed = created + timedelta(minutes=random.randint(30, 240))
        else:
            closed = None
        table_id = random.randint(1, N_TABLES)
        rows.append((i, total, created, table_id, status, closed))
        tab_info.append((i, created, status, total))
    insert_batch(
        cur,
        """
        INSERT INTO tabs
            (tab_id, total_price, created_at, table_id, status, closed_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
        rows,
    )
    return tab_info


def make_tab_items(cur, tab_info):
    rows = []
    item_id = 1
    for tab_id, _created, _status, _total in tab_info:
        n = random.randint(5, 10)
        for _ in range(n):
            name = fake.word().capitalize() + " " + fake.word().capitalize()
            qty = random.choices([1, 2, 3, 4], weights=[80, 12, 5, 3])[0]
            price = round(random.uniform(3, 30), 2)
            rows.append((item_id, tab_id, name, qty, price))
            item_id += 1
    insert_batch(
        cur,
        """
        INSERT INTO tab_items (tab_item_id, tab_id, item_name, quantity, unit_price)
        VALUES (%s, %s, %s, %s, %s)
    """,
        rows,
    )


def make_payments(cur, tab_info):
    rows = []
    pid = 1
    for tab_id, created, status, total in tab_info:
        if status != "paid":
            continue
        # subtotal = the tab total, tax = 8.5%, tip = 10-25%
        tax = round(total * 0.085, 2)
        tip = round(total * random.uniform(0.10, 0.25), 2)
        full = round(total + tax + tip, 2)
        method = random.choices(["card", "cash", "mobile"], weights=[70, 20, 10])[0]
        paid_at = created + timedelta(minutes=random.randint(30, 180))
        rows.append((pid, tab_id, total, tax, tip, full, method, paid_at))
        pid += 1
    insert_batch(
        cur,
        """
        INSERT INTO payments
            (payment_id, tab_id, subtotal, tax, tip, total, payment_method, paid_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """,
        rows,
    )


# order matters because of foreign keys
ALL_TABLES = [
    "payments",
    "tab_items",
    "tabs",
    "reservations",
    "tables",
    "food_items",
    "employees",
]

# (table, pk column) so we can fix the autoincrement sequences after using explicit ids
SEQ_FIX = [
    ("employees", "employee_id"),
    ("food_items", "food_item_id"),
    ("tables", "table_id"),
    ("reservations", "reservation_id"),
    ("tabs", "tab_id"),
    ("tab_items", "tab_item_id"),
    ("payments", "payment_id"),
]


def main():
    # load env so we can grab POSTGRES_URI
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / "default.env")
    if (root / ".env").exists():
        load_dotenv(root / ".env", override=True)

    uri = os.environ["POSTGRES_URI"]
    uri = uri.replace("postgresql+psycopg://", "postgresql://")

    conn = psycopg.connect(uri)
    cur = conn.cursor()

    t0 = time.time()

    print("wiping tables...")
    cur.execute("TRUNCATE " + ", ".join(ALL_TABLES) + " RESTART IDENTITY CASCADE")

    print("employees...")
    make_employees(cur)
    print("food_items...")
    make_food_items(cur)
    print("tables...")
    make_tables(cur)
    print("reservations...")
    make_reservations(cur)
    print("tabs...")
    tabs = make_tabs(cur)
    print("tab_items (this one takes a while)...")
    make_tab_items(cur, tabs)
    print("payments...")
    make_payments(cur, tabs)

    print("fixing sequences...")
    for table, pk in SEQ_FIX:
        cur.execute(
            f"SELECT setval('{table}_{pk}_seq', (SELECT MAX({pk}) FROM {table}))"
        )

    conn.commit()
    cur.close()
    conn.close()

    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
