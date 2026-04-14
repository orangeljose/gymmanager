# GymManager PWA - Documento de Requisitos

## 🎯 Visión General
Aplicación PWA para administración de gimnasios y pequeños negocios. Permite gestionar clientes, pagos, membresías y múltiples sedes con diferentes roles de usuario.

## 🏗️ Stack Tecnológico
- **Frontend**: React + Vite + TypeScript + PWA
- **Backend**: Python + Flask
- **Base de Datos**: Firebase Firestore
- **Autenticación**: Firebase Auth
- **Offline**: Dexie.js + Workbox

## 📊 Modelo de Datos (Firestore)

### Colecciones y Documentos

#### 1. `businesses` - Negocios
{
  id: string,              // auto-generated
  name: string,            // "Mi Gimnasio Central"
  rubro: string,           // "gym", "restaurant", etc.
  logo: string | null,     // URL de Firebase Storage
  ownerId: string,         // UID de Firebase Auth
  createdAt: Timestamp,
  settings: {
    currency: string,      // "MXN", "USD", etc.
    timezone: string       // "America/Mexico_City"
  }
}

#### 2. `branches` - Sedes
{
  id: string,
  name: string,            // "Sede Norte"
  address: string,
  phone: string,
  businessId: string,      // Referencia a businesses
  managerId: string | null, // UID del admin de sede
  isActive: boolean
}

#### 3. `membership_plans` - Planes/Membresías
{
  id: string,
  name: string,            // "Mensual", "Trimestral"
  price: number,           // 35000 (en cents para evitar floats)
  durationDays: number,    // 30, 90, 365
  description: string,
  businessId: string,
  isActive: boolean,
  benefits: string[]
}

#### 4. `clients` - Clientes del negocio
{
  id: string,
  name: string,
  email: string,
  phone: string,
  documentId: string | null, // Cédula/DNI
  branchId: string,           // Sede donde se registró
  businessId: string,
  membershipPlanId: string,
  membershipStart: Timestamp,
  membershipEnd: Timestamp,
  isActive: boolean,
  status: "active" | "expired" | "suspended",
  registeredBy: string,       // UID del usuario
  notes: string | null,
  createdAt: Timestamp
}

#### 5. `users` - Usuarios del sistema (empleados)
{
  id: string,              // MISMO UID que Firebase Auth
  email: string,
  name: string,
  role: "super_admin" | "branch_admin" | "cashier" | "trainer",
  businessId: string,
  branchId: string | null, // null para super_admin
  isActive: boolean,
  permissions: string[],    // ["read_clients", "write_payments", ...]
  createdAt: Timestamp
}

#### 6. `payments` - Pagos registrados
{
  id: string,
  clientId: string,
  clientName: string,      // Denormalizado para búsqueda rápida
  amount: number,          // En cents (ej: 35000 = $350.00)
  method: "cash" | "card" | "transfer" | "other",
  methodDetails: {
    cardLast4: string | null,
    transactionId: string | null,
    reference: string | null
  },
  membershipPlanId: string,
  monthsPaid: number,      // 1, 3, 12
  startDate: Timestamp,
  endDate: Timestamp,
  branchId: string,
  businessId: string,
  registeredBy: string,    // UID del usuario
  registeredByName: string, // Denormalizado
  receiptNumber: string,    // Formato: P-YYYYMMDD-XXX
  syncedAt: Timestamp | null, // Para offline sync
  createdAt: Timestamp
}

🔐 Roles y Permisos
Rol	Clientes (leer)	Clientes (escribir)	Pagos (registrar)	Reportes	Usuarios (editar)
super_admin	✅	✅	✅	✅	✅
branch_admin	✅	✅ (su sede)	✅	✅ (su sede)	❌
cashier	✅	❌	✅	❌	❌
trainer	✅	❌	❌	❌	❌

## 📡 API Overview

La API REST está documentada completamente en [`API_SPEC.md`](./API_SPEC.md).

**Endpoints principales:**
- `GET /api/clients` - Listado y búsqueda de clientes
- `POST /api/payments` - Registro de pagos
- `GET /api/reports/solvency` - Reporte de morosos

> 📖 Para detalles de request/response, códigos de error y ejemplos, ver `API_SPEC.md`

📱 Funcionalidades PWA Offline
Cache de clientes: Últimos 200 clientes vistos disponibles offline

Registro de pagos offline:

Guardar en IndexedDB

Asignar synced: false

Sincronizar al recuperar conexión

Resolución de conflictos:

Timestamp más reciente prevalece

Notificar al usuario si hay conflicto

🚀 Plan de Implementación (MVP)
Semana 1-2: Backend Base
Proyecto Flask con estructura MVC

Conexión a Firebase Admin SDK

Endpoints de clientes y pagos

Middleware de autenticación y roles

Semana 3-4: Frontend Base
Login con Firebase Auth

Dashboard con métricas básicas

Listado de clientes con búsqueda

Formulario de registro de pagos

Semana 5-6: Offline y PWA
Configurar Dexie.js

Sincronización de pagos offline

Service Worker con Workbox

Botón "Instalar PWA"

Semana 7-8: Reportes y Mejoras
Reporte de morosos

Reporte de ingresos

Gestión de roles

Pruebas con usuarios reales

📊 Cálculo de Límites (Firebase Free Tier)
Concepto	Límite	Proyección MVP
Documentos almacenados	1 GB	~10 MB (sobra)
Lecturas/día	50K	~1,000 (sobra)
Escrituras/día	20K	~500 (sobra)
Usuarios Auth	Ilimitado	~50 empleados
🔒 Reglas de Seguridad (Firestore)
javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Leer: solo autenticados
    match /{document=**} {
      allow read: if request.auth != null;
    }
    
    // Escribir según rol
    match /payments/{payment} {
      allow write: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role in ['cashier', 'branch_admin', 'super_admin'];
    }
    
    match /clients/{client} {
      allow write: if request.auth != null &&
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role in ['branch_admin', 'super_admin'];
    }
  }
}

📝 Notas Técnicas
Manejo de dinero: Siempre usar enteros (cents) para evitar problemas con floats

Fechas: Siempre usar Timestamp de Firestore, nunca strings

Denormalización: Guardar clientName y registeredByName en pagos para evitar lecturas adicionales

IDs: Los usuarios en colección users deben usar el mismo UID de Firebase Auth