# GymManager Backend - API REST para Administración de Gimnasios

Backend Flask para la PWA de administración de gimnasios GymManager con integración completa a Firebase Firestore y Auth.

## 🚀 Características Principales

- ✅ **Autenticación Firebase** - Verificación de tokens JWT
- ✅ **Gestión de Clientes** - CRUD completo con filtros
- ✅ **Registro de Pagos** - Online y offline con sincronización
- ✅ **Reportes** - Morosos, ingresos diarios, por método
- ✅ **Múltiples Sedes** - Gestión por negocio y permisos
- ✅ **Roles y Permisos** - Super admin, admin, cajero, entrenador
- ✅ **Rate Limiting** - 100 peticiones/minuto por usuario
- ✅ **Logging Completo** - Todas las operaciones críticas
- ✅ **Manejo de Errores** - Respuestas estandarizadas

## 📋 Requisitos Previos

1. **Python 3.8+** instalado
2. **Cuenta Firebase** con Firestore y Auth configurados
3. **Archivo de credenciales** `serviceAccountKey.json` descargado de Firebase

## 🛠️ Instalación y Configuración

### 1. Clonar y configurar entorno

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd gymmanager/backend

# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
venv\Scripts\activate

# Activar entorno (Linux/Mac)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus datos
nano .env
```

**Variables requeridas:**
- `FIREBASE_CREDENTIALS_JSON` - JSON string de credenciales de Firebase
- `FIREBASE_DATABASE_URL` - URL de tu proyecto Firebase
- `FLASK_ENV` - `development` o `production`
- `PORT` - Puerto del servidor (default: 5000)
- `CORS_ORIGINS` - Orígenes permitidos separados por coma

### 3. Configurar Firebase

1. Ve a [Firebase Console](https://console.firebase.google.com/)
2. Selecciona tu proyecto
3. Ve a **Project Settings** → **Service accounts**
4. Clica **"Generate new private key"**
5. Descarga el archivo JSON y renómbralo a `serviceAccountKey.json`
6. Coloca el archivo en la raíz del backend

## 🚀 Ejecución

### Desarrollo

```bash
# Ejecutar en modo desarrollo
python app.py
```

El servidor iniciará en:
- URL: `http://127.0.0.1:5000`
- Health check: `http://127.0.0.1:5000/health`

### Producción

```bash
# Ejecutar en modo producción
export FLASK_ENV=production
python app.py
```

## 📡 Endpoints Disponibles

### Autenticación
- `POST /api/auth/verify` - Verificar token Firebase

### Clientes
- `GET /api/clients` - Listar clientes (filtros: branchId, status, search, page, limit)
- `GET /api/clients/<id>` - Obtener cliente por ID
- `POST /api/clients` - Crear cliente (requiere admin+)
- `PUT /api/clients/<id>` - Actualizar cliente (requiere admin+)
- `GET /api/clients/<id>/payments` - Historial de pagos

### Pagos
- `POST /api/payments` - Registrar pago (requiere cajero+)
- `GET /api/payments/report` - Reporte de pagos (requiere admin+)
- `POST /api/payments/sync` - Sincronizar pagos offline (requiere cajero+)

### Reportes
- `GET /api/reports/solvency` - Clientes morosos (requiere admin+)
- `GET /api/reports/income/daily` - Ingresos diarios (requiere admin+)
- `GET /api/reports/income/by-method` - Ingresos por método (requiere admin+)

### Sedes y Negocios
- `GET /api/businesses` - Negocios del usuario
- `GET /api/branches/<businessId>` - Sedes de un negocio
- `POST /api/branches` - Crear sede (requiere admin+)

## 🔐 Autenticación

Todos los endpoints (excepto `/health` y `/api/auth/verify`) requieren:

```http
Authorization: Bearer <firebase_token>
Content-Type: application/json
```

## 📊 Formato de Respuestas

