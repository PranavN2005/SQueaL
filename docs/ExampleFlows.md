# Example Flows

## 1. Host Seats a Walk-In Party

Party of 4 walks in without a reservation. The hose needs to find an available table that fits them.

First the host checks what tables are available by calling `GET /tables`. The host sees that table 7 (capacity 6) and table 3 (capacity 4) both have open status. The host picks table 3 as the closest fit for 4 guests.

The host then checks who’s working on todays shift (shift 4) by calling `GET shifts/4/servers`. She sees that waiter 12 is assigned to the section including table 3.

The host assigns waiter 12 to table 3 by calling `PATCH /tables/3/assigned_waiter`

Finally, the table is updated by the host to reflect its state by calling `PATCH /tables/3`

## 2. Jacky tries to book a table for 5 tomorrow at 7pm but the restaurant is fully booked at that specific time, prompting him to reserve again.

Jacky decides to book the table for 5 tomorrow through:

- start by going to `POST/reservations`
- host will go to `GET/tables` to see if there is adequate space for tomorrow
- then their table will be assigned a waiter through `PATCH /tables/{table_id}/assigned_waiter`
- when they seat, they order drinks to start off, and the waiter uses `POST /tables/{table_id}/tabs` to start their tab
- after they finalize their entrees, the waiter adds onto their tab with `PATCH /tables/{table_id}/tabs/{tab_id}`
- at the end of the night, they call for the check and the waiter calls `GET /tables/{table_id}/tabs/{tab_id}`which returns the full tab of everything they had tonight

## 3. Closing out a table after guests leave

- A party of 4 has finished dining at table 3 and is ready to leave. Before the table can be used for the next guests, the waiter and host need to confirm the final bill and reset the table back to open status.
- First, the waiter retrieves the current tab for table 3 by calling
  1. `GET /tables/3/tabs/55`
- The response shows all items ordered during the meal, along with the subtotal, tax, and total. The waiter confirms that the final total is correct and presents the bill to the guests.
- After payment is completed, the host updates the table record by calling
  1. `PATCH /tables/3` with the below body:

```http
PATCH /tables/3
{
  "status": "dirty",
  "current_party_size": null,
  "reserved_for": null
}
```

- The table’s status is temporarily updated so the system no longer shows it as actively occupied.
- Once the table has been cleaned and is ready for the next party, the host resets it completely by calling
  1. `POST /tables/3/reset`
- The response returns the table to its default state, with status ‘open’, no assigned waiter and no current party info. Ready to seat the next party.
