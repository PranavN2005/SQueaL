# Performance Writeup

## Fake Data Modeling

The script that generates all of this is [`scripts/seed_fake_data.py`](../scripts/seed_fake_data.py). It loads about a million rows total. You can run it with `uv run python scripts/seed_fake_data.py` against the local docker postgres. It'll wipe everything first, then refill. So it's safe to re-run.

SQueaL models one restaurant, so the scenario we landed on is: one busy restaurant, three years of operating history, nothing archived. That puts most of the row count into the historical tables and lets the fixed tables stay small.

Here's the breakdown:

| Table | Rows | Why |
|---|---:|---|
| `employees` | 40 | A 50-table restaurant probably has 15 to 20 servers active at once, but hospitality turnover is brutal, so 40 over three years felt accurate. |
| `food_items` | 200 | The menu evolves and we don't remove old items. Lots of dead specials after 3 years. |
| `tables` | 50 | Bounded by the floor plan. |
| `reservations` | 80,000 | About 73 per day. |
| `parties` | 110,000 | A little higher than reservations because of walk-ins. About 100 a day, which seems realistic. |
| `tabs` | 100,000 | Roughly one tab per seated party. Adjusted to make the math fit but this could show people walking out before ordering or maybe reservation no shows. |
| `tab_items` | ~600,000 | Each tab gets between 3 and 9 items, picked at random. |
| `payments` | ~88,000 | One row per `paid` tab. Roughly 88% of tabs end up paid, the rest are `open` or `void`. |
| `tab_splits` | 10,000 | 10% of tabs get split among multiple customers. |
| `tab_split_payers` | ~30,000 | Each split has between 2 and 4 payers. |
| **Total** | **~1,020,000** | |

A few things about the script:

- Tab totals are random between $15 and $150. Tip is between 10% and 25%. Tax is hardcoded at 8.5% (which is the tax in Cal Poly's zip).
- Item prices are random between $3 and $30.
- `tab_items.item_name` is just free text, meaning the items in `food_items` are basically decorative.
- Money is stored as plain Python floats with `round(x, 2)`. There's going to be a small amount of drift in the totals at the penny level. We are not running a bank.

Total runtime on a recent run was about 47 seconds. Most of that is the tab_items batch (about 600k rows) and the faker calls for item names. Pretty bearable for a one-time load.

## Performance results of hitting endpoints

Each endpoint was hit against the local DB (~1M rows) and timed with curl's `time_total`:

| Endpoint | Time (ms) |
|---|---:|
| `GET /parties/{party_id}/tabs`------------------| 62.6 |
| `POST /parties/`--------------------------------| 5.3 |
| `PATCH /tables/{table_id}/assigned_waiter`------| 5.1 |
| `POST /reservations/`---------------------------| 3.9 |
| `POST /parties/{party_id}/tabs`-----------------| 3.8 |
| `PATCH /tables/{table_id}`----------------------| 3.1 |
| `GET /parties/{party_id}/`----------------------| 3.0 |
| `GET /tables/{table_id}/tabs/{tab_id}`----------| 2.4 |
| `GET /employees/`-------------------------------| 2.4 |
| `GET /tables/`----------------------------------| 2.3 |

The slowest endpoint by a wide margin is **`GET /parties/{party_id}/tabs`** with ~62 ms. Everything else hits small tables or looks up by primary key (already indexed), so they stay in the 2-5 ms range.

## Performance Tuning
`GET /parties/{party_id}/tabs` joins `tabs` to `tab_items` and filters by `party_id`. Running EXPLAIN ANALYZE:

**Before:**
```
Sort  (cost=14474.22..14474.25 rows=12 width=49) (actual time=60.027...)
  Sort Key: tabs.tab_id
  -> Hash Right Join  (cost=2167.03..14474.01 rows=12 width=49)
       Hash Cond: (tab_items.tab_id = tabs.tab_id)
       -> Seq Scan on tab_items  (cost=0.00..10734.43 rows=599043)
       -> Hash  (cost=2167.00..2167.00 rows=2 width=24)
            -> Seq Scan on tabs  (cost=0.00..2167.00 rows=2)
                 Filter: (party_id = 1)
                 Rows Removed by Filter: 99998
            
Planning Time: 1.710 ms
Execution Time: 61.265 ms
```

The problem is that it performs two full table scans. tabs scans all 100k rows and throws away 99,998 to find the 2 matching party_id, and tab_items scans all 599k rows for the join. Neither tabs.party_id nor tab_items.tab_id is indexed, so Postgres has no choice but to read every row.

```CREATE INDEX idx_tabs_party_id ON tabs (party_id);```
idx_tabs_party_id lets Postgres jump straight to one party's tabs instead of scanning 100k. 

```CREATE INDEX idx_tab_items_tab_id ON tab_items (tab_id);```
idx_tab_items_tab_id lets the join look up items by tab_id instead of scanning 599k.

**After:**
```
Sort  (cost=29.45..29.48 rows=12 width=49) (actual time=0.529..0.532)
  Sort Key: tabs.tab_id
  -> Nested Loop Left Join  (cost=4.73..29.23 rows=12 width=49)
       -> Bitmap Heap Scan on tabs  (cost=4.31..12.05 rows=2)
            Recheck Cond: (party_id = 1)`
            -> Bitmap Index Scan on idx_tabs_party_id
                 Index Cond: (party_id = 1)
       -> Index Scan using idx_tab_items_tab_id on tab_items
            Index Cond: (tab_id = tabs.tab_id)

Planning Time: 2.081 ms
Execution Time: 0.683 ms
```

Both sequential scans became index scans. Execution dropped from 61.3 ms to 0.68 ms. The "Rows Removed by Filter: 99998" line is gone because Postgres  uses the index to go straight to the matching party's tabs instead of reading the whole table. 