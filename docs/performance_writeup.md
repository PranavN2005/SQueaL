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



## Performance Tuning


