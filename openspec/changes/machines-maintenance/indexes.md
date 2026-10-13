# Manual Firebase Composite Indexes — machines-maintenance

The `machines` collection is queried by a **single equality on `businessId`** only
(category/status/branchId/search are filtered in Python), so it needs **no
composite index** — the automatic single-field index suffices.

Two composite indexes are required on **`machine_maintenance`** (create manually
in Firebase console → Firestore → Indexes → Composite):

| Collection | Fields | Serves |
|------------|--------|--------|
| `machine_maintenance` | `businessId` ASC, `machineId` ASC | `GET /api/machines/<id>/maintenance` (per-machine history) |
| `machine_maintenance` | `businessId` ASC, `date` DESC | `GET /api/machines/summary` (recent repairs, `limit` 5) |

## Notes

- The `(businessId, machineId)` index covers the two-equality filter in the
  history endpoint. History ordering (`date` DESC) is done in Python to avoid a
  third field in the index.
- The `(businessId, date)` index is what the summary's bounded query
  (`order_by=date DESC, limit=5`) relies on.
- **NOT needed**: the proposal's `machines (businessId, category)` and
  `machines (businessId, status)` — those filters never reach Firestore.
- If an index is missing, the API returns an actionable 500 via
  `_index_error_response` (see `backend/routes/machines.py`).
