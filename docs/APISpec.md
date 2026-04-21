# API Specification

## Overview

Below, we have the proposed REST API for a restaurant table management and tab tracking system. The API is designed to support common restaurant operations including reservations, table assignment, shift staffing, tab creation, tab updates, and table resets. 


## 1. Create Reservation

### `POST /reservations`

Creates a reservation for a specific customer, table, party size, and time.

**Example request body**
```json
{
  "customer_name": "Danny Kullman",
  "table_id": 7,
  "party_size": 5,
  "reservation_time": "2026-04-21T19:00:00-08:00"
}
```

**Example response**
```json
{
  "reservation_id": 101,
  "customer_name": "Danny Kullman",
  "table_id": 7,
  "party_size": 5,
  "reservation_time": "2026-04-21T19:00:00-08:00",
  "status": "reserved"
}
```

---

## 2. Assign Waiter to Table

### `PATCH /tables/{table_id}/assigned_waiter`

Assigns a waiter to a specific table.

**Example request**
```http
PATCH /tables/3/assigned_waiter
```

**Example request body**
```json
{
  "assigned_waiter_id": 12
}
```

**Example response**
```json
{
  "table_id": 3,
  "assigned_waiter_id": 12
}
```

---

## 3. Create Tab for a Table

### `POST /tables/{table_id}/tabs`

Creates a new tab for a table with an initial set of ordered items.

**Example request**
```http
POST /tables/3/tabs
```

**Example request body**
```json
{
  "items": [
    {
      "item_name": "Coke",
      "quantity": 2,
      "unit_price": 3.5
    },
    {
      "item_name": "Mozzarella Sticks",
      "quantity": 1,
      "unit_price": 8.99
    }
  ]
}
```

**Example response**
```json
{
  "tab_id": 55,
  "table_id": 3,
  "items": [
    {
      "item_name": "Coke",
      "quantity": 2,
      "unit_price": 3.5,
      "line_total": 7.0
    },
    {
      "item_name": "Mozzarella Sticks",
      "quantity": 1,
      "unit_price": 8.99,
      "line_total": 8.99
    }
  ],
  "subtotal": 15.99
}
```

---

## 4. Add Items to an Existing Tab

### `PATCH /tables/{table_id}/tabs/{tab_id}`

Adds additional items to an existing tab.

**Example request**
```http
PATCH /tables/3/tabs/55
```

**Example request body**
```json
{
  "items_to_add": [
    {
      "item_name": "Burger",
      "quantity": 2,
      "unit_price": 12.5
    }
  ]
}
```

**Example response**
```json
{
  "tab_id": 55,
  "table_id": 3,
  "items": [
    {
      "item_name": "Coke",
      "quantity": 2,
      "unit_price": 3.5,
      "line_total": 7.0
    },
    {
      "item_name": "Burger",
      "quantity": 2,
      "unit_price": 12.5,
      "line_total": 25.0
    }
  ],
  "subtotal": 32.0
}
```

---

## 5. Get Tab Details

### `GET /tables/{table_id}/tabs/{tab_id}`

Returns the current contents of a tab, including pricing details.

**Example request**
```http
GET /tables/3/tabs/55
```

**Example response**
```json
{
  "tab_id": 55,
  "table_id": 3,
  "items": [
    {
      "item_name": "Coke",
      "quantity": 2,
      "unit_price": 3.5,
      "line_total": 7.0
    },
    {
      "item_name": "Burger",
      "quantity": 2,
      "unit_price": 12.5,
      "line_total": 25.0
    }
  ],
  "subtotal": 32.0,
  "tax": 2.0,
  "total": 34.0
}
```

---

## 6. Get All Tables

### `GET /tables`

Returns all tables and their current status.

Fields may include:
- `table_id`
- `capacity`
- `status`
- `assigned_waiter_id`
- `current_party_size`
- `reserved_for`

**Example request**
```http
GET /tables
```

**Example response**
```json
[
  {
    "table_id": 1,
    "capacity": 2,
    "status": "open",
    "assigned_waiter_id": null,
    "current_party_size": null,
    "reserved_for": null
  },
  {
    "table_id": 7,
    "capacity": 6,
    "status": "reserved",
    "assigned_waiter_id": 8,
    "current_party_size": null,
    "reserved_for": "Lucas Pierce"
  }
]
```

---

## 7. Get Servers Working a Shift

### `GET /shifts/{shift_id}/servers`

Returns the list of servers assigned to a particular shift.

**Example request**
```http
GET /shifts/4/servers
```

**Example response**
```json
[
  {
    "staff_id": 8,
    "first_name": "Jazzy",
    "last_name": "TheGoat"
  },
  {
    "staff_id": 12,
    "first_name": "Hollow",
    "last_name": "Knight"
  }
]
```

---

## 8. Add a Server to a Shift

### `POST /shifts/{shift_id}/servers`

Adds a server to a specific shift.

**Example request**
```http
POST /shifts/4/servers
```

**Example request body**
```json
{
  "server_id": 15
}
```

**Example response**
```json
{
  "shift_id": 4,
  "server_id": 15
}
```

---

## 9. Update Table State

### `PATCH /tables/{table_id}`

Updates the state of a table, including occupancy information.

**Example request**
```http
PATCH /tables/3
```

**Example request body**
```json
{
  "status": "occupied",
  "current_party_size": 4,
  "reserved_for": null
}
```

**Example response**
```json
{
  "table_id": 3,
  "capacity": 4,
  "status": "occupied",
  "assigned_waiter_id": 12,
  "current_party_size": 4,
  "reserved_for": null
}
```

---

## 10. Reset Table

### `POST /tables/{table_id}/reset`

Resets a table back to its default open state after a party has left and cleanup is complete.

**Example request**
```http
POST /tables/3/reset
```

**Example response**
```json
{
  "table_id": 3,
  "capacity": 4,
  "status": "open",
  "assigned_waiter_id": null,
  "current_party_size": null,
  "reserved_for": null
}
```

---

