# GymManager API Specification

## 📋 Información General

| Propiedad | Valor |
|-----------|-------|
| **Base URL** (desarrollo) | `http://localhost:5000/api` |
| **Base URL** (producción) | `https://api.gymmanager.com/api` |
| **Formato** | JSON |
| **Autenticación** | Bearer Token (JWT de Firebase) |
| **Versión** | 1.0.0 |

### Headers requeridos

```http
Authorization: Bearer <firebase_token>
Content-Type: application/json

Formato de respuesta estándar
json
{
  "success": true,
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
Formato de error
json
{
  "success": false,
  "error": {
    "code": 400,
    "message": "Descripción del error"
  }
}
Códigos de estado HTTP
Código	Significado
200	OK
201	Creado
400	Error de validación
401	No autenticado
403	No autorizado (rol incorrecto)
404	Recurso no encontrado
429	Demasiadas peticiones
500	Error interno
🔐 Autenticación
POST /auth/verify
Verifica un token de Firebase y retorna información del usuario.

Headers: Ninguno especial

Request Body:

json
{
  "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
}
Response (200):

json
{
  "success": true,
  "data": {
    "uid": "abc123def456",
    "email": "admin@gym.com",
    "name": "Admin Principal",
    "role": "super_admin",
    "businessId": "gimnasio-central"
  }
}
Errors:

401: Token inválido o expirado

🏢 Negocios y Sedes
GET /businesses
Lista todos los negocios a los que el usuario tiene acceso.

Headers: Authorization required

Query Parameters: Ninguno

Response (200):

json
{
  "success": true,
  "data": [
    {
      "id": "gimnasio-central",
      "name": "Mi Gimnasio Central",
      "rubro": "gym",
      "logo": "https://storage.googleapis.com/...",
      "createdAt": "2026-01-15T10:00:00Z"
    }
  ]
}
GET /branches/:businessId
Lista las sedes de un negocio.

URL Parameters:

Parámetro	Tipo	Descripción
businessId	string	ID del negocio
Response (200):

json
{
  "success": true,
  "data": [
    {
      "id": "sede-norte",
      "name": "Sede Norte",
      "address": "Av. Principal 123",
      "phone": "+1234567890",
      "isActive": true
    }
  ]
}
POST /branches
Crea una nueva sede. (Requiere super_admin o branch_admin)

Request Body:

json
{
  "name": "Sede Sur",
  "address": "Calle Secundaria 456",
  "phone": "+1234567891",
  "businessId": "gimnasio-central"
}
Response (201):

json
{
  "success": true,
  "data": {
    "id": "sede-sur",
    "name": "Sede Sur",
    "address": "Calle Secundaria 456",
    "phone": "+1234567891",
    "businessId": "gimnasio-central",
    "isActive": true,
    "createdAt": "2026-04-14T10:00:00Z"
  }
}
👥 Clientes
GET /clients
Lista clientes con filtros y paginación.

Headers: Authorization required

Query Parameters:

Parámetro	Tipo	Requerido	Descripción
branchId	string	No	Filtrar por sede
status	string	No	active, expired, suspended
search	string	No	Buscar por nombre o email
page	integer	No	Número de página (default: 1)
limit	integer	No	Items por página (default: 20, max: 100)
Ejemplo de request:

text
GET /api/clients?branchId=sede-norte&status=active&search=juan&page=1&limit=20
Response (200):

json
{
  "success": true,
  "data": [
    {
      "id": "client-001",
      "name": "Juan Pérez",
      "email": "juan@example.com",
      "phone": "+1234567890",
      "branchId": "sede-norte",
      "membershipPlanId": "plan-mensual",
      "membershipEnd": "2026-05-14T00:00:00Z",
      "status": "active",
      "isActive": true
    }
  ],
  "meta": {
    "total": 45,
    "page": 1,
    "limit": 20,
    "pages": 3
  }
}
GET /clients/:id
Obtiene un cliente por su ID.

URL Parameters:

Parámetro	Tipo	Descripción
id	string	ID del cliente
Response (200):

json
{
  "success": true,
  "data": {
    "id": "client-001",
    "name": "Juan Pérez",
    "email": "juan@example.com",
    "phone": "+1234567890",
    "documentId": "12345678",
    "branchId": "sede-norte",
    "businessId": "gimnasio-central",
    "membershipPlanId": "plan-mensual",
    "membershipStart": "2026-04-14T00:00:00Z",
    "membershipEnd": "2026-05-14T00:00:00Z",
    "status": "active",
    "registeredBy": "user-uid-123",
    "notes": "Prefiere horario matutino",
    "createdAt": "2026-04-01T10:00:00Z"
  }
}
POST /clients
Crea un nuevo cliente. (Requiere branch_admin o super_admin)

Request Body:

json
{
  "name": "María García",
  "email": "maria@example.com",
  "phone": "+1234567892",
  "documentId": "87654321",
  "branchId": "sede-norte",
  "businessId": "gimnasio-central",
  "membershipPlanId": "plan-mensual",
  "notes": "Viene por referencia"
}
Response (201):

json
{
  "success": true,
  "data": {
    "id": "client-002",
    "name": "María García",
    "email": "maria@example.com",
    "phone": "+1234567892",
    "branchId": "sede-norte",
    "membershipPlanId": "plan-mensual",
    "membershipStart": "2026-04-14T00:00:00Z",
    "membershipEnd": "2026-05-14T00:00:00Z",
    "status": "active",
    "createdAt": "2026-04-14T10:00:00Z"
  }
}
Errors:

400: Email ya registrado o datos inválidos

403: Rol sin permisos

PUT /clients/:id
Actualiza un cliente existente. (Requiere branch_admin o super_admin)

URL Parameters:

Parámetro	Tipo	Descripción
id	string	ID del cliente
Request Body: (todos opcionales)

json
{
  "name": "María García López",
  "phone": "+1234567893",
  "notes": "Cambió de horario",
  "status": "suspended"
}
Response (200):

json
{
  "success": true,
  "data": {
    "id": "client-002",
    "name": "María García López",
    "phone": "+1234567893",
    "status": "suspended",
    "updatedAt": "2026-04-14T11:00:00Z"
  }
}
GET /clients/:id/payments
Obtiene el historial de pagos de un cliente.

URL Parameters:

Parámetro	Tipo	Descripción
id	string	ID del cliente
Response (200):

json
{
  "success": true,
  "data": [
    {
      "id": "payment-001",
      "amount": 35000,
      "method": "cash",
      "membershipPlanId": "plan-mensual",
      "startDate": "2026-04-14T00:00:00Z",
      "endDate": "2026-05-14T00:00:00Z",
      "receiptNumber": "P-20260414-001",
      "createdAt": "2026-04-14T10:00:00Z"
    }
  ]
}
💰 Pagos
POST /payments
Registra un nuevo pago y actualiza automáticamente la membresía del cliente.

Headers: Authorization required

Request Body:

json
{
  "clientId": "client-001",
  "amount": 35000,
  "method": "cash",
  "membershipPlanId": "plan-mensual",
  "branchId": "sede-norte",
  "methodDetails": {
    "cardLast4": null,
    "transactionId": null,
    "reference": "REF-12345"
  }
}
Validaciones automáticas:

El monto debe coincidir con el precio del plan

El cliente debe existir y estar activo

La sede debe pertenecer al negocio del usuario

Response (201):

json
{
  "success": true,
  "data": {
    "id": "payment-002",
    "receiptNumber": "P-20260414-002",
    "clientId": "client-001",
    "amount": 35000,
    "method": "cash",
    "membershipPlanId": "plan-mensual",
    "startDate": "2026-04-14T00:00:00Z",
    "endDate": "2026-05-14T00:00:00Z",
    "registeredBy": "user-uid-123",
    "registeredByName": "Admin Principal",
    "createdAt": "2026-04-14T10:30:00Z"
  }
}
Errors:

400: Monto incorrecto o cliente inactivo

403: Rol sin permisos (cajero o superior requerido)

404: Cliente o plan no encontrado

GET /payments/report
Reporte de pagos con filtros. (Requiere branch_admin o super_admin)

Query Parameters:

Parámetro	Tipo	Requerido	Descripción
startDate	string (ISO)	Sí	Fecha inicio (YYYY-MM-DD)
endDate	string (ISO)	Sí	Fecha fin (YYYY-MM-DD)
branchId	string	No	Filtrar por sede
method	string	No	cash, card, transfer, other
Ejemplo:

text
GET /api/payments/report?startDate=2026-04-01&endDate=2026-04-30&branchId=sede-norte
Response (200):

json
{
  "success": true,
  "data": {
    "summary": {
      "totalAmount": 245000,
      "totalPayments": 7,
      "averageAmount": 35000
    },
    "byMethod": {
      "cash": 140000,
      "card": 70000,
      "transfer": 35000
    },
    "payments": [
      {
        "id": "payment-001",
        "receiptNumber": "P-20260414-001",
        "clientName": "Juan Pérez",
        "amount": 35000,
        "method": "cash",
        "registeredByName": "Admin Principal",
        "createdAt": "2026-04-14T10:00:00Z"
      }
    ]
  }
}
POST /payments/sync
Sincroniza múltiples pagos registrados offline. (Requiere cashier o superior)

Request Body:

json
{
  "payments": [
    {
      "clientId": "client-001",
      "amount": 35000,
      "method": "cash",
      "membershipPlanId": "plan-mensual",
      "branchId": "sede-norte",
      "registeredAt": "2026-04-14T09:00:00Z",
      "localId": "offline-001"
    },
    {
      "clientId": "client-002",
      "amount": 35000,
      "method": "card",
      "membershipPlanId": "plan-mensual",
      "branchId": "sede-norte",
      "registeredAt": "2026-04-14T09:05:00Z",
      "localId": "offline-002"
    }
  ]
}
Response (200):

json
{
  "success": true,
  "data": {
    "synced": 2,
    "failed": 0,
    "results": [
      {
        "localId": "offline-001",
        "serverId": "payment-010",
        "status": "success"
      },
      {
        "localId": "offline-002",
        "serverId": "payment-011",
        "status": "success"
      }
    ]
  }
}
Errors (conflictos):

json
{
  "success": false,
  "data": {
    "synced": 1,
    "failed": 1,
    "results": [
      {
        "localId": "offline-001",
        "status": "success",
        "serverId": "payment-010"
      },
      {
        "localId": "offline-002",
        "status": "conflict",
        "message": "El cliente ya tiene un pago registrado después de esta fecha"
      }
    ]
  }
}
📊 Reportes
GET /reports/solvency
Lista clientes morosos (membresía vencida). (Requiere branch_admin o super_admin)

Query Parameters:

Parámetro	Tipo	Requerido	Descripción
branchId	string	No	Filtrar por sede
daysOverdue	integer	No	Días de vencimiento (default: 0)
Ejemplo:

text
GET /api/reports/solvency?branchId=sede-norte&daysOverdue=7
Response (200):

json
{
  "success": true,
  "data": [
    {
      "id": "client-015",
      "name": "Carlos Ruiz",
      "phone": "+1234567899",
      "membershipPlanId": "plan-mensual",
      "membershipEnd": "2026-04-07T00:00:00Z",
      "daysOverdue": 7,
      "lastPaymentDate": "2026-03-07T10:00:00Z",
      "lastPaymentAmount": 35000
    }
  ],
  "meta": {
    "total": 12,
    "branchId": "sede-norte"
  }
}
GET /reports/income/daily
Ingresos diarios en un rango de fechas.

Query Parameters:

Parámetro	Tipo	Requerido	Descripción
startDate	string (ISO)	Sí	YYYY-MM-DD
endDate	string (ISO)	Sí	YYYY-MM-DD
branchId	string	No	Filtrar por sede
Response (200):

json
{
  "success": true,
  "data": {
    "totalPeriod": 525000,
    "daily": [
      {
        "date": "2026-04-01",
        "amount": 105000,
        "paymentsCount": 3
      },
      {
        "date": "2026-04-02",
        "amount": 70000,
        "paymentsCount": 2
      }
    ]
  }
}
GET /reports/income/by-method
Ingresos agrupados por método de pago.

Query Parameters:

Parámetro	Tipo	Requerido	Descripción
startDate	string (ISO)	No	YYYY-MM-DD
endDate	string (ISO)	No	YYYY-MM-DD
branchId	string	No	Filtrar por sede
Response (200):

json
{
  "success": true,
  "data": {
    "cash": {
      "amount": 245000,
      "percentage": 46.7,
      "count": 7
    },
    "card": {
      "amount": 175000,
      "percentage": 33.3,
      "count": 5
    },
    "transfer": {
      "amount": 105000,
      "percentage": 20.0,
      "count": 3
    }
  }
}
🔄 Webhooks (opcional para futura implementación)
POST /webhooks/payment-confirmed
Endpoint para recibir confirmaciones de pasarelas de pago externas.

Headers:

http
X-Webhook-Secret: tu_secreto_configurado
Request Body:

json
{
  "paymentId": "payment-001",
  "status": "confirmed",
  "externalReference": "tx_123456",
  "confirmedAt": "2026-04-14T10:35:00Z"
}
📝 Notas de implementación
Rate Limiting por endpoint
Endpoint	Límite	Ventana
POST /auth/verify	10 requests/min	Por IP
POST /payments	30 requests/min	Por usuario
POST /payments/sync	5 requests/min	Por usuario
GET /reports/*	20 requests/min	Por usuario
Resto de GET	100 requests/min	Por usuario
Paginación estándar
Todos los endpoints de lista soportan:

page: Número de página (1-indexed)

limit: Items por página (default 20, max 100)

Headers de paginación:

http
X-Total-Count: 150
X-Page: 2
X-Total-Pages: 8
Ordenamiento por defecto
Clientes: por createdAt DESC

Pagos: por createdAt DESC

Reportes: por date ASC

🧪 Ejemplos de uso con cURL
Login (obtener token de Firebase)
bash
# Esto se hace desde el frontend con Firebase Auth
# El token se obtiene automáticamente después del login
Listar clientes
bash
curl -X GET "http://localhost:5000/api/clients?branchId=sede-norte&status=active" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6..." \
  -H "Content-Type: application/json"
Registrar un pago
bash
curl -X POST http://localhost:5000/api/payments \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6..." \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "client-001",
    "amount": 35000,
    "method": "cash",
    "membershipPlanId": "plan-mensual",
    "branchId": "sede-norte"
  }'
Sincronizar pagos offline
bash
curl -X POST http://localhost:5000/api/payments/sync \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6..." \
  -H "Content-Type: application/json" \
  -d '{
    "payments": [...]
  }'
Reporte de morosos
bash
curl -X GET "http://localhost:5000/api/reports/solvency?branchId=sede-norte&daysOverdue=5" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6..."
📚 Cambios y versionado