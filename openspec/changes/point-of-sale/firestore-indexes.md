# Firestore Indexes — point-of-sale

La colección `sales` es nueva y empieza vacía (código aditivo, sin migración de datos).

## Required composite index (manual)

| Collection | Fields | Order | Query |
|---|---|---|---|
| `sales` | `businessId` ASC, `date` ASC | Composite | Listado de ventas scoped por negocio ordenado por fecha |

Créalo en la consola de Firebase (Firestore > Índices) o vía `firebase firestore:indexes`.

El backend aplica SOLO la igualdad de `businessId` en Firestore y resuelve los
filtros de rango (`startDate`/`endDate`), `branchId`, búsqueda por `clientName`
y el orden `date` DESC en Python (volumen bajo/medio de ventas por negocio), por
lo que el índice compuesto no es estrictamente necesario para el flujo actual.
Se documenta de todos modos para el orden server-side futuro y para que
`_index_error_response` (`backend/routes/sales.py`) tenga un mensaje accionable.

## Automatic single-field indexes

| Collection | Field | Note |
|---|---|---|
| `sales` | `businessId` | Automatic single-field index |
| `sales` | `date` | Automatic single-field index (equality/range básico) |

## Rollback

Eliminar `backend/routes/sales.py`, desregistrar `sales_bp` en `routes/__init__.py`
y `app.py`, y revertir el frontend (POS, nav, types, api). La colección `sales`
puede quedar en su lugar o eliminarse; no muta ninguna colección existente.
