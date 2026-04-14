# GymManager - Database Schema (Firestore)

## 📋 Visión General

| Propiedad | Valor |
|-----------|-------|
| **Base de Datos** | Cloud Firestore (NoSQL) |
| **Proyecto** | gymmanager-v1 |
| **Región** | us-central1 (o la elegida) |
| **Modo** | Nativo (No Datastore) |

### Convenciones de diseño

| Concepto | Convención | Ejemplo |
|----------|------------|---------|
| **Nombres de colecciones** | plural, snake_case | `membership_plans` |
| **Nombres de campos** | camelCase | `membershipStart` |
| **IDs de documentos** | auto-generado o slug | `client-001`, `sede-norte` |
| **Referencias** | Guardar como string, no como Reference type | `businessId: "gimnasio-central"` |
| **Timestamps** | Firestore Timestamp | `createdAt: Timestamp` |
| **Moneda** | Entero en cents | `amount: 35000` ($350.00) |

### Relaciones (sin JOINs físicos)

businesses (1) ──┬── branches (N)
├── membership_plans (N)
├── clients (N)
└── users (N)

branches (1) ────┬── clients (N)
└── payments (N)

clients (1) ─────┴── payments (N)

users (1) ───────┴── payments (N) (registeredBy)

---

## 🗂️ Colección: `businesses`

**Propósito:** Almacena los negocios (ej: gimnasios, restaurantes)

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id` | string (ID) | Sí | Auto-generado o definido |
| `name` | string | Sí | Nombre del negocio |
| `rubro` | string | Sí | `gym`, `restaurant`, `store`, etc. |
| `logo` | string \| null | No | URL de Firebase Storage |
| `ownerId` | string | Sí | UID del dueño (Firebase Auth) |
| `createdAt` | Timestamp | Sí | Fecha de creación |
<!-- | `settings` | object | Sí | Configuración del negocio | -->

<!-- ### `settings` object

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `currency` | string | `"USD"` | Código ISO (USD, MXN, EUR) |
| `timezone` | string | `"America/New_York"` | Zona horaria |
| `language` | string | `"es"` | Idioma por defecto |
| `receiptPrefix` | string | `"P"` | Prefijo para recibos | -->

### Ejemplo de documento

```json
{
  "name": "Mi Gimnasio Central",
  "rubro": "gym",
  "logo": "https://storage.googleapis.com/gymmanager/logos/gym-central.png",
  "ownerId": "abc123def456",
  "createdAt": "2026-01-15T10:00:00.000Z",
  //*//  "settings": {
  //   "currency": "MXN",
  //   "timezone": "America/Mexico_City",
  //   "language": "es",
  //   "receiptPrefix": "GYM"
  //*//}
}

Índices requeridos
Campos	Tipo	Propósito
ownerId	Single	Buscar negocios de un usuario
rubro	Single	Filtrar por tipo de negocio

🗂️ Colección: branches
Propósito: Sedes físicas de cada negocio

Campo	Tipo	Requerido	Descripción
id	string (ID)	Sí	Auto-generado o definido
name	string	Sí	Nombre de la sede
address	string	Sí	Dirección completa
phone	string	Sí	Teléfono de contacto
businessId	string	Sí	ID del negocio padre
managerId	string | null	No	UID del administrador de sede
isActive	boolean	Sí	Si está operativa
createdAt	Timestamp	Sí	Fecha de creación
Ejemplo de documento
json
{
  "name": "Sede Norte",
  "address": "Av. Principal 123, Col. Centro, CDMX",
  "phone": "+525555123456",
  "businessId": "gimnasio-central",
  "managerId": "user-uid-456",
  "isActive": true,
  "createdAt": "2026-01-15T10:30:00.000Z"
}
Índices requeridos
Campos	Tipo	Propósito
businessId	Single	Listar sedes de un negocio
businessId + isActive	Compuesto	Filtrar sedes activas
managerId	Single	Buscar sede por administrador
🗂️ Colección: membership_plans
Propósito: Planes/membresías disponibles en cada negocio

Campo	Tipo	Requerido	Descripción
id	string (ID)	Sí	Auto-generado o definido
name	string	Sí	Ej: "Mensual", "Trimestral"
price	number	Sí	Precio en cents (ej: 35000 = $350.00)
durationDays	number	Sí	Duración en días (30, 90, 365)
description	string	No	Descripción del plan
businessId	string	Sí	ID del negocio padre
isActive	boolean	Sí	Si está disponible para venta
benefits	array<string>	No	Lista de beneficios
createdAt	Timestamp	Sí	Fecha de creación
Ejemplo de documento
json
{
  "name": "Mensual",
  "price": 35000,
  "durationDays": 30,
  "description": "Acceso completo por 30 días",
  "businessId": "gimnasio-central",
  "isActive": true,
  "benefits": [
    "Acceso todas las sedes",
    "Clases grupales ilimitadas",
    "Estacionamiento gratuito"
  ],
  "createdAt": "2026-01-15T11:00:00.000Z"
}
Índices requeridos
Campos	Tipo	Propósito
businessId	Single	Listar planes de un negocio
businessId + isActive	Compuesto	Filtrar planes activos
price	Single	Ordenar por precio
🗂️ Colección: clients
Propósito: Clientes del negocio (los que pagan membresía)

Campo	Tipo	Requerido	Descripción
id	string (ID)	Sí	Auto-generado
name	string	Sí	Nombre completo
email	string	Sí	Correo electrónico
phone	string	Sí	Teléfono
documentId	string | null	No	Cédula/DNI/RUT
branchId	string	Sí	Sede donde se registró
businessId	string	Sí	Negocio al que pertenece
membershipPlanId	string	Sí	Plan actual
membershipStart	Timestamp	Sí	Inicio de membresía actual
membershipEnd	Timestamp	Sí	Fin de membresía actual
isActive	boolean	Sí	Si está activo en el sistema
status	string	Sí	active, expired, suspended
registeredBy	string	Sí	UID del usuario que registró
notes	string | null	No	Notas adicionales
createdAt	Timestamp	Sí	Fecha de registro
Valores de status
Valor	Significado	Condición
active	Al día	membershipEnd > now()
expired	Vencido	membershipEnd < now()
suspended	Suspendido por admin	isActive = false
Ejemplo de documento
json
{
  "name": "Juan Pérez Gómez",
  "email": "juan.perez@example.com",
  "phone": "+525555789012",
  "documentId": "ABCD123456",
  "branchId": "sede-norte",
  "businessId": "gimnasio-central",
  "membershipPlanId": "plan-mensual",
  "membershipStart": "2026-04-01T00:00:00.000Z",
  "membershipEnd": "2026-05-01T00:00:00.000Z",
  "isActive": true,
  "status": "active",
  "registeredBy": "user-uid-123",
  "notes": "Prefiere horario matutino. Lesión de rodilla.",
  "createdAt": "2026-04-01T09:00:00.000Z"
}
Índices requeridos
Campos	Tipo	Propósito
businessId	Single	Listar clientes de un negocio
branchId	Single	Filtrar por sede
status	Single	Filtrar por estado
membershipEnd	Single	Buscar morosos
businessId + status	Compuesto	Filtrar por negocio y estado
branchId + status	Compuesto	Filtrar por sede y estado
name	Single	Búsqueda por nombre (requiere índice de colección única)
🗂️ Colección: users
Propósito: Usuarios del sistema (empleados). El ID debe coincidir con el UID de Firebase Auth.

