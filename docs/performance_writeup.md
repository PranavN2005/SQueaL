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
| `PATCH /tables/{table_id}/assigned_waiter`------| 5.1 |
| `POST /reservations/`---------------------------| 3.9 |
| `PATCH /tables/{table_id}`----------------------| 3.1 |
| `GET /tables/{table_id}/tabs/{tab_id}`----------| 2.4 |
| `GET /employees/`-------------------------------| 2.4 |
| `GET /tables/`----------------------------------| 2.3 |

The slowest endpoint by a wide margin is **`PATCH /tables/{table_id}/assigned_waiter`** with ~5.1 ms. 

## Performance Tuning
The slowest endpoint updates a table’s assigned waiter by `table_id`.
```
EXPLAIN ANALYZE
UPDATE tables
SET assigned_waiter_id = 3
WHERE table_id = 3
```

**Before:**
```
Update on tables  (cost=0.00..1.62 rows=0 width=0) (actual time=1.184..1.185 rows=0 loops=1)
  Buffers: shared hit=13 dirtied=1
  -> Seq Scan on tables  (cost=0.00..1.62 rows=1 width=10)
        Filter: (table_id = 3)
        Rows Removed by Filter: 49
        Buffers: shared hit=1

Planning Time: 2.762 ms
Execution Time: 4.289 ms
```

The query used a sequential scan on tables, meaning Postgres checked every row to find the one where table_id = 3. It removed 49 rows by the filter, so it scanned the whole table instead of jumping directly to the matching row.

```CREATE INDEX idx_tables_table_id ON tables(table_id)```
This index should allow Postgres to find a table by table_id faster, especially more as the tables table grows

**After:**
```
Update on tables  (cost=0.00..1.62 rows=0 width=0) (actual time=0.07... rows=0 loops=1)
  Buffers: shared hit=4
  -> Seq Scan on tables  (cost=0.00..1.62 rows=1 width=10)
        Filter: (table_id = 3)
        Rows Removed by Filter: 49
        Buffers: shared hit=1

Planning:
Buffers: shared hit=16 read=1
Planning Time: 2.741 ms
Execution Time: 0.140 ms
```
Postgres still uses sequential scan because the tale is small at 50 rows so index is appropriate for this query pattern.
The execution time decreased from 4.289 ms to 0.140 ms, indicating a significant performance improvement. The endpoint is now fast enough for the expected workload.