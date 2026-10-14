# Firestore Indexes — product-inventory

Phase 2 is additive: `products` and `product_movements` start empty.

## Required composite index (manual)

| Collection | Fields | Order | Query |
|---|---|---|---|
| `product_movements` | `businessId` ASC, `date` ASC | Composite | Movement history + summary windows scoped by business |

Create it in the Firebase console (Firestore > Índices) or via `firebase firestore:indexes`.
The backend surfaces a missing index with an actionable 500 through `_index_error_response`
(see `backend/routes/products.py`).

## Automatic single-field indexes

| Collection | Field | Note |
|---|---|---|
| `products` | `businessId` | Automatic single-field index |
| `product_movements` | `productId` | Automatic single-field index |

The list/summary endpoints apply **only** a `businessId` equality filter in Firestore;
`category`, `lowStock`, `search` and `branchId` are filtered in Python (10–50 docs/business),
so no composite index is required on `products`.

## Rollback

Remove `backend/routes/products.py`, unregister the blueprint in `routes/__init__.py` and
`app.py`, and revert the frontend pages/api/nav/routes. Collections can be left in place or
deleted; no existing collection mutates.
