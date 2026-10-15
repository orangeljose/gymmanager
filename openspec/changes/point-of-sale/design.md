# Design: Point of Sale (Cart Checkout) + Inventory Relocation

## Technical Approach

Add a `sales_bp` blueprint (`/api/sales`) mirroring `products.py` + `PaymentService`: a `sales` collection for income, `V-YYYYMMDD-XXX` receipts via `count_firestore` (+1, timestamp fallback), and multi-item checkout with validate-all-first stock check then non-atomic write+decrement. `products.py` narrows `register_movement` to `purchase` only and its `/report` re-reads income from `sales`. Frontend adds `PointOfSalePage` (`/pos`) and relabels inventory to "Mercancía" under Administración with a "Reponer" action.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|---|---|---|---|
| Sales ledger | New `sales` collection + `sales_bp` | keep sale in `product_movements` | splits income (sales) from outflow (purchases); matches proposal |
| Receipt number | `count_firestore('sales', businessId)+1` → `V-YYYYMMDD-XXX`; fallback `V-YYYYMMDD-HHMMSSffffff` | client id; date-only | mirrors `PaymentService`; count is quota-efficient; uniqueness via ceiling check |
| Multi-item decrement | validate-all-first, then create sale + per-item `stockQty` update (non-atomic) | Firestore transaction | transactions out of scope; validate-first rejects oversell with no partial write |
| Report | two scoped queries (`sales` + `product_movements`), Python aggregation | single movement query | income now lives in `sales`; response shape preserved |
| Movement endpoint | `@require_role(ADMIN_ROLES)`, `type` fixed to `purchase` | keep in-body role check | single role now; clearer |
| Nav | Caja "Productos" → `/pos`; Administración "Mercancía" → `/products` | — | confirmed UX decision |

## Data Flow

    POST /api/sales
      → validate items (each product exists, active, in scope)
      → if any qty > stockQty → 400 (product name), no write
      → receipt = V- + count+1
      → create `sales` doc
      → for each item: update product stockQty -= qty
      → 201 {sale}

    GET /api/products/report
      → query `sales` (income) + query `product_movements` (purchase outflow)
      → aggregate by date in Python → {sales, purchases, net, daily}

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/routes/sales.py` | Create | `sales_bp` POST/GET/GET:id + receipt gen + stock guard |
| `backend/routes/__init__.py` | Modify | import + export `sales_bp` |
| `backend/app.py` | Modify | import + `register_blueprint(sales_bp)` |
| `backend/routes/products.py` | Modify | `register_movement` purchase-only; `/report` reads `sales`; remove `SALE_ROLES` |
| `backend/tests/routes/test_sales.py` | Create | checkout, oversell, receipt, list/detail, perms |
| `backend/tests/routes/test_products.py` | Modify | drop sale-movement cases; report now 2 queries |
| `frontend/src/pages/PointOfSalePage.tsx` | Create | grid + cart + checkout + receipt summary |
| `frontend/src/pages/ProductsPage.tsx` | Modify | label "Mercancía"; "Reponer" button (admin+) |
| `frontend/src/components/ProductMovementModal.tsx` | Modify | purchase-only ("Reponer") |
| `frontend/src/App.tsx` | Modify | `/pos` route (cashier+) |
| `frontend/src/components/Layout.tsx` | Modify | nav swap |
| `frontend/src/services/api.ts` | Modify | `createSale`, `getSales`, `getSale` |
| `frontend/src/types/index.ts` | Modify | `Sale`, `SaleItem`; `MovementType` → `purchase` |

## Interfaces / Contracts

```python
# sale document
{
  'id', 'receiptNumber': 'V-20261015-003', 'date': 'YYYY-MM-DD',
  'totalCents': int, 'method': PaymentModel.VALID_METHODS,
  'paymentAccountId': str|None, 'clientId': str|None, 'clientName': str|None,
  'items': [{'productId','productName','qty','unitPriceCents','subtotalCents'}],
  'businessId', 'branchId', 'registeredBy', 'registeredByName', 'createdAt'
}
```

- `POST /api/sales` body `{items, method, paymentAccountId?, clientId?, clientName?, branchId?, date?}` → 201
- `GET /api/sales?startDate&endDate&clientName&branchId&page&limit` → `{data, meta}`
- `GET /api/sales/:id` → sale detail (receipt)
- FE `MovementType` narrows to `'purchase'`.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Route | multi-item checkout 201 + per-item decrement | mock `create_document`/`update_document`; assert writes |
| Route | oversell → 400 + no write | insufficient item; assert no create/update |
| Route | receipt `V-` format + fallback | assert regex `V-\d{8}-\d{3}` |
| Route | list/detail + scope + perms | `prime_app_modules` + `make_client` fixtures (isolation-safe) |
| Unit | receipt count+1 / ceiling fallback | mirror `test_receipt_number.py` |
| Update | report split (sales vs purchases) | assert 2 queries, correct net |

## Migration / Rollout

No data migration (code-only; no production sale-movement data). Rollback: remove `sales.py`/`sales_bp`, revert `products.py`, FE routes/nav. Requires manual Firestore index `sales (businessId ASC, date ASC)`.

## Open Questions

- [ ] Keep `/products` (Mercancía) readable by all roles (per spec) vs. restrict to admin+ since it now lives under Administración? Recommend read-all + writes/Reponer admin+.
