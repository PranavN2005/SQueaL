# Peer Review Response

We are documenting our responses to the peer review feedback by four
reviewers: **Bryce Corbett** (issues 1-4), **Addie Weaver** (issues 5-8),
**Owen Sam** (issues 9-12), and **Joshua Winn** (issues 13-16).

Each suggestion falls into one of these categories:

- **Addressed** - the issue was fixed, either in an earlier migration/commit
or as part of this peer-review response.
- **Not applicable** - the feedback targets code or schema that no longer exists
(mostly the removed `parties` feature), or describes behavior that we intended to have.
- **Deferred** - acknowledged feedback we consciously chose not to do this milestone,
with reasons.

---

## Major changes that resolved feedback in bulk

Two structural changes landed after the reviews and account for a large share of the
feedback:

1. **Removal of the `parties` feature** (migration `9d2a2f8a4d1e_remove_parties_and_splits`).
  Reviewers identified something that was on our list of things to address: that `parties` and `tables` were two parallel,
   half-completed ways to own a tab. We chose to stick with the model where a table was considered a party and dropped
   `parties` entirely, refactored out the party-specific tab endpoints.
2. **Tab lifecycle + payments** (migration `f3a9c1d4b2e7_v4_tab_status_payments_splits`).
  Added `tabs.status` (`open`/`paid`/`void`) with a check constraint, a `closed_at`
   timestamp, and a `payments` table. This enabled the checkout endpoint and resolved
   every "tabs have no open/closed state" comment.

---

## Already addressed