Campo	Tipo	Requerido	Descripción
id	string (ID)	Sí	MISMO UID que Firebase Auth
email	string	Sí	Correo electrónico
name	string	Sí	Nombre del usuario
role	string	Sí	super_admin, branch_admin, cashier, trainer
businessId	string	Sí	Negocio al que pertenece
branchId	string | null	No	Sede asignada (null para super_admin)
isActive	boolean	Sí	Si puede acceder al sistema
permissions	array<string>	Sí	Lista de permisos explícitos
createdAt	Timestamp	Sí	Fecha de creación
Roles y permisos predefinidos
Rol	Permisos automáticos
super_admin	["*"] (todos)
branch_admin	["read_clients", "write_clients", "read_payments", "write_payments", "read_reports"]
cashier	["read_clients", "write_payments"]
trainer	["read_clients"]
Ejemplo de documento
json
{
  "email": "admin@gym.com",
  "name": "Carlos Admin",
  "role": "branch_admin",
  "businessId": "gimnasio-central",
  "branchId": "sede-norte",
  "isActive": true,
  "permissions": ["read_clients", "write_clients", "read_payments", "write_payments", "read_reports"],
  "createdAt": "2026-01-15T12:00:00.000Z"
}
Índices requeridos
Campos	Tipo	Propósito
businessId	Single	Listar usuarios de un negocio
role	Single	Filtrar por rol
branchId	Single	Filtrar por sede
🗂️ Colección: payments
Propósito: Registro de todos los pagos realizados

Campo	Tipo	Requerido	Descripción
id	string (ID)	Sí	Auto-generado
clientId	string	Sí	ID del cliente
clientName	string	Sí	Denormalizado (nombre del cliente)
amount	number	Sí	Monto en cents
method	string	Sí	cash, card, transfer, other
methodDetails	object	No	Detalles según método
membershipPlanId	string	Sí	Plan que se pagó
monthsPaid	number	Sí	Meses pagados (1, 3, 12)
startDate	Timestamp	Sí	Inicio del período pagado
endDate	Timestamp	Sí	Fin del período pagado
branchId	string	Sí	Sede donde se registró
businessId	string	Sí	Negocio al que pertenece
registeredBy	string	Sí	UID del usuario que registró
registeredByName	string	Sí	Denormalizado (nombre del registrador)
receiptNumber	string	Sí	Número único de recibo
syncedAt	Timestamp | null	No	Para pagos offline (null = pendiente)
createdAt	Timestamp	Sí	Fecha del registro
methodDetails object según método
Para method: "cash"
json
{
  "cashierName": "Juan Caja",
  "receivedAmount": 35000,
  "change": 0
}
Para method: "card"
json
{
  "cardLast4": "1234",
  "cardBrand": "Visa",
  "transactionId": "tx_abc123",
  "authorizationCode": "AUTH123"
}
Para method: "transfer"
json
{
  "reference": "REF-20260414-001",
  "bank": "BBVA",
  "accountNumber": "****1234"
}
Ejemplo de documento
json
{
  "clientId": "client-001",
  "clientName": "Juan Pérez",
  "amount": 35000,
  "method": "cash",
  "methodDetails": {
    "cashierName": "María Caja",
    "receivedAmount": 50000,
    "change": 15000
  },
  "membershipPlanId": "plan-mensual",
  "monthsPaid": 1,
  "startDate": "2026-04-14T00:00:00.000Z",
  "endDate": "2026-05-14T00:00:00.000Z",
  "branchId": "sede-norte",
  "businessId": "gimnasio-central",
  "registeredBy": "user-uid-123",
  "registeredByName": "Carlos Admin",
  "receiptNumber": "P-20260414-001",
  "syncedAt": null,
  "createdAt": "2026-04-14T10:30:00.000Z"
}
Índices requeridos
Campos	Tipo	Propósito
clientId	Single	Historial de pagos de un cliente
businessId	Single	Reportes por negocio
branchId	Single	Reportes por sede
createdAt	Single	Reportes por fecha
method	Single	Reportes por método de pago
businessId + createdAt	Compuesto	Reportes por negocio y fecha
branchId + createdAt	Compuesto	Reportes por sede y fecha
syncedAt	Single	Pagos pendientes de sincronizar
🔄 Subcolecciones (opcionales para futuras versiones)
clients/{clientId}/checkins
Para registrar ingresos diarios de clientes al gimnasio.

