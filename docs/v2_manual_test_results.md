# Example workflow 1

A party of 4 walks in without a reservation. The host needs to find an available table that fits them.

1. The host first checks what tables are available by calling `GET /tables/`. She sees that table 3 (capacity 4) and several other tables have status `"open"`. She picks table 3 as the closest fit for 4 guests.
2. The host checks who is working today by calling `GET /employees/`. (We have not modeled shifts; every employee is treated as on-shift.) She sees Danny Kullman (employee 12) is on the floor.
3. The host assigns waiter 12 to table 3 by calling `PATCH /tables/3/assigned_waiter`.
4. The host marks the table as occupied with the party of 4 by calling `PATCH /tables/3`.

# Testing results 

### Step 1: `GET /tables/`

```bash
curl -X 'GET' \
  'https://squeal.onrender.com/tables/' \
  -H 'accept: application/json' \
  -H 'access_token: <REDACTED>'
```

Response:

```json
[
  {"table_id": 1, "capacity": 2, "status": "open", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 2, "capacity": 4, "status": "open", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 3, "capacity": 4, "status": "open", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 4, "capacity": 6, "status": "open", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 5, "capacity": 2, "status": "open", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 6, "capacity": 8, "status": "open", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 7, "capacity": 6, "status": "open", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 8, "capacity": 4, "status": "open", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null}
]
```

### Step 2: `GET /employees/`

```bash
curl -X 'GET' \
  'https://squeal.onrender.com/employees/' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL'
```

Response:

```json
[
  {"employee_id": 10, "first_name": "Dylan",  "last_name": "Martin"},
  {"employee_id": 11, "first_name": "Pranav", "last_name": "Nallaperumal"},
  {"employee_id": 12, "first_name": "Danny",  "last_name": "Kullman"},
  {"employee_id": 13, "first_name": "Andy",   "last_name": "Cai"}
]
```

### Step 3: `PATCH /tables/3/assigned_waiter`

```bash
curl -X 'PATCH' \
  'https://squeal.onrender.com/tables/3/assigned_waiter' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{"assigned_waiter_id": 12}'
```

Response:

```json
{"table_id": 3, "assigned_waiter_id": 12}
```

### Step 4: `PATCH /tables/3`

```bash
curl -X 'PATCH' \
  'https://squeal.onrender.com/tables/3' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{"status": "occupied", "current_party_size": 4}'
```

Response:

```json
{"table_id": 3, "capacity": 4, "status": "occupied", "assigned_waiter_id": 12, "current_party_size": 4, "reserved_for": null}
```

---

# Example workflow 2

Jacky wants to book a table for 5. Once seated, the waiter manages their tab through the meal: drinks first, then entrées, then the final bill.

1. Jacky's reservation is created via `POST /reservations`. The system marks table 7 as `reserved` with `reserved_for = "Jacky Wang"`.
2. When the party arrives, the host calls `GET /tables/` and confirms table 7 is reserved and ready.
3. The host assigns waiter 13 (Andy) to table 7 by calling `PATCH /tables/7/assigned_waiter`.
4. The party orders drinks and an appetizer; the waiter starts the tab via `POST /tables/7/tabs`.
5. After they decide on entrées, the waiter adds them with `PATCH /tables/7/tabs/1`.
6. At the end of the night, the waiter calls `GET /tables/7/tabs/1` to retrieve the final bill (subtotal, 7.75% sales tax, total).

# Testing results

### Step 1: `POST /reservations/`

```bash
curl -X 'POST' \
  'https://squeal.onrender.com/reservations/' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_name": "Jacky Wang",
    "table_id": 7,
    "party_size": 5,
    "reservation_time": "2026-05-12-PST"
  }'
```

Response:

```json
{
  "reservation_id": 1,
  "customer_name": "Jacky Wang",
  "table_id": 7,
  "party_size": 5,
  "reservation_time": "2026-05-12-PST",
  "status": "reserved"
}
```

### Step 2: `GET /tables/`

```bash
curl -X 'GET' \
  'https://squeal.onrender.com/tables/' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL'
```

Response (table 7 now reflects the reservation):

```json
[
  {"table_id": 1, "capacity": 2, "status": "open",     "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 2, "capacity": 4, "status": "open",     "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 3, "capacity": 4, "status": "occupied", "assigned_waiter_id": 12,   "current_party_size": 4,    "reserved_for": null},
  {"table_id": 4, "capacity": 6, "status": "open",     "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 5, "capacity": 2, "status": "open",     "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 6, "capacity": 8, "status": "open",     "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null},
  {"table_id": 7, "capacity": 6, "status": "reserved", "assigned_waiter_id": null, "current_party_size": null, "reserved_for": "Jacky Wang"},
  {"table_id": 8, "capacity": 4, "status": "open",     "assigned_waiter_id": null, "current_party_size": null, "reserved_for": null}
]
```

