# Peer Review Response

We are documenting our responses to the peer review feedback by four
reviewers: **Bryce Corbett** (issues 1-4), **Addie Weaver** (issues 5-8),
**Owen Sam** (issues 9-12), and **Joshua Winn** (issues 13-16).

Each suggestion falls into one of these three categories:

- **Already addressed** - the issue was fixed in a migration or commit since
  reviews were issued.
- **Not applicable** - the feedback targets code or schema that no longer exists
  (prolly about the removed `parties` feature), or describes behavior that we intended.
- **Will fix / planned** - actionable feedback we are addressing now. (This section is
  a work in progress and will be filled in as the fixes land.)

> Status: **DRAFT** - the "Already addressed" and "Not applicable" sections are complete.
> The "Will fix" section is being filled in as code changes are made.

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

| Reviewer | Feedback | Resolution |
|---|---|---|
| Addie #5.4 | `tabs.py` and `tables.py` share the `/tables` prefix | Tabs are now a top-level resource at `/tabs` with its own router prefix. |
| Addie #5.5 / Bryce code #5 | `PATCH` on a tab wiped all items instead of appending | `update_tab` in [`src/api/tabs.py`](../src/api/tabs.py) now calls `_insert_items` to append. The destructive party-tab PATCH was removed with `parties`. |
| Addie schema #2 / Owen #10.7 / Joshua schema #7 | No `status` field on tabs | Added `tabs.status` with a `CHECK (status IN ('open','paid','void'))` constraint in migration `f3a9c1d4b2e7`. |
| Addie schema #9 / Joshua schema #1 | No `GET /tables/{id}` for a single table | Added `get_table` in [`src/api/tables.py`](../src/api/tables.py). |
| Addie schema #6 / Joshua schema #2 | No way to list/view reservations | Added `GET /reservations/` (with `status` and `table_id` filters) and `GET /reservations/{id}` in [`src/api/reservations.py`](../src/api/reservations.py). DELETE/PATCH still pending. |
| Addie product #2 / Owen product / Joshua product #2 | Need a single checkout / pay-and-close operation | Added [`src/api/checkout.py`](../src/api/checkout.py): `POST /tabs/{tab_id}/checkout` atomically computes the bill, records a payment, marks the tab `paid`, and sets the table `dirty`. Uses `SELECT ... FOR UPDATE` and `Decimal` money. |
| Bryce product #1 / Joshua product #2 | Split a check | Added `POST /tabs/{tab_id}/split` in [`src/api/tabs.py`](../src/api/tabs.py), which moves line items onto a new tab on the same table. |
| Bryce schema/API #16 | No "close tab" and no "list reservations" endpoints | Both now exist (checkout + reservation listing). |
| Addie #1 / Joshua #7 / Bryce code #1 | API key printed to logs on every request | Removed the `print(...)` in [`src/api/auth.py`](../src/api/auth.py) that leaked both the caller's key and the server's secret. |
| Bryce code #2 | 401 status returned with `"Forbidden"` detail (mismatch) | Changed the `detail` to `"Unauthorized"` so the message matches the `401 UNAUTHORIZED` status code in [`src/api/auth.py`](../src/api/auth.py). |
| Addie #2 (Test #1) / Joshua #8, #9 / Bryce test #2 / Owen test wf3 | Tab items accept negative/zero quantity and negative price, producing negative subtotals/totals | Added `Field(..., gt=0)` to `quantity` and `Field(..., ge=0)` to `unit_price` on `TabItemIn` in [`src/api/tabs.py`](../src/api/tabs.py). Invalid values now return `422` before any DB write. Covers the create, update, and split paths. |
| Addie #3 / Joshua #6 (Test #1) / Bryce code #11 | `TableUpdate.status` accepts any string (`"random_status"` was stored) | Restricted `status` to `Optional[Literal["open", "occupied", "reserved", "dirty"]]` in [`src/api/tables.py`](../src/api/tables.py). Invalid statuses now return `422`. |
| Joshua schema #6 | Inconsistent table-status naming (`open` vs `available`) | The current code writes only `open`/`occupied`/`reserved`/`dirty` (verified in `seed.sql`, `seed_fake_data.py`, `reset_table`, `checkout.py`, `reservations.py`), and the new `Literal` enforces exactly that set. The lone `available` reference lives only in the historical [`docs/v1_manual_test_results.md`](v1_manual_test_results.md) log, which reflects the older v1 API and is left intact as a record. |

---

## Not applicable

### Feedback targeting the removed `parties` feature

The `parties` table and its endpoints were removed entirely, so the following are no
longer relevant:

| Reviewer | Feedback |
|---|---|
| Addie #5.6 | `create_party_tab` doesn't null-check `table_id` |
| Addie #5.10 | `delete_party` succeeds even if the party doesn't exist |
| Addie #5.11 | `get_party_tabs` returns 404 when a party has zero tabs |
| Addie schema #4 | `parties` and `reservations` not linked |
| Owen #9.1 | Party deletion fails due to FK from tabs |
| Owen #9.2, #9.3 | Unnecessary `SELECT party_id` in `partys.py` |
| Owen #10.5 | Both parties and tables can accrue tabs |
| Owen #10.9, #10.10 | `parties` is obsolete / `table_id` FK direction |
| Joshua #13.11 | `delete_party` always returns success |
| Joshua schema #8 | Two tab systems (table + party) |
| Bryce code #5, #6, #7 | Dual PATCH behavior, 404 on empty party tabs, party delete cleanup |
| Bryce schema/API #14 | Two PATCH endpoints doing opposite things |

### Feedback describing intended behavior

| Reviewer | Feedback | Why it's intended |
|---|---|---|
| Addie schema #7 / Owen #10.4 | `PATCH /assigned_waiter` should fold into `PATCH /tables/{id}`; reservation should set `current_party_size` | The dedicated waiter endpoint is intentional: it allows assigning a server atomically without touching table status or party size. |
| Addie schema #8 | `POST /tables/{id}/reset` should be a `PATCH` | `reset` is an intentional RPC-style action with no request body; it conceptually clears a table rather than partially updating it. |
| Addie schema #12 / Owen #10.5 | `tab_id` is redundant under `/tables/{id}/tabs` | Tabs are now a top-level `/tabs` resource, so this nesting concern no longer applies. |
| Owen #9.4 | `get_tables` doesn't error when no tables exist | Returning an empty list `[]` is the correct REST behavior for a collection with no members. |
| Owen #9.5 / Addie #5.8 | `tabs.total_price` is never updated | The authoritative total is computed dynamically from `tab_items`. The column is vestigial and is simply not relied upon; tab responses are always correct. |

### `food_items` is decorative by design

Reviewers **Addie schema #3**, **Owen #10.8**, **Joshua schema #4**, and
**Bryce schema #7** all noted that `food_items` exists but is never referenced by
`tab_items`. This is a **documented, deliberate design constraint**, not an oversight.
From [`docs/performance_writeup.md`](performance_writeup.md):

> "`tab_items.item_name` is just free text, meaning the items in `food_items` are
> basically decorative."

The seed script populates ~200 `food_items` rows as realistic filler for the
~1M-row performance dataset, but the API intentionally accepts free-text item names
rather than enforcing a menu foreign key. Connecting the menu (server-side price
lookup via a `food_item_id` FK) is a larger feature we have scoped as future work, not
a bug in the current milestone.

### Shifts system

**Addie schema #11**, **Joshua schema #3**, and **Bryce schema #11** noted that the
API spec references a shifts system that has no tables or endpoints. Shifts were never
implemented for this milestone. We will mark those sections of
[`docs/APISpec.md`](APISpec.md) as future work rather than building the feature now.

---

## Will fix / planned

> This section is in progress. The following actionable items have been accepted and
> are being implemented; this document will be updated with the specific resolution for
> each as the changes land.

- **Reservation guards:** reject `party_size > capacity` (400) and double-bookings of
  the same table (409). (Addie tests #2/#3, Owen #2/#3, Joshua #3/#5, Bryce tests #1/#3)
- **CORS:** add `POST` and `DELETE` to allowed methods and clean up the leftover
  `potion-exchange` origin. (Joshua #2, Bryce code #18)
- **Error handling:** replace runtime `assert` statements with proper `HTTPException`s.
  (Addie #2, Bryce code generally)
- **Performance:** batch `_insert_items` into a single statement, and remove the
  duplicate `_load_tab` call in `update_tab`. (Bryce code #16, Owen #6)
- **Reset guard:** only allow `POST /tables/{id}/reset` when the table is `dirty`.
  (Bryce code #9)

---

## Deferred (acknowledged, not in this milestone)

| Feedback | Reviewers | Reason |
|---|---|---|
| `reservation_time` back to `TIMESTAMPTZ` | All four | Valid, but a risky live-data migration; existing callers and our own test logs use free-form strings. Documented as a known limitation. |
| Reservation immediately marks table `reserved` even for future dates | Joshua #13.1/#13.12 | Known design gap; acceptable for the near-term reservation workflow. |
| `reserved_for` as FK to `reservations` | Owen #10.11, Joshua schema #9, Addie schema #5 | Major schema refactor; out of scope. |
| Item deletion / voiding from a tab | Owen #10.6, Bryce schema/API #16 | Useful; planned as a follow-up endpoint. |
| Employee roles / `is_active` / availability | Owen test, Joshua schema #12, Bryce schema #12 | Schema expansion; future work. |
| `GET /tables/available`, filtering on `GET /tables` | Addie product #1, Joshua schema #10 | Product idea; future work. |
| Wait-time / end-of-shift analytics | Joshua product #1, Bryce product #2 | Depends on shifts + timestamps; future work. |
| `ON DELETE` rules, `updated_at`, FK indexes beyond existing | Bryce schema #1/#9/#10 | Lower priority; some indexes already added in `63e7bf35c61b`. |
| Idempotency keys, per-user bearer tokens, API versioning | Bryce schema/API cross-cutting | Good practice; architectural, out of scope for this sprint. |
| Money as `Decimal`/`NUMERIC` everywhere | Addie #7, Bryce code #12 | Checkout already uses `Decimal`; converting all float paths is deferred. Penny-level drift is acknowledged in the performance writeup. |
| Configurable tax rate | Bryce code #13 | Minor; deferred. |