json
{
  "checkinTime": "2026-04-14T08:30:00.000Z",
  "checkedBy": "user-uid-123",
  "branchId": "sede-norte"
}
payments/{paymentId}/refunds
Para registrar devoluciones o cancelaciones.

json
{
  "refundAmount": 35000,
  "reason": "Cliente canceló membresía",
  "refundedBy": "user-uid-123",
  "refundedAt": "2026-04-15T10:00:00.000Z"
}
📊 Consultas comunes y su rendimiento
1. Clientes morosos de una sede
javascript
const query = db.collection('clients')
  .where('branchId', '==', 'sede-norte')
  .where('status', '==', 'active')
  .where('membershipEnd', '<', new Date());
Índice requerido: branchId + status + membershipEnd

2. Pagos de hoy en un negocio
javascript
const today = new Date();
today.setHours(0,0,0,0);
const tomorrow = new Date(today);
tomorrow.setDate(tomorrow.getDate() + 1);

const query = db.collection('payments')
  .where('businessId', '==', 'gimnasio-central')
  .where('createdAt', '>=', today)
  .where('createdAt', '<', tomorrow);
Índice requerido: businessId + createdAt

3. Búsqueda de cliente por nombre
javascript
// Firestore NO soporta búsqueda tipo "LIKE"
// Solución 1: Usar array de palabras clave
const query = db.collection('clients')
  .where('searchKeywords', 'array-contains', 'juan');

// Solución 2: Usar Algolia o Meilisearch (recomendado para escalar)
Campo adicional sugerido en clients:

json
"searchKeywords": ["juan", "perez", "juanperez", "jp"]
4. Reporte de ingresos por método
javascript
// Esto requiere procesamiento en cliente o Cloud Function
// No se puede hacer con una sola query nativa de Firestore
🔧 Reglas de validación (seguridad)
Reglas de Firestore (resumen)
javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Validar que los usuarios autenticados tengan rol
    function hasRole(requiredRole) {
      let userDoc = get(/databases/$(database)/documents/users/$(request.auth.uid));
      return userDoc != null && userDoc.data.role == requiredRole;
    }
    
    // Validar que pertenezca al mismo negocio
    function belongsToBusiness(businessIdField) {
      let userDoc = get(/databases/$(database)/documents/users/$(request.auth.uid));
      return resource.data[businessIdField] == userDoc.data.businessId;
    }
    
    // Clientes
    match /clients/{client} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        (hasRole('super_admin') || hasRole('branch_admin')) &&
        belongsToBusiness('businessId');
    }
    
    // Pagos
    match /payments/{payment} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        (hasRole('super_admin') || hasRole('branch_admin') || hasRole('cashier')) &&
        belongsToBusiness('businessId');
    }
  }
}
📈 Proyección de crecimiento
Escenario	Clientes	Pagos/mes	Tamaño estimado
MVP (1 gimnasio)	500	600	~10 MB
Pequeño (3 gimnasios)	2,000	2,400	~40 MB
Mediano (10 gimnasios)	10,000	12,000	~200 MB
Grande (50 gimnasios)	50,000	60,000	~1 GB
Nota: Firestore gratis incluye 1 GB. Al superarlo, cuesta $0.18/GB/mes.

🛠️ Migraciones y cambios de esquema
Firestore es schemaless, pero documenta cambios aquí:

Fecha	Cambio	Impacto	Script de migración
2026-04-14	Versión inicial	-	-
(futuro)	Agregar searchKeywords a clients	Bajo	Actualizar documentos existentes con Cloud Function
Script de migración (ejemplo)
javascript
// Para agregar searchKeywords a clientes existentes
const clients = await db.collection('clients').get();
const batch = db.batch();

clients.forEach(doc => {
  const name = doc.data().name.toLowerCase();
  const keywords = name.split(' ');
  batch.update(doc.ref, { searchKeywords: keywords });
});

await batch.commit();