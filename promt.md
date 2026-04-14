Necesito que me ayudes a crear un backend en Flask para una PWA de administración de gimnasios. Ya tengo Firebase configurado (Firestore + Auth). El proyecto se llama "GymManager".

## Requisitos del Backend

### Estructura de carpetas que necesito:
backend/
├── app.py # Entry point principal
├── requirements.txt # Dependencias
├── .env # Variables de entorno
├── config.py # Configuración (Firebase creds, etc)
├── models/
│ ├── init.py
│ ├── client.py
│ ├── payment.py
│ └── user.py
├── routes/
│ ├── init.py
│ ├── auth.py
│ ├── clients.py
│ ├── payments.py
│ ├── reports.py
│ └── branches.py
├── services/
│ ├── init.py
│ ├── firebase_service.py
│ ├── payment_service.py
│ └── membership_service.py
├── middleware/
│ ├── init.py
│ └── auth_middleware.py
└── utils/
├── init.py
└── validators.py

text

### Endpoints a implementar (todos con autenticación JWT de Firebase):

#### 1. Clientes
- `GET /api/clients` - Listar clientes (soporta filtros: branchId, status, search)
- `GET /api/clients/<id>` - Obtener cliente por ID
- `POST /api/clients` - Crear cliente (solo branch_admin o super_admin)
- `PUT /api/clients/<id>` - Actualizar cliente
- `GET /api/clients/<id>/payments` - Historial de pagos del cliente

#### 2. Pagos
- `POST /api/payments` - Registrar pago
  - Al registrar pago, automáticamente debe:
    - Actualizar membershipEnd del cliente según el plan
    - Generar receiptNumber (formato: P-YYYYMMDD-XXX)
    - Validar que el monto coincida con el plan
  - Campos requeridos: clientId, amount, method, membershipPlanId, branchId
- `GET /api/payments/report` - Reporte de pagos (filtros: startDate, endDate, branchId)
- `POST /api/payments/sync` - Sincronizar múltiples pagos offline (batch)

#### 3. Reportes
- `GET /api/reports/solvency` - Clientes morosos (membershipEnd < today)
- `GET /api/reports/income/daily` - Ingresos agrupados por día
- `GET /api/reports/income/by-method` - Ingresos por método de pago

#### 4. Sedes y Negocios
- `GET /api/businesses` - Negocios del usuario autenticado
- `GET /api/branches/<businessId>` - Sedes de un negocio
- `POST /api/branches` - Crear nueva sede

### Middleware de Autenticación

Necesito un decorador `@require_auth` que:
1. Extraiga el token del header `Authorization: Bearer <token>`
2. Verifique el token con Firebase Admin SDK
3. Obtenga el UID del usuario
4. Consulte el rol del usuario en la colección `users` de Firestore
5. Inyecte `current_user` (con uid, email, role) en la request
6. Opcionalmente, otro decorador `@require_role(['admin', 'cashier'])` para restringir endpoints

### Servicios importantes

#### Firebase Service
- Función para inicializar Firebase Admin SDK desde variable de entorno
- Función para verificar token
- Función helper para queries a Firestore con logging

#### Payment Service
- Función `register_payment(data, current_user)` que maneje toda la lógica
- Función `generate_receipt_number()` que lleve contador por día
- Función `extend_membership(client_id, plan_id, months_paid)`

#### Membership Service
- Función `calculate_new_end_date(start_date, duration_days)`
- Función `get_plan_by_id(plan_id)`
- Función `validate_payment_amount(client_id, amount, plan_id)`

### Variables de entorno necesarias (.env)
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
FIREBASE_DATABASE_URL=https://tu-proyecto.firebaseio.com
JWT_SECRET_KEY=tu-secreto-super-seguro
FLASK_ENV=development
PORT=5000
CORS_ORIGINS=http://localhost:5173,https://tudominio.com

text

### Dependencias (requirements.txt)
Flask==3.0.0
flask-cors==4.0.0
firebase-admin==6.4.0
python-dotenv==1.0.0
flask-limiter==3.5.0

text

### Extras que necesito:
1. Manejo de errores consistente (respuestas con formato `{"error": "mensaje", "code": 400}`)
2. Logging de todas las operaciones importantes (registro de pagos, creación de clientes)
3. Validación de datos con Pydantic o esquemas simples en utils/validators.py
4. Rate limiting: 100 peticiones por minuto por usuario
5. Documentación de API inline con comentarios (para poder generar documentación después)

### Formato de respuestas esperado:
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
Lo que NO necesito:
Frontend (solo API)

Migraciones de base de datos (Firestore es schemaless)

Tests unitarios por ahora (solo el código funcional)

Por favor, generame:

El archivo app.py completo

El middleware de autenticación

El servicio de Firebase

Al menos 2 routes completas (clients y payments) como ejemplo

El archivo requirements.txt

El archivo .env.example

Instrucciones para correr el proyecto localmente