# GymManager - Plan de Pruebas (Test Plan)

## 📋 Tabla de Contenidos

1. [Objetivo del plan de pruebas](#objetivo-del-plan-de-pruebas)
2. [Estrategia de pruebas](#estrategia-de-pruebas)
3. [Entorno de pruebas](#entorno-de-pruebas)
4. [Casos de prueba por módulo](#casos-de-prueba-por-módulo)
   - [Autenticación](#autenticación)
   - [Gestión de Clientes](#gestión-de-clientes)
   - [Gestión de Pagos (Online)](#gestión-de-pagos-online)
   - [Gestión de Pagos (Offline)](#gestión-de-pagos-offline)
   - [Reportes](#reportes)
   - [Roles y Permisos](#roles-y-permisos)
   - [Sincronización Offline](#sincronización-offline)
5. [Pruebas de rendimiento](#pruebas-de-rendimiento)
6. [Pruebas de seguridad](#pruebas-de-seguridad)
7. [Pruebas de usabilidad](#pruebas-de-usabilidad)
8. [Pruebas de compatibilidad](#pruebas-de-compatibilidad)
9. [Criterios de aceptación](#criterios-de-aceptación)
10. [Reporte de bugs (plantilla)](#reporte-de-bugs-plantilla)

---

## 🎯 Objetivo del plan de pruebas

Validar que **GymManager** funcione correctamente en todos los escenarios críticos antes del lanzamiento, especialmente:

- ✅ Registro de pagos **online y offline**
- ✅ Sincronización automática al recuperar internet
- ✅ Cálculo correcto de fechas de vencimiento
- ✅ Control de acceso por roles (seguridad)
- ✅ Rendimiento aceptable con datos reales

---

## 🧪 Estrategia de pruebas

| Tipo de prueba | Cobertura | Herramientas |
|----------------|-----------|--------------|
| **Pruebas unitarias** | Backend (Flask) | `pytest` |
| **Pruebas de integración** | API + Firestore | `pytest` + `requests` |
| **Pruebas E2E** | Flujos completos | `Playwright` / `Cypress` |
| **Pruebas offline** | PWA + IndexedDB | Manual + `Lighthouse` |
| **Pruebas de carga** | Rendimiento | `k6` / `Artillery` |
| **Pruebas de seguridad** | Autenticación + roles | Manual + `OWASP ZAP` |

### Matriz de prioridad

| Prioridad | Color | Descripción |
|-----------|-------|-------------|
| **Alta** | 🔴 | Debe funcionar sí o sí (pagos, login) |
| **Media** | 🟡 | Importante pero no bloqueante (reportes) |
| **Baja** | 🟢 | Mejora de experiencia (exportar Excel) |

---

## 💻 Entorno de pruebas

### Configuración local

```bash
# 1. Clonar repositorio
git clone https://github.com/tuusuario/gymmanager.git
cd gymmanager

# 2. Configurar backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pytest pytest-cov  # Para pruebas

# 3. Configurar frontend
cd ../frontend
npm install
npm run dev

# 4. Inicializar Firebase emulator (opcional)
firebase emulators:start

Datos de prueba
Crear archivo test_data.json:

json
{
  "business": {
    "id": "test-gym",
    "name": "Gimnasio Test",
    "rubro": "gym"
  },
  "branches": [
    { "id": "sede-norte", "name": "Sede Norte" },
    { "id": "sede-sur", "name": "Sede Sur" }
  ],
  "plans": [
    { "id": "plan-mensual", "name": "Mensual", "price": 35000, "durationDays": 30 },
    { "id": "plan-trimestral", "name": "Trimestral", "price": 90000, "durationDays": 90 }
  ],
  "clients": [
    { "name": "Juan Pérez", "email": "juan@test.com", "branchId": "sede-norte", "membershipPlanId": "plan-mensual" },
    { "name": "María López", "email": "maria@test.com", "branchId": "sede-norte", "membershipPlanId": "plan-trimestral" }
  ],
  "users": [
    { "email": "admin@test.com", "role": "super_admin" },
    { "email": "cashier@test.com", "role": "cashier", "branchId": "sede-norte" }
  ]
}
✅ Casos de prueba por módulo
1. Autenticación 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
AUTH-01	Login exitoso	1. Ingresar email válido
2. Ingresar contraseña correcta
3. Tocar "Iniciar sesión"	Redirige al Dashboard	🔴
AUTH-02	Login fallido (contraseña incorrecta)	1. Ingresar email válido
2. Ingresar contraseña incorrecta
3. Tocar "Iniciar sesión"	Mensaje: "Contraseña incorrecta"	🔴
AUTH-03	Login fallido (usuario no existe)	1. Ingresar email no registrado
2. Cualquier contraseña
3. Tocar "Iniciar sesión"	Mensaje: "Usuario no encontrado"	🔴
AUTH-04	Recuperar contraseña	1. Tocar "¿Olvidaste tu contraseña?"
2. Ingresar email
3. Revisar correo	Recibe enlace para resetear	🟡
AUTH-05	Cierre de sesión	1. Estando logueado
2. Tocar "Cerrar sesión"	Vuelve a pantalla de login	🔴
AUTH-06	Token expirado	1. No usar app por >1 hora
2. Intentar registrar pago	Redirige a login automáticamente	🔴
2. Gestión de Clientes 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
CLI-01	Registrar cliente nuevo	1. Ir a Clientes → "+"
2. Completar campos obligatorios
3. Guardar	Cliente aparece en la lista	🔴
CLI-02	Registrar cliente sin email	1. Intentar guardar sin email	Mensaje: "Email es obligatorio"	🔴
CLI-03	Registrar cliente duplicado	1. Guardar mismo email dos veces	Mensaje: "Email ya registrado"	🟡
CLI-04	Buscar cliente por nombre	1. En Clientes, escribir "Juan"	Muestra solo clientes con "Juan"	🔴
CLI-05	Buscar cliente por teléfono	1. Escribir número parcial "555"	Muestra coincidencias	🟡
CLI-06	Editar cliente	1. Tocar cliente → Editar
2. Cambiar teléfono
3. Guardar	Datos actualizados en perfil	🔴
CLI-07	Suspender cliente	1. Editar cliente
2. Cambiar estado a "Suspendido"
3. Guardar	Cliente no puede recibir pagos nuevos	🟡
CLI-08	Ver perfil de cliente	1. Tocar cualquier cliente	Muestra todos sus datos + historial	🔴
CLI-09	Paginación de clientes	1. Tener >20 clientes
2. Desplazarse al final	Aparece botón "Cargar más"	🟢
CLI-10	Eliminar cliente (solo super_admin)	1. Siendo admin, ir a cliente
2. Tocar "Eliminar"
3. Confirmar	Cliente desaparece de la lista	🟡
3. Gestión de Pagos (Online) 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
PAY-01	Registrar pago exitoso	1. Buscar cliente activo
2. Tocar "Cobrar"
3. Confirmar monto
4. Seleccionar "Efectivo"
5. Registrar	✅ Pago registrado
✅ Membresía extendida
✅ Recibo generado	🔴
PAY-02	Registrar pago con monto incorrecto	1. Intentar modificar monto manual (si permitiera)	No debe permitir cambio o validar	🔴
PAY-03	Registrar pago a cliente moroso	1. Buscar cliente con membresía vencida
2. Registrar pago	✅ Pago registrado
✅ Fecha fin = hoy + duración plan	🔴
PAY-04	Registrar pago con tarjeta	1. Seleccionar método "Tarjeta"
2. Ingresar últimos 4 dígitos
3. Registrar	Guarda cardLast4 en métodoDetails	🟡
PAY-05	Registrar pago con transferencia	1. Seleccionar "Transferencia"
2. Ingresar referencia
3. Registrar	Guarda referencia en métodoDetails	🟡
PAY-06	Generar recibo después de pago	1. Registrar pago
2. Tocar "Ver recibo"	PDF/HTML con datos correctos	🔴
PAY-07	Ver historial de pagos	1. Ir a perfil de cliente
2. Ver sección "Historial"	Lista cronológica de pagos	🔴
PAY-08	Anular pago (solo admin)	1. En historial, tocar pago
2. Tocar "Anular"
3. Confirmar	Pago marcado como anulado
Membresía revierte? (discutible)	🟡
PAY-09	Número de recibo incremental	1. Registrar 3 pagos seguidos	Recibos: P-20260414-001, -002, -003	🔴
PAY-10	Pago con cliente inactivo	1. Intentar cobrar a cliente suspendido	Mensaje: "Cliente suspendido"	🔴
4. Gestión de Pagos (Offline) 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
OFF-01	Registrar pago sin internet	1. Desactivar WiFi/Datos
2. Registrar pago normal	✅ Pago se guarda localmente
✅ Ícono "pendiente de sincronizar"	🔴
OFF-02	Ver clientes offline	1. Sin internet
2. Abrir lista de clientes	Muestra clientes cacheados (últimos 200)	🔴
OFF-03	Sincronización automática al reconectar	1. Registrar 2 pagos offline
2. Activar internet
3. Esperar 10 segundos	Pagos aparecen en Firestore
Ícono de sincronización desaparece	🔴
OFF-04	Sincronización manual	1. Offline, registrar pagos
2. Con internet, ir a Configuración
3. Tocar "Sincronizar ahora"	Fuerza sincronización inmediata	🟡
OFF-05	Conflicto: mismo cliente, dos pagos offline	1. Cajero A registra pago offline (10:00)
2. Cajero B registra pago offline (10:05)
3. Sincronizan ambos	Prevalece el más reciente (10:05)
El otro se marca como conflicto	🔴
OFF-06	Conflicto: offline vs online posterior	1. Registrar pago online (10:00)
2. Cajero offline registra pago (09:55)
3. Sincronizar	Prevalece online (10:00)
Notificar conflicto al cajero	🟡
OFF-07	Límite de pagos offline	1. Registrar >100 pagos offline	No hay límite práctico (IndexedDB)	🟢
OFF-08	Persistencia offline después de cerrar app	1. Registrar pago offline
2. Cerrar app
3. Abrir app sin internet	Pago sigue pendiente	🔴
5. Reportes 🟡
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
REP-01	Ver clientes morosos	1. Tener cliente con vencimiento < hoy
2. Ir a Reportes → Morosos	Aparece en la lista con días de retraso	🔴
REP-02	Filtrar morosos por sede	1. Tener morosos en Sede Norte y Sur
2. Filtrar "Sede Norte"	Solo muestra morosos de Sede Norte	🟡
REP-03	Reporte de ingresos diarios	1. Registrar pagos en diferentes días
2. Ver gráfico	Barras con montos correctos	🔴
REP-04	Reporte por método de pago	1. Registrar pagos con efectivo, tarjeta
2. Ver reporte	Porcentajes: efectivo 60%, tarjeta 40%	🟡
REP-05	Exportar a Excel	1. En cualquier reporte
2. Tocar "Exportar"	Descarga archivo .csv con datos	🟢
REP-06	Dashboard con métricas correctas	1. Registrar pagos hoy
2. Ver dashboard	"Ingresos hoy" coincide con suma	🔴
REP-07	Próximos vencimientos	1. Tener cliente que vence en 2 días
2. Ver dashboard	Aparece en "Próximos vencimientos"	🟡
6. Roles y Permisos 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
ROL-01	Super Admin ve todas las sedes	1. Login con admin@test.com
2. Ver dashboard	Muestra datos de todas las sedes	🔴
ROL-02	Admin de sede ve solo su sede	1. Login con admin_sede@test.com (Sede Norte)
2. Buscar cliente de Sede Sur	No aparece cliente de otra sede	🔴
ROL-03	Cajero NO puede editar clientes	1. Login con cashier@test.com
2. Ir a cliente
3. Buscar botón "Editar"	Botón no visible o deshabilitado	🔴
ROL-04	Cajero SÍ puede registrar pagos	1. Login con cashier@test.com
2. Ir a cliente
3. Botón "Cobrar"	Visible y funcional	🔴
ROL-05	Entrenador solo puede ver clientes	1. Login con trainer@test.com
2. Ver clientes	✅ Puede ver lista
❌ No puede cobrar
❌ No puede editar	🔴
ROL-06	Entrenador ve solvencia	1. Login trainer
2. Ver cliente moroso	Indicador rojo visible	🟡
ROL-07	Super Admin puede crear empleados	1. Login admin
2. Configuración → Usuarios → Invitar	Puede agregar nuevos	🔴
ROL-08	Cajero NO puede crear empleados	1. Login cashier
2. Buscar "Usuarios" en menú	Opción no visible	🔴
ROL-09	Admin sede NO puede ver reportes de otra sede	1. Login admin_sede Norte
2. Intentar ver reporte de Sede Sur	Datos vacíos o error 403	🟡
7. Sincronización Offline 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
SYNC-01	Sincronización batch de 10 pagos	1. Registrar 10 pagos offline
2. Conectar internet
3. Medir tiempo	< 5 segundos para 10 pagos	🔴
SYNC-02	Preservar orden de pagos	1. Registrar pagos offline: A (10:00), B (10:05)
2. Sincronizar	En Firestore, A tiene createdAt 10:00, B 10:05	🔴
SYNC-03	No duplicar pagos	1. Registrar pago offline
2. Sincronizar
3. Sincronizar nuevamente	Pago aparece una sola vez	🔴
SYNC-04	Indicador visual de sincronización	1. Registrar pago offline
2. Ver ícono	Ícono de "nube con flecha"	🟡
SYNC-05	Sincronización automática en background	1. Registrar pagos offline
2. Dejar app en segundo plano
3. Volver después de 1 min	Pagos ya sincronizados	🟢
SYNC-06	Manejo de red intermitente	1. Registrar pago
2. Conectar/desconectar WiFi varias veces	Eventualmente sincroniza	🟡

Datos de prueba
Crear archivo test_data.json:

json
{
  "business": {
    "id": "test-gym",
    "name": "Gimnasio Test",
    "rubro": "gym"
  },
  "branches": [
    { "id": "sede-norte", "name": "Sede Norte" },
    { "id": "sede-sur", "name": "Sede Sur" }
  ],
  "plans": [
    { "id": "plan-mensual", "name": "Mensual", "price": 35000, "durationDays": 30 },
    { "id": "plan-trimestral", "name": "Trimestral", "price": 90000, "durationDays": 90 }
  ],
  "clients": [
    { "name": "Juan Pérez", "email": "juan@test.com", "branchId": "sede-norte", "membershipPlanId": "plan-mensual" },
    { "name": "María López", "email": "maria@test.com", "branchId": "sede-norte", "membershipPlanId": "plan-trimestral" }
  ],
  "users": [
    { "email": "admin@test.com", "role": "super_admin" },
    { "email": "cashier@test.com", "role": "cashier", "branchId": "sede-norte" }
  ]
}
✅ Casos de prueba por módulo
1. Autenticación 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
AUTH-01	Login exitoso	1. Ingresar email válido
2. Ingresar contraseña correcta
3. Tocar "Iniciar sesión"	Redirige al Dashboard	🔴
AUTH-02	Login fallido (contraseña incorrecta)	1. Ingresar email válido
2. Ingresar contraseña incorrecta
3. Tocar "Iniciar sesión"	Mensaje: "Contraseña incorrecta"	🔴
AUTH-03	Login fallido (usuario no existe)	1. Ingresar email no registrado
2. Cualquier contraseña
3. Tocar "Iniciar sesión"	Mensaje: "Usuario no encontrado"	🔴
AUTH-04	Recuperar contraseña	1. Tocar "¿Olvidaste tu contraseña?"
2. Ingresar email
3. Revisar correo	Recibe enlace para resetear	🟡
AUTH-05	Cierre de sesión	1. Estando logueado
2. Tocar "Cerrar sesión"	Vuelve a pantalla de login	🔴
AUTH-06	Token expirado	1. No usar app por >1 hora
2. Intentar registrar pago	Redirige a login automáticamente	🔴
2. Gestión de Clientes 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
CLI-01	Registrar cliente nuevo	1. Ir a Clientes → "+"
2. Completar campos obligatorios
3. Guardar	Cliente aparece en la lista	🔴
CLI-02	Registrar cliente sin email	1. Intentar guardar sin email	Mensaje: "Email es obligatorio"	🔴
CLI-03	Registrar cliente duplicado	1. Guardar mismo email dos veces	Mensaje: "Email ya registrado"	🟡
CLI-04	Buscar cliente por nombre	1. En Clientes, escribir "Juan"	Muestra solo clientes con "Juan"	🔴
CLI-05	Buscar cliente por teléfono	1. Escribir número parcial "555"	Muestra coincidencias	🟡
CLI-06	Editar cliente	1. Tocar cliente → Editar
2. Cambiar teléfono
3. Guardar	Datos actualizados en perfil	🔴
CLI-07	Suspender cliente	1. Editar cliente
2. Cambiar estado a "Suspendido"
3. Guardar	Cliente no puede recibir pagos nuevos	🟡
CLI-08	Ver perfil de cliente	1. Tocar cualquier cliente	Muestra todos sus datos + historial	🔴
CLI-09	Paginación de clientes	1. Tener >20 clientes
2. Desplazarse al final	Aparece botón "Cargar más"	🟢
CLI-10	Eliminar cliente (solo super_admin)	1. Siendo admin, ir a cliente
2. Tocar "Eliminar"
3. Confirmar	Cliente desaparece de la lista	🟡
3. Gestión de Pagos (Online) 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
PAY-01	Registrar pago exitoso	1. Buscar cliente activo
2. Tocar "Cobrar"
3. Confirmar monto
4. Seleccionar "Efectivo"
5. Registrar	✅ Pago registrado
✅ Membresía extendida
✅ Recibo generado	🔴
PAY-02	Registrar pago con monto incorrecto	1. Intentar modificar monto manual (si permitiera)	No debe permitir cambio o validar	🔴
PAY-03	Registrar pago a cliente moroso	1. Buscar cliente con membresía vencida
2. Registrar pago	✅ Pago registrado
✅ Fecha fin = hoy + duración plan	🔴
PAY-04	Registrar pago con tarjeta	1. Seleccionar método "Tarjeta"
2. Ingresar últimos 4 dígitos
3. Registrar	Guarda cardLast4 en métodoDetails	🟡
PAY-05	Registrar pago con transferencia	1. Seleccionar "Transferencia"
2. Ingresar referencia
3. Registrar	Guarda referencia en métodoDetails	🟡
PAY-06	Generar recibo después de pago	1. Registrar pago
2. Tocar "Ver recibo"	PDF/HTML con datos correctos	🔴
PAY-07	Ver historial de pagos	1. Ir a perfil de cliente
2. Ver sección "Historial"	Lista cronológica de pagos	🔴
PAY-08	Anular pago (solo admin)	1. En historial, tocar pago
2. Tocar "Anular"
3. Confirmar	Pago marcado como anulado
Membresía revierte? (discutible)	🟡
PAY-09	Número de recibo incremental	1. Registrar 3 pagos seguidos	Recibos: P-20260414-001, -002, -003	🔴
PAY-10	Pago con cliente inactivo	1. Intentar cobrar a cliente suspendido	Mensaje: "Cliente suspendido"	🔴
4. Gestión de Pagos (Offline) 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
OFF-01	Registrar pago sin internet	1. Desactivar WiFi/Datos
2. Registrar pago normal	✅ Pago se guarda localmente
✅ Ícono "pendiente de sincronizar"	🔴
OFF-02	Ver clientes offline	1. Sin internet
2. Abrir lista de clientes	Muestra clientes cacheados (últimos 200)	🔴
OFF-03	Sincronización automática al reconectar	1. Registrar 2 pagos offline
2. Activar internet
3. Esperar 10 segundos	Pagos aparecen en Firestore
Ícono de sincronización desaparece	🔴
OFF-04	Sincronización manual	1. Offline, registrar pagos
2. Con internet, ir a Configuración
3. Tocar "Sincronizar ahora"	Fuerza sincronización inmediata	🟡
OFF-05	Conflicto: mismo cliente, dos pagos offline	1. Cajero A registra pago offline (10:00)
2. Cajero B registra pago offline (10:05)
3. Sincronizan ambos	Prevalece el más reciente (10:05)
El otro se marca como conflicto	🔴
OFF-06	Conflicto: offline vs online posterior	1. Registrar pago online (10:00)
2. Cajero offline registra pago (09:55)
3. Sincronizar	Prevalece online (10:00)
Notificar conflicto al cajero	🟡
OFF-07	Límite de pagos offline	1. Registrar >100 pagos offline	No hay límite práctico (IndexedDB)	🟢
OFF-08	Persistencia offline después de cerrar app	1. Registrar pago offline
2. Cerrar app
3. Abrir app sin internet	Pago sigue pendiente	🔴
5. Reportes 🟡
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
REP-01	Ver clientes morosos	1. Tener cliente con vencimiento < hoy
2. Ir a Reportes → Morosos	Aparece en la lista con días de retraso	🔴
REP-02	Filtrar morosos por sede	1. Tener morosos en Sede Norte y Sur
2. Filtrar "Sede Norte"	Solo muestra morosos de Sede Norte	🟡
REP-03	Reporte de ingresos diarios	1. Registrar pagos en diferentes días
2. Ver gráfico	Barras con montos correctos	🔴
REP-04	Reporte por método de pago	1. Registrar pagos con efectivo, tarjeta
2. Ver reporte	Porcentajes: efectivo 60%, tarjeta 40%	🟡
REP-05	Exportar a Excel	1. En cualquier reporte
2. Tocar "Exportar"	Descarga archivo .csv con datos	🟢
REP-06	Dashboard con métricas correctas	1. Registrar pagos hoy
2. Ver dashboard	"Ingresos hoy" coincide con suma	🔴
REP-07	Próximos vencimientos	1. Tener cliente que vence en 2 días
2. Ver dashboard	Aparece en "Próximos vencimientos"	🟡
6. Roles y Permisos 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
ROL-01	Super Admin ve todas las sedes	1. Login con admin@test.com
2. Ver dashboard	Muestra datos de todas las sedes	🔴
ROL-02	Admin de sede ve solo su sede	1. Login con admin_sede@test.com (Sede Norte)
2. Buscar cliente de Sede Sur	No aparece cliente de otra sede	🔴
ROL-03	Cajero NO puede editar clientes	1. Login con cashier@test.com
2. Ir a cliente
3. Buscar botón "Editar"	Botón no visible o deshabilitado	🔴
ROL-04	Cajero SÍ puede registrar pagos	1. Login con cashier@test.com
2. Ir a cliente
3. Botón "Cobrar"	Visible y funcional	🔴
ROL-05	Entrenador solo puede ver clientes	1. Login con trainer@test.com
2. Ver clientes	✅ Puede ver lista
❌ No puede cobrar
❌ No puede editar	🔴
ROL-06	Entrenador ve solvencia	1. Login trainer
2. Ver cliente moroso	Indicador rojo visible	🟡
ROL-07	Super Admin puede crear empleados	1. Login admin
2. Configuración → Usuarios → Invitar	Puede agregar nuevos	🔴
ROL-08	Cajero NO puede crear empleados	1. Login cashier
2. Buscar "Usuarios" en menú	Opción no visible	🔴
ROL-09	Admin sede NO puede ver reportes de otra sede	1. Login admin_sede Norte
2. Intentar ver reporte de Sede Sur	Datos vacíos o error 403	🟡
7. Sincronización Offline 🔴
ID	Caso de prueba	Pasos	Resultado esperado	Prioridad
SYNC-01	Sincronización batch de 10 pagos	1. Registrar 10 pagos offline
2. Conectar internet
3. Medir tiempo	< 5 segundos para 10 pagos	🔴
SYNC-02	Preservar orden de pagos	1. Registrar pagos offline: A (10:00), B (10:05)
2. Sincronizar	En Firestore, A tiene createdAt 10:00, B 10:05	🔴
SYNC-03	No duplicar pagos	1. Registrar pago offline
2. Sincronizar
3. Sincronizar nuevamente	Pago aparece una sola vez	🔴
SYNC-04	Indicador visual de sincronización	1. Registrar pago offline
2. Ver ícono	Ícono de "nube con flecha"	🟡
SYNC-05	Sincronización automática en background	1. Registrar pagos offline
2. Dejar app en segundo plano
3. Volver después de 1 min	Pagos ya sincronizados	🟢
SYNC-06	Manejo de red intermitente	1. Registrar pago
2. Conectar/desconectar WiFi varias veces	Eventualmente sincroniza	🟡
⚡ Pruebas de rendimiento
Escenarios de carga con k6
Instalar k6:

bash
# macOS
brew install k6

# Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
Archivo load_test.js:

javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },  // Subir a 20 usuarios
    { duration: '1m', target: 20 },   // Mantener 20 usuarios
    { duration: '10s', target: 0 },   // Bajar a 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% requests < 500ms
    http_req_failed: ['rate<0.01'],   // <1% de errores
  },
};

const BASE_URL = 'http://localhost:5000/api';
const TOKEN = 'eyJhbGciOiJSUzI1NiIs...'; // Token válido

export default function () {
  const headers = {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json',
  };

  // 1. Listar clientes
  let res = http.get(`${BASE_URL}/clients`, { headers });
  check(res, { 'clientes status 200': (r) => r.status === 200 });

  // 2. Registrar pago
  const payload = JSON.stringify({
    clientId: 'client-001',
    amount: 35000,
    method: 'cash',
    membershipPlanId: 'plan-mensual',
    branchId: 'sede-norte'
  });
  res = http.post(`${BASE_URL}/payments`, payload, { headers });
  check(res, { 'pago status 201': (r) => r.status === 201 });

  sleep(1);
}
Ejecutar prueba:

bash
k6 run load_test.js
Resultados esperados
Métrica	Umbral	Estado
Tiempo respuesta (p95)	< 500 ms	✅
Tasa de error	< 1%	✅
CPU backend	< 70%	✅
Memoria backend	< 512 MB	✅
Lecturas Firestore	< 50,000/día	✅
🔒 Pruebas de seguridad
ID	Prueba	Pasos	Resultado esperado
SEC-01	Acceso sin token	Llamar a API sin header Authorization	Error 401
SEC-02	Token inválido	Usar token falso "abc123"	Error 401
SEC-03	Token expirado	Usar token de hace 2 horas	Error 401
SEC-04	Escalada de privilegios	Cajero intenta llamar a DELETE /clients/:id	Error 403
SEC-05	Cross-sede access	Admin de Sede Norte intenta ver clientes de Sede Sur	Devuelve 0 resultados o error
SEC-06	SQL Injection (aunque no hay SQL)	Enviar ' OR '1'='1 en campo de búsqueda	Se escapa correctamente
SEC-07	XSS	Registrar cliente con <script>alert('XSS')</script>	Se sanitiza al mostrar
SEC-08	Rate limiting	Hacer 150 requests en 1 minuto	Error 429 después de 100 requests
🎨 Pruebas de usabilidad
Encuesta a 5 usuarios reales (dueños de gimnasio)
Preguntas:

¿Pudiste registrar un cliente en menos de 30 segundos?

¿Pudiste cobrar un pago en menos de 3 taps?

¿Entendiste qué significa el ícono de nube?

¿El tamaño de los botones es adecuado para dedos?

¿Encontraste el reporte de morosos sin ayuda?

Criterio de éxito: ≥80% respuestas positivas.

Tareas típicas con cronómetro
Tarea	Usuario objetivo	Tiempo máximo	Resultado
Registrar nuevo cliente	Cajero	45 segundos	✅
Cobrar pago a cliente existente	Cajero	15 segundos	✅
Ver quiénes deben pagar	Dueño	10 segundos	✅
Agregar nueva sede	Dueño	30 segundos	✅
📱 Pruebas de compatibilidad
Dispositivos móviles (PWA)
Dispositivo	OS	Navegador	Instalable	Offline	Pagos
iPhone 14	iOS 17	Safari	✅	✅	✅
iPhone SE	iOS 16	Safari	✅	✅	✅
Samsung S23	Android 14	Chrome	✅	✅	✅
Xiaomi Redmi	Android 13	Chrome	✅	✅	✅
Motorola G	Android 12	Chrome	✅	✅	✅
Navegadores de escritorio
Navegador	Versión	Funcionalidad
Chrome	120+	✅ Completa
Firefox	115+	✅ Completa
Safari	17+	✅ Completa
Edge	120+	✅ Completa
✅ Criterios de aceptación
Para lanzar MVP (release 1.0)
0 bugs críticos (pagos no se registran, pérdida de datos)

<3 bugs mayores (reporte incorrecto, UI rota)

100% de pruebas 🔴 (prioridad alta) pasan

>90% de pruebas 🟡 (prioridad media) pasan

Puede registrar pagos offline y sincronizar

Tiempo de carga inicial <3 segundos

PWA instalable en Android e iOS

Para producción estable (release 1.1)
0 bugs mayores

100% de todas las pruebas pasan

Prueba de carga: 50 usuarios concurrentes

Documentación actualizada

Backup automático configurado

🐛 Reporte de bugs (plantilla)
Copia y pega esto para reportar bugs:

markdown
## Título: [Breve descripción del problema]

**Gravedad:** (Crítica / Mayor / Menor / Sugerencia)

**Prioridad:** (Alta / Media / Baja)

**Entorno:**
- Dispositivo: [iPhone 14 / Samsung S23 / Chrome en Windows]
- OS: [iOS 17 / Android 14 / Windows 11]
- App versión: [1.0.0]

**Pasos para reproducir:**
1. 
2. 
3. 

**Resultado actual:**
[Qué ocurre]

**Resultado esperado:**
[Qué debería ocurrir]

**Evidencia:**
- [ ] Captura de pantalla
- [ ] Video
- [ ] Logs

**ID de sesión (si aplica):** `session_abc123`
Ejemplo de bug reportado
markdown
## Título: El recibo muestra fecha incorrecta al registrar pago después de medianoche

**Gravedad:** Mayor

**Prioridad:** Alta

**Entorno:**
- Dispositivo: iPhone 14
- OS: iOS 17.2
- App versión: 1.0.0

**Pasos para reproducir:**
1. Registrar un pago a las 00:05 AM del 15 de abril
2. Ver el recibo generado

**Resultado actual:**
El recibo muestra fecha 14 de abril (día anterior)

**Resultado esperado:**
Debe mostrar 15 de abril

**Evidencia:**
- [x] Captura de pantalla adjunta

**ID de sesión:** `session_20240415_001`
📊 Dashboard de pruebas (ejemplo)
Módulo	Pruebas totales	Pasadas	Fallidas	Bloqueadas	% éxito
Autenticación	6	6	0	0	100%
Clientes	10	9	1	0	90%
Pagos online	10	10	0	0	100%
Pagos offline	8	7	1	0	87.5%
Reportes	7	6	1	0	85.7%
Roles	9	9	0	0	100%
Sincronización	6	5	1	0	83.3%
TOTAL	56	52	4	0	92.8%
Estado: ✅ LISTO PARA LANZAR (supera 90%)

📝 Notas finales
Antes de cada release
bash
# 1. Correr pruebas unitarias
cd backend
pytest --cov=app tests/

# 2. Correr pruebas E2E
cd frontend
npm run test:e2e

# 3. Validar PWA
npm run build
npx lighthouse http://localhost:5000 --view --preset=performance

# 4. Prueba de carga (si aplica)
k6 run load_test.js