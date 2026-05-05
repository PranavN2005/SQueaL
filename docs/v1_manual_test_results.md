# Example Workflow

## 1. Host Seats a Walk-In Party

A party of 4 walks in without a reservation. The host needs to find an
available table that fits them.

First the host checks what tables are available by calling `GET /tables`. The
host sees that table 7 (capacity 6) and table 3 (capacity 4) both have
`available` status. The host picks table 3 as the closest fit for 4 guests.

The host then checks who is on staff by calling `GET /employees/`. She sees
that employee 12 (Danny Kullman) is available to take the table.

The host assigns Danny to table 3 by calling
`PATCH /tables/3/assigned_waiter`.

Finally, the table is updated by the host to reflect its new state by calling
`PATCH /tables/3` with `status: occupied` and `current_party_size: 4`.

---

# Testing Results

## Step 1 — Get all tables

```
curl -X 'GET' \
  'https://squeal.onrender.com/tables/' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL'
```

**Response:**

```json
[
  {"table_id": 1, "capacity": 2, "status": "available", "assigned_waiter_id": null, "current_party_size": null},
  {"table_id": 2, "capacity": 4, "status": "occupied",  "assigned_waiter_id": 10,   "current_party_size": 3},
  {"table_id": 3, "capacity": 4, "status": "available", "assigned_waiter_id": null, "current_party_size": null},
  {"table_id": 4, "capacity": 6, "status": "occupied",  "assigned_waiter_id": 11,   "current_party_size": 5},
  {"table_id": 5, "capacity": 2, "status": "available", "assigned_waiter_id": null, "current_party_size": null},
  {"table_id": 6, "capacity": 8, "status": "available", "assigned_waiter_id": null, "current_party_size": null},
  {"table_id": 7, "capacity": 6, "status": "available", "assigned_waiter_id": null, "current_party_size": null},
  {"table_id": 8, "capacity": 4, "status": "available", "assigned_waiter_id": null, "current_party_size": null}
]
```

The host identifies table 3 (capacity 4, status `available`) as the best fit
for the party of 4.

---

## Step 2 — Get available employees (staff lookup)

```
curl -X 'GET' \
  'https://squeal.onrender.com/employees/' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL'
```

**Response:**

```json
[
  {"employee_id": 10, "first_name": "Dylan",  "last_name": "Martin"},
  {"employee_id": 11, "first_name": "Pranav", "last_name": "Nallaperumal"},
  {"employee_id": 12, "first_name": "Danny",  "last_name": "Kullman"},
  {"employee_id": 13, "first_name": "Andy",   "last_name": "Cai"}
]
```

The host selects employee 12 (Danny Kullman) to cover table 3.

---

## Step 3 — Assign waiter to table 3

```
curl -X 'PATCH' \
  'https://squeal.onrender.com/tables/3/assigned_waiter' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{"assigned_waiter_id": 12}'
```

**Response:**

```json
{
  "table_id": 3,
  "assigned_waiter_id": 12
}
```

Danny Kullman is now assigned to table 3.

---

## Step 4 — Update table 3 to occupied with party size 4

```
curl -X 'PATCH' \
  'https://squeal.onrender.com/tables/3' \
  -H 'accept: application/json' \
  -H 'access_token: DontSQueaL' \
  -H 'Content-Type: application/json' \
  -d '{"status": "occupied", "current_party_size": 4}'
```

**Response:**

```json
{
  "table_id": 3,
  "capacity": 4,
  "status": "occupied",
  "assigned_waiter_id": 12,
  "current_party_size": 4
}
```

Table 3 is now marked as occupied, assigned to Danny Kullman, and seats a
party of 4. The walk-in seating flow is complete.