### Éxito
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
```

### Error
```json
{
  "success": false,
  "error": {
    "code": 400,
    "message": "Descripción del error"
  }
}
```

## 🏗️ Estructura del Proyecto

```
backend/
├── app.py                    # Aplicación Flask principal
├── requirements.txt            # Dependencias Python
├── .env.example             # Template variables de entorno
├── config.py                # Configuración de la app
├── models/                  # Modelos y validaciones
│   ├── __init__.py
│   ├── client.py            # Validaciones de clientes
│   ├── payment.py           # Validaciones de pagos
│   └── user.py              # Modelos de usuarios
├── routes/                  # Endpoints API
│   ├── __init__.py
│   ├── auth.py              # Autenticación
│   ├── clients.py           # Gestión de clientes
│   ├── payments.py          # Gestión de pagos
│   ├── reports.py           # Reportes
│   └── branches.py          # Sedes y negocios
├── services/                # Lógica de negocio
│   ├── __init__.py
│   ├── firebase_service.py   # Conexión Firebase
│   ├── payment_service.py    # Lógica de pagos
│   └── membership_service.py # Membresías
├── middleware/              # Middleware Flask
│   ├── __init__.py
│   └── auth_middleware.py   # Autenticación y roles
└── utils/                  # Utilidades
    ├── __init__.py
    └── validators.py        # Validaciones de datos
```

## 🔧 Roles y Permisos

| Rol | Permisos |
|-----|-----------|
| **super_admin** | Todos los permisos (`*`) |
| **branch_admin** | Leer clientes, escribir clientes, leer pagos, escribir pagos, leer reportes |
| **cashier** | Leer clientes, escribir pagos |
| **trainer** | Leer clientes |

## 📱 Funcionalidad Offline

La API soporta sincronización de pagos registrados offline:

1. **Registro Offline**: Los pagos se guardan localmente en el frontend
2. **Sincronización**: `POST /api/payments/sync` procesa pagos batch
3. **Resolución de Conflictos**: Por timestamp más reciente
4. **Estado**: Campo `syncedAt` indica si el pago fue sincronizado

## 🐛 Solución de Problemas

### Error: "FIREBASE_CREDENTIALS_JSON no está configurado"
```bash
# Asegúrate de tener el archivo .env
ls -la .env

# Verifica que la variable esté configurada
cat .env | grep FIREBASE_CREDENTIALS_JSON
```

### Error: "Token inválido o expirado"
- Verifica que el token sea de Firebase Auth
- El frontend debe obtener un token nuevo
- Revisa la configuración de Firebase Auth

### Error: "No tienes acceso a esta sede"
- El usuario no tiene permiso para la sede solicitada
- Verifica el rol y la sede asignada en Firestore
- Solo super admin puede acceder a todas las sedes

### Error: "Cliente no encontrado"
- Verifica que el ID del cliente sea correcto
- El cliente debe pertenecer al mismo negocio que el usuario

## 📝 Logs

La aplicación genera logs en:
- **Consola**: En modo desarrollo
- **Archivo**: `gymmanager.log` en modo producción

Niveles de logging:
- `DEBUG`: Información detallada (desarrollo)
- `INFO`: Operaciones importantes (producción)
- `WARNING`: Advertencias
- `ERROR`: Errores críticos

## 🚀 Despliegue

Para despliegue en producción, consulta el archivo [`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md)

## 📚 Documentación Adicional

- [API Specification](../docs/API_SPEC.md) - Especificación completa de la API
- [Database Schema](../docs/DATABASE_SCHEMA.md) - Esquema de Firestore
- [Requirements](../docs/requirements.md) - Requisitos del proyecto
- [Test Plan](../docs/TEST_PLAN.md) - Plan de pruebas
- [Deployment Guide](../docs/DEPLOYMENT.md) - Guía de despliegue

## 🤝 Soporte

Para problemas o preguntas:
- Revisa los logs de la aplicación
- Consulta la documentación técnica
- Verifica la configuración de Firebase

---

**GymManager Backend** - Desarrollado con ❤️ para gimnasios modernos
