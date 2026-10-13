# Firestore Indexes — cash-expenses

## Required composite index

The `GET /api/expenses` and `GET /api/expenses/summary` endpoints query the
`expenses` collection with an equality filter on `businessId` and sort/range on
`date`. Firestore requires a composite index for this combination.

| Collection | Fields | Order |
|------------|--------|-------|
| `expenses` | `businessId` ASC, `date` ASC | Ascending / Ascending |

## Manual creation (Spark plan)

1. Open the Firebase Console → **Firestore Database** → **Indexes**.
2. Create a **composite** index:
   - Collection ID: `expenses`
   - Fields: `businessId` (Ascending), `date` (Ascending)
   - Query scope: Collection
3. Wait for the index to finish building before exercising the endpoints.

If the index is missing, the API returns a `500` with an actionable message
(via `_index_error_response`) pointing back to this document.

## Notes

- The API applies only the `businessId` equality filter in Firestore; all other
  filters (`branchId`, `category`, date range, `search`) and the summary grouping
  run in Python (low volume). No further composite indexes are required.
- Rollback: drop the index (optional) once `routes/expenses.py` is removed.