| Reviewer/Issue                                                     | Feedback                                                                                        | Resolution                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Addie #5.4                                                         | `tabs.py` and `tables.py` share the `/tables` prefix                                            | Tabs are now a top-level resource at `/tabs` with its own router prefix.                                                                                                                                                                                                                                                                                                                                          |
| Addie #5.5 / Bryce code #5                                         | `PATCH` on a tab wiped all items instead of appending                                           | `update_tab` in `[src/api/tabs.py](../src/api/tabs.py)` now calls `_insert_items` to append. The destructive party-tab PATCH was removed with `parties`.                                                                                                                                                                                                                                                          |
| Addie schema #2 / Owen #10.7 / Joshua schema #7                    | No `status` field on tabs                                                                       | Added `tabs.status` with a `CHECK (status IN ('open','paid','void'))` constraint in migration `f3a9c1d4b2e7`.                                                                                                                                                                                                                                                                                                     |
| Addie schema #9 / Joshua schema #1                                 | No `GET /tables/{id}` for a single table                                                        | Added `get_table` in `[src/api/tables.py](../src/api/tables.py)`.                                                                                                                                                                                                                                                                                                                                                 |
| Addie schema #6 / Joshua schema #2                                 | No way to list/view reservations                                                                | Added `GET /reservations/` (with `status` and `table_id` filters) and `GET /reservations/{id}` in `[src/api/reservations.py](../src/api/reservations.py)`. DELETE/PATCH still pending.                                                                                                                                                                                                                            |
| Addie product #2 / Owen product / Joshua product #2                | Need a single checkout / pay-and-close operation                                                | Added `[src/api/checkout.py](../src/api/checkout.py)`: `POST /tabs/{tab_id}/checkout` atomically computes the bill, records a payment, marks the tab `paid`, and sets the table `dirty`. Uses `SELECT ... FOR UPDATE` and `Decimal` money.                                                                                                                                                                        |
| Bryce product #1 / Joshua product #2                               | Split a check                                                                                   | Added `POST /tabs/{tab_id}/split` in `[src/api/tabs.py](../src/api/tabs.py)`, which moves line items onto a new tab on the same table.                                                                                                                                                                                                                                                                            |
| Bryce schema/API #16                                               | No "close tab" and no "list reservations" endpoints                                             | Both now exist (checkout + reservation listing).                                                                                                                                                                                                                                                                                                                                                                  |
| Addie #1 / Joshua #7 / Bryce code #1                               | API key printed to logs on every request                                                        | Removed the `print(...)` in `[src/api/auth.py](../src/api/auth.py)` that leaked both the caller's key and the server's secret.                                                                                                                                                                                                                                                                                    |
| Bryce code #2                                                      | 401 status returned with `"Forbidden"` detail (mismatch)                                        | Changed the `detail` to `"Unauthorized"` so the message matches the `401 UNAUTHORIZED` status code in `[src/api/auth.py](../src/api/auth.py)`.                                                                                                                                                                                                                                                                    |
| Addie #2 (Test #1) / Joshua #8, #9 / Bryce test #2 / Owen test wf3 | Tab items accept negative/zero quantity and negative price, producing negative subtotals/totals | Added `Field(..., gt=0)` to `quantity` and `Field(..., ge=0)` to `unit_price` on `TabItemIn` in `[src/api/tabs.py](../src/api/tabs.py)`. Invalid values now return `422` before any DB write. Covers the create, update, and split paths.                                                                                                                                                                         |
| Addie #3 / Joshua #6 (Test #1) / Bryce code #11                    | `TableUpdate.status` accepts any string (`"random_status"` was stored)                          | Restricted `status` to `Optional[Literal["open", "occupied", "reserved", "dirty"]]` in `[src/api/tables.py](../src/api/tables.py)`. Invalid statuses now return `422`.                                                                                                                                                                                                                                            |
| Joshua schema #6                                                   | Inconsistent table-status naming (`open` vs `available`)                                        | The current code writes only `open`/`occupied`/`reserved`/`dirty` (verified in `seed.sql`, `seed_fake_data.py`, `reset_table`, `checkout.py`, `reservations.py`), and the new `Literal` enforces exactly that set. The lone `available` reference lives only in the historical `[docs/v1_manual_test_results.md](v1_manual_test_results.md)` log, which reflects the older v1 API and is left intact as a record. |
| Addie Test #2 / Owen #3 / Joshua #3 / Bryce Test #1                | Reservation accepts `party_size` greater than table capacity                                    | `create_reservation` in `[src/api/reservations.py](../src/api/reservations.py)` now fetches the table's `capacity` and returns `400` when `party_size > capacity`. Exact-fit parties are allowed, consistent with the existing `PATCH /tables/{id}` check.                                                                                                                                                        |
| Addie Test #3 / Owen #2 / Joshua #5 / Bryce Test #3                | Same table can be double-booked for the same time                                               | `create_reservation` now rejects with `409` when an active (`status = 'reserved'`) reservation already exists for the same `table_id` and `reservation_time`. (Match is exact-string on `reservation_time` pending the deferred `TIMESTAMPTZ` migration.)                                                                                                                                                         |
| Joshua #2 / Bryce code #18                                         | CORS blocks POST/DELETE; leftover `potion-exchange` origin                                      | `[src/api/server.py](../src/api/server.py)` now allows `GET, POST, PATCH, DELETE, OPTIONS`, replaces the leftover origin with `["*"]`, and sets `allow_credentials=False` (the API uses header-token auth, not cookies, so a wildcard origin is valid).                                                                                                                                                           |
| Addie #2 / Bryce code (general)                                    | `assert` used for runtime error handling (silently stripped under `python -O`)                  | Replaced all six `assert ... is not None` statements in `[src/api/tabs.py](../src/api/tabs.py)` and `[src/api/tables.py](../src/api/tables.py)` with explicit `raise HTTPException(status_code=500, detail="Internal error")` guards.                                                                                                                                                                             |
| Bryce code #16                                                     | `_insert_items` inserted one row per round-trip                                                 | `[src/api/tabs.py](../src/api/tabs.py)` now passes a list of param dicts to a single `conn.execute`, batching all line items into one statement (an empty list is short-circuited).                                                                                                                                                                                                                               |
| Owen #6                                                            | `update_tab` called `_load_tab` twice (the first full load was discarded)                       | The pre-insert existence check is now a cheap `SELECT 1 FROM tabs`; the full `_load_tab` (items + subtotal) runs only once, after the insert, in `[src/api/tabs.py](../src/api/tabs.py)`.                                                                                                                                                                                                                         |
| Bryce code #9                                                      | `POST /tables/{id}/reset` worked on any table, even an active one                               | `reset_table` in `[src/api/tables.py](../src/api/tables.py)` now returns `409` when the table is `occupied`, protecting an actively dining table. Resetting `dirty`/`open`/`reserved` tables (the normal close-out and cleanup paths) still works.                                                                                                                                                                |
| Owen #10.6 / Bryce schema #16                                      | No way to delete an item from a tab                                                             | Added `DELETE /tabs/{tab_id}/items/{tab_item_id}` in `[src/api/tabs.py](../src/api/tabs.py)`. Returns `404` if the tab or item doesn't exist (or the item belongs to a different tab). Returns the updated tab with recalculated subtotal on success.                                                                                                                                                             |
| Addie schema #6 (partial) / Joshua #14.2 (partial)                 | No way to cancel a reservation                                                                  | Added `DELETE /reservations/{reservation_id}` in `[src/api/reservations.py](../src/api/reservations.py)`. Sets the reservation to `cancelled`, and if the table is still `reserved` under that customer's name, resets it to `open`. Returns `404` for unknown reservations and `409` if already cancelled.                                                                                                       |
| Addie product #1 / Joshua schema #10 | No way to find available tables by party size; `GET /tables` always returns everything | Added `GET /tables/available?party_size=N` in [`src/api/tables.py`](../src/api/tables.py). Returns only `open` tables with `capacity >= party_size`, sorted closest fit first, each labelled `"exact"` or `"oversized"`, with a total count. Defaults to `party_size=1` if omitted. |


---

## Not applicable

### Feedback targeting the removed `parties` feature

The `parties` table and its endpoints were removed entirely, so the following are no
longer relevant:


| Reviewer              | Feedback                                                           |
| --------------------- | ------------------------------------------------------------------ |
| Addie #5.6            | `create_party_tab` doesn't null-check `table_id`                   |
| Addie #5.10           | `delete_party` succeeds even if the party doesn't exist            |
| Addie #5.11           | `get_party_tabs` returns 404 when a party has zero tabs            |
| Addie schema #4       | `parties` and `reservations` not linked                            |
| Owen #9.1             | Party deletion fails due to FK from tabs                           |
| Owen #9.2, #9.3       | Unnecessary `SELECT party_id` in `partys.py`                       |
| Owen #10.5            | Both parties and tables can accrue tabs                            |
| Owen #10.9, #10.10    | `parties` is obsolete / `table_id` FK direction                    |
| Joshua #13.11         | `delete_party` always returns success                              |
| Joshua schema #8      | Two tab systems (table + party)                                    |
| Bryce code #5, #6, #7 | Dual PATCH behavior, 404 on empty party tabs, party delete cleanup |
| Bryce schema/API #14  | Two PATCH endpoints doing opposite things                          |


### Feedback describing intended behavior


| Reviewer                      | Feedback                                                                                                    | Why it's intended                                                                                                                                          |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Addie schema #7 / Owen #10.4  | `PATCH /assigned_waiter` should fold into `PATCH /tables/{id}`; reservation should set `current_party_size` | The dedicated waiter endpoint is intentional: it allows assigning a server atomically without touching table status or party size.                         |
| Addie schema #8               | `POST /tables/{id}/reset` should be a `PATCH`                                                               | `reset` is an intentional RPC-style action with no request body; it conceptually clears a table rather than partially updating it.                         |
| Addie schema #12 / Owen #10.5 | `tab_id` is redundant under `/tables/{id}/tabs`                                                             | Tabs are now a top-level `/tabs` resource, so this nesting concern no longer applies.                                                                      |
| Owen #9.4                     | `get_tables` doesn't error when no tables exist                                                             | We figured that returning an empty list `[]` is the correct RESTful behavior for a collection with no members.                                             |
| Owen #9.5 / Addie #5.8        | `tabs.total_price` is never updated                                                                         | The authoritative total is computed dynamically from `tab_items`. The column is vestigial and is simply not relied upon; tab responses are always correct. |


### `food_items` is decorative by design

Reviewers **Addie schema #3**, **Owen #10.8**, **Joshua schema #4**, and
**Bryce schema #7** all noted that `food_items` exists but is never referenced by
`tab_items`. This is a deliberate feature

 From `[docs/performance_writeup.md](performance_writeup.md)`:

> "`tab_items.item_name` is just free text, meaning the items in `food_items` are
> basically decorative."

The seed script populates ~200 `food_items` rows as realistic filler for the
~1M-row performance dataset, but the API intentionally accepts free-text item names
rather than enforcing a menu foreign key. Connecting the menu (server-side price
lookup via a `food_item_id` FK) is a larger feature we have scoped as future work, not
a bug in the current milestone.

### Shifts system

**Addie schema #11**, **Joshua schema #3**, and **Bryce schema #11** noted that the API spec references a shifts system that has no tables or endpoints. Shifts were never implemented over this quarter, since that would introduce a larger degree of complexity to our existing API's and necessitate the need for at least 2 new ones. We will mark those sections of `[docs/APISpec.md](APISpec.md)` as future work rather than building the feature now.

---

The remaining items we consciously
chose not to do this quarter are in **Deferred** below.

---

## Deferred


| Feedback                                                             | Reviewers                                      | Reason                                                                                                                                  |
| -------------------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `reservation_time` back to `TIMESTAMPTZ`                             | All four                                       | Valid, but a risky live-data migration; existing callers and our own test logs use free-form strings. Documented as a known limitation. |
| Reservation cancel/update (PATCH)                                    | Addie schema #6, Joshua #14.2                  | `DELETE` (cancel) is now implemented. `PATCH` (update time/size) remains out of scope.                                                  |
| Reservation immediately marks table `reserved` even for future dates | Joshua #13.1/#13.12                            | Known design gap; acceptable for the near-term reservation workflow.                                                                    |
| `reserved_for` as FK to `reservations`                               | Owen #10.11, Joshua schema #9, Addie schema #5 | Major schema refactor; out of scope.                                                                                                    |
| Employee roles / `is_active` / availability                          | Owen test, Joshua schema #12, Bryce schema #12 | Schema expansion; future work.                                                                                                          |
| Wait-time / end-of-shift analytics                                   | Joshua product #1, Bryce product #2            | would require shifts + timestamps; future work.                                                                                         |
| `ON DELETE` rules, `updated_at`, FK indexes beyond existing          | Bryce schema #1/#9/#10                         | Lower priority; some indexes already added in `63e7bf35c61b`.                                                                           |
| Idempotency keys, per-user bearer tokens, API versioning             | Bryce schema/API cross-cutting                 | Good practice; architectural, out of scope for this sprint seems like an LLM's suggestion                                               |
| Money as `Decimal`/`NUMERIC` everywhere                              | Addie #7, Bryce code #12                       | Checkout already uses `Decimal`; converting all float paths is deferred. Penny-level drift is acknowledged in the performance writeup.  |
| Configurable tax rate                                                | Bryce code #13                                 | Minor; deferred.                                                                                                                        |