### Step 3: `PATCH /tables/7/assigned_waiter`

```bash
curl -X 'PATCH' \
  'https://squeal.onrender.com/tables/7/assigned_waiter' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{"assigned_waiter_id": 13}'
```

Response:

```json
{"table_id": 7, "assigned_waiter_id": 13}
```

### Step 4: `POST /tables/7/tabs`

```bash
curl -X 'POST' \
  'https://squeal.onrender.com/tables/7/tabs' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{
    "items": [
      {"item_name": "Coke", "quantity": 2, "unit_price": 3.50},
      {"item_name": "Mozzarella Sticks", "quantity": 1, "unit_price": 8.99}
    ]
  }'
```

Response:

```json
{
  "tab_id": 1,
  "table_id": 7,
  "items": [
    {"item_name": "Coke", "quantity": 2, "unit_price": 3.5,  "line_total": 7.0},
    {"item_name": "Mozzarella Sticks", "quantity": 1, "unit_price": 8.99, "line_total": 8.99}
  ],
  "subtotal": 15.99
}
```

### Step 5: `PATCH /tables/7/tabs/1`

```bash
curl -X 'PATCH' \
  'https://squeal.onrender.com/tables/7/tabs/1' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{
    "items_to_add": [
      {"item_name": "Burger", "quantity": 2, "unit_price": 12.50}
    ]
  }'
```

Response:

```json
{
  "tab_id": 1,
  "table_id": 7,
  "items": [
    {"item_name": "Coke", "quantity": 2, "unit_price": 3.5,  "line_total": 7.0},
    {"item_name": "Mozzarella Sticks", "quantity": 1, "unit_price": 8.99, "line_total": 8.99},
    {"item_name": "Burger", "quantity": 2, "unit_price": 12.5, "line_total": 25.0}
  ],
  "subtotal": 40.99
}
```

### Step 6: `GET /tables/7/tabs/1`

```bash
curl -X 'GET' \
  'https://squeal.onrender.com/tables/7/tabs/1' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL'
```

Response (tax = 7.75% SLO county sales tax):

```json
{
  "tab_id": 1,
  "table_id": 7,
  "items": [
    {"item_name": "Coke", "quantity": 2, "unit_price": 3.5,  "line_total": 7.0},
    {"item_name": "Mozzarella Sticks", "quantity": 1, "unit_price": 8.99, "line_total": 8.99},
    {"item_name": "Burger", "quantity": 2, "unit_price": 12.5, "line_total": 25.0}
  ],
  "subtotal": 40.99,
  "tax": 3.18,
  "total": 44.17
}
```

---

# Example workflow 3

Jacky's party at table 7 has finished dining and is ready to leave. Before the table can be used for the next guests, the waiter confirms the final bill and the host resets the table.

1. The waiter retrieves the current tab for table 7 by calling `GET /tables/7/tabs/1`. The response shows all items ordered along with subtotal, tax, and total. The waiter confirms the bill and presents it to the guests.
2. After payment, the host updates the table record by calling `PATCH /tables/7` to mark it `dirty` and clear party/reservation info.
3. Once the table has been cleaned, the host calls `POST /tables/7/reset` to return the table to its default state, ready to seat the next party.

# Testing results

### Step 1: `GET /tables/7/tabs/1`

```bash
curl -X 'GET' \
  'https://squeal.onrender.com/tables/7/tabs/1' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL'
```

Response:

```json
{
  "tab_id": 1,
  "table_id": 7,
  "items": [
    {"item_name": "Coke",              "quantity": 2, "unit_price": 3.5,  "line_total": 7.0},
    {"item_name": "Mozzarella Sticks", "quantity": 1, "unit_price": 8.99, "line_total": 8.99},
    {"item_name": "Burger",            "quantity": 2, "unit_price": 12.5, "line_total": 25.0}
  ],
  "subtotal": 40.99,
  "tax": 3.18,
  "total": 44.17
}
```

### Step 2: `PATCH /tables/7`

```bash
curl -X 'PATCH' \
  'https://squeal.onrender.com/tables/7' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "dirty",
    "current_party_size": null,
    "reserved_for": null
  }'
```

Response:

```json
{
  "table_id": 7,
  "capacity": 6,
  "status": "dirty",
  "assigned_waiter_id": 13,
  "current_party_size": null,
  "reserved_for": null
}
```

### Step 3: `POST /tables/7/reset`

```bash
curl -X 'POST' \
  'https://squeal.onrender.com/tables/7/reset' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL'
```

Response:

```json
{
  "table_id": 7,
  "capacity": 6,
  "status": "open",
  "assigned_waiter_id": null,
  "current_party_size": null,
  "reserved_for": null
}
```
