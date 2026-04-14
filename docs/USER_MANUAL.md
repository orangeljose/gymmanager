# GymManager - Manual de Usuario

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Primeros pasos](#primeros-pasos)
   - [Instalar la aplicación](#instalar-la-aplicación)
   - [Iniciar sesión](#iniciar-sesión)
   - [Recuperar contraseña](#recuperar-contraseña)
3. [Panel de control (Dashboard)](#panel-de-control-dashboard)
4. [Gestión de Clientes](#gestión-de-clientes)
   - [Registrar nuevo cliente](#registrar-nuevo-cliente)
   - [Buscar cliente](#buscar-cliente)
   - [Ver perfil de cliente](#ver-perfil-de-cliente)
   - [Editar cliente](#editar-cliente)
5. [Gestión de Pagos](#gestión-de-pagos)
   - [Registrar pago](#registrar-pago)
   - [Registrar pago sin internet](#registrar-pago-sin-internet)
   - [Ver historial de pagos](#ver-historial-de-pagos)
   - [Generar recibo](#generar-recibo)
6. [Reportes](#reportes)
   - [Clientes morosos](#clientes-morosos)
   - [Ingresos por día](#ingresos-por-día)
   - [Ingresos por método de pago](#ingresos-por-método-de-pago)
7. [Gestión de Sedes](#gestión-de-sedes)
   - [Agregar nueva sede](#agregar-nueva-sede)
   - [Editar sede](#editar-sede)
8. [Gestión de Usuarios (Empleados)](#gestión-de-usuarios-empleados)
   - [Agregar empleado](#agregar-empleado)
   - [Roles y permisos](#roles-y-permisos)
9. [Preguntas frecuentes](#preguntas-frecuentes)
10. [Soporte técnico](#soporte-técnico)

---

## 📱 Introducción

**GymManager** es una aplicación diseñada para administrar tu gimnasio de manera sencilla desde cualquier dispositivo. Puedes:

- ✅ Registrar clientes y sus membresías
- ✅ Cobrar pagos (incluso sin internet)
- ✅ Ver quién debe pagar (morosos)
- ✅ Administrar múltiples sedes
- ✅ Asignar roles a empleados (cajeros, entrenadores)

**Disponible para:** Celular, tablet o computadora.

---

## 🚀 Primeros pasos

### Instalar la aplicación

**En celular (Android/iPhone):**

1. Abre Chrome (Android) o Safari (iPhone)
2. Ve a la URL que te proporcionó el administrador (ej: `https://tu-gimnasio.firebaseapp.com`)
3. Aparecerá un mensaje: **"Instalar aplicación"**
4. Toca **"Instalar"**
5. Aparecerá un ícono en tu pantalla de inicio

**En computadora:**
- Solo abre el navegador y guarda el sitio en favoritos

> 💡 **Consejo:** La aplicación funciona sin internet. Los pagos que registres offline se sincronizarán automáticamente cuando vuelvas a tener conexión.

---

### Iniciar sesión

1. Abre la aplicación (ícono de GymManager)
2. Ingresa tu **correo electrónico** y **contraseña**
3. Toca **"Iniciar sesión"**

![Login screen description: Pantalla con campos de email y contraseña]

**¿No tienes cuenta?** Contacta al dueño del gimnasio para que te cree una.

---

### Recuperar contraseña

1. En la pantalla de login, toca **"¿Olvidaste tu contraseña?"**
2. Ingresa tu correo electrónico
3. Revisa tu bandeja de entrada (incluyendo spam)
4. Sigue el enlace para crear una nueva contraseña

---

## 📊 Panel de control (Dashboard)

Al iniciar sesión, verás el panel principal con:

| Elemento | Qué muestra |
|----------|-------------|
| **Clientes activos** | Número de clientes con membresía vigente |
| **Ingresos hoy** | Total cobrado en el día |
| **Morosos** | Clientes con membresía vencida |
| **Gráfico de ingresos** | Cobros de los últimos 7 días |
| **Próximos vencimientos** | Clientes que vencen en los próximos 3 días |

**Ejemplo de dashboard:**

╔══════════════════════════════════════════════╗
║ 🏋️ Gimnasio Central [Admin] ║
╠══════════════════════════════════════════════╣
║ ║
║ ┌──────────┐ ┌──────────┐ ┌──────────┐ ║
║ │ 145 │ │ $12,500 │ │ 23 │ ║
║ │ Clientes │ │ Hoy │ │ Morosos │ ║
║ │ activos │ │ │ │ │ ║
║ └──────────┘ └──────────┘ └──────────┘ ║
║ ║
║ 📈 Ingresos últimos 7 días ║
║ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ║
║ Lun Mar Mié Jue Vie Sáb Dom ║
║ ║
║ ⚠️ Próximos vencimientos (3 días) ║
║ • Juan Pérez - Vence mañana ║
║ • María López - Vence en 2 días ║
╚══════════════════════════════════════════════╝


---

## 👥 Gestión de Clientes

### Registrar nuevo cliente

**Rol requerido:** Administrador o Dueño

1. Ve a la pestaña **"Clientes"** (icono de personas)
2. Toca el botón **"+"** o **"Nuevo cliente"**
3. Completa el formulario:

| Campo | Obligatorio | Ejemplo |
|-------|-------------|---------|
| Nombre completo | ✅ | Juan Pérez García |
| Correo electrónico | ✅ | juan@email.com |
| Teléfono | ✅ | 555-123-4567 |
| Documento (INE/Cédula) | ❌ | ABC123456 |
| Sede | ✅ | Sede Norte |
| Plan de membresía | ✅ | Mensual ($350) |
| Notas | ❌ | Prefiere horario matutino |

4. Toca **"Guardar cliente"**

✅ **Cliente registrado automáticamente con membresía activa**

---

### Buscar cliente

1. Ve a **"Clientes"**
2. Usa el campo de búsqueda (lupa)
3. Escribe: **nombre**, **email** o **teléfono**
4. Los resultados aparecen en tiempo real

**Ejemplo:** Buscar "Juan" muestra todos los Juanes registrados.

---

### Ver perfil de cliente

1. Toca sobre cualquier cliente en la lista
2. Verás:
   - Datos personales (nombre, email, teléfono)
   - Estado de membresía (verde = al día, rojo = vencido)
   - Fecha de vencimiento
   - Historial de pagos
   - Botón **"Registrar pago"**

---

### Editar cliente

**Rol requerido:** Administrador o Dueño

1. Ve al perfil del cliente
2. Toca el ícono de **"Editar"** (lápiz)
3. Modifica los campos necesarios
4. Toca **"Guardar cambios"**

**Nota:** No puedes editar el historial de pagos (solo agregar nuevos pagos).

---

## 💰 Gestión de Pagos

### Registrar pago

**Rol requerido:** Cajero, Administrador o Dueño

**Método rápido (recomendado):**

1. Desde el **Dashboard**, toca el botón **"💵 Cobrar"** (grande, color verde)
2. Busca al cliente (escribe su nombre)
3. Confirma el monto (se muestra automáticamente según su plan)
4. Selecciona **método de pago**:
   - Efectivo
   - Tarjeta (crédito/débito)
   - Transferencia
   - Otro
5. (Opcional) Agrega notas (ej: "Pagó con $500, cambio $150")
6. Toca **"Registrar pago"**

✅ **La membresía se extiende automáticamente según el plan**

**Desde perfil de cliente:**

1. Ve al perfil del cliente
2. Toca **"Registrar pago"**
3. Sigue los mismos pasos

---

### Registrar pago sin internet

**¡GymManager funciona OFFLINE!**

Si no tienes internet en el gimnasio:

1. Registra el pago normalmente (la app no te pedirá conexión)
2. El pago se guarda en tu dispositivo
3. Cuando vuelvas a tener internet, la app sincronizará automáticamente

**Indicadores:**
- 📱 **Ícono de nube tachada** = Estás offline
- 📱 **Ícono de sincronización** = Enviando pagos pendientes

> ⚠️ **Importante:** Los pagos offline se sincronizan en orden. Si dos cajeros registran el mismo cliente offline, el sistema mantiene el más reciente.

---

### Ver historial de pagos

1. Ve al perfil del cliente
2. Desplázate hacia abajo a la sección **"Historial de pagos"**
3. Verás una lista con:

| Fecha | Monto | Método | Recibo | Vigencia |
|-------|-------|--------|--------|----------|
| 14/04/2026 | $350 | Efectivo | #001 | 14/04 - 14/05 |
| 14/03/2026 | $350 | Tarjeta | #002 | 14/03 - 14/04 |

---

### Generar recibo

Después de registrar un pago:

1. Aparecerá una pantalla con **"Pago registrado exitosamente"**
2. Toca **"Ver recibo"**
3. Puedes:
   - **Compartir** por WhatsApp/Email
   - **Imprimir** (si estás en computadora)
   - **Guardar como PDF**

**Ejemplo de recibo:**

╔════════════════════════════════════════╗
║ GIMNASIO CENTRAL ║
║ Sede Norte ║
║ Av. Principal 123 ║
╠════════════════════════════════════════╣
║ RECIBO: #GYM-20260414-001 ║
║ FECHA: 14/04/2026 10:30 AM ║
║ ║
║ CLIENTE: Juan Pérez ║
║ PLAN: Mensual ║
║ MONTO: $350.00 MXN ║
║ MÉTODO: Efectivo ║
║ ║
║ VIGENCIA: 14/04/2026 al 14/05/2026 ║
║ ║
║ CAJERO: María González ║
║ ║
║ ¡Gracias por tu pago! ║
╚════════════════════════════════════════╝


---

## 📈 Reportes

### Clientes morosos

**Rol requerido:** Administrador o Dueño

1. Ve a la pestaña **"Reportes"** (icono de gráfico)
2. Toca **"Clientes morosos"**
3. Verás lista de clientes con membresía vencida:

| Cliente | Vencido hace | Teléfono | Último pago |
|---------|--------------|----------|-------------|
| Carlos Ruiz | 7 días | 555-1234 | $350 (07/03) |
| Ana Torres | 3 días | 555-5678 | $350 (10/03) |

4. Puedes:
   - Llamar directamente (tocar teléfono)
   - Enviar mensaje por WhatsApp
   - Filtrar por sede

---

### Ingresos por día

1. **Reportes** → **"Ingresos diarios"**
2. Selecciona un rango de fechas (ej: 1 al 30 de abril)
3. Verás gráfico de barras con:

$12,000 ┤ ┌───┐
$10,000 ┤ │ │
$ 8,000 ┤ ┌───┐│ │
$ 6,000 ┤ │ ││ │┌───┐
$ 4,000 ┤┌──┐│ ││ ││ │
$ 2,000 ┤│ ││ ││ ││ │
$ 0 └┴──┴┴───┴┴───┴┴───┴──
1 2 3 4 5 (día)


4. Toca cualquier barra para ver los pagos de ese día

---

### Ingresos por método de pago

1. **Reportes** → **"Por método de pago"**
2. Verás un gráfico circular:

Efectivo (60%)
╭─────────────────╮
│ ████████████ │ $21,000
│ ██ │
│ ██ Tarjeta │
│ ██ (25%) │ $8,750
│ ██ │
╰─────────────────╯
Transferencia (15%) = $5,250


---

## 🏢 Gestión de Sedes

**Rol requerido:** Dueño (Super Admin)

### Agregar nueva sede

1. Ve a **"Configuración"** (icono de engranaje)
2. Toca **"Sedes"**
3. Toca **"Agregar sede"**
4. Completa:

| Campo | Ejemplo |
|-------|---------|
| Nombre | Sede Sur |
| Dirección | Calle Secundaria 456, Col. Centro |
| Teléfono | 555-9876 |

5. Toca **"Guardar"**

✅ **Nueva sede creada. Ahora puedes asignar clientes y empleados a esta sede**

---

### Editar sede

1. **Configuración** → **"Sedes"**
2. Toca la sede que quieres modificar
3. Edita los campos necesarios
4. Toca **"Guardar cambios"**

**Nota:** Si desactivas una sede, los clientes seguirán existiendo pero no podrás registrar nuevos pagos en ella.

---

## 👔 Gestión de Usuarios (Empleados)

**Rol requerido:** Dueño (Super Admin)

### Agregar empleado

1. Ve a **"Configuración"** → **"Usuarios"**
2. Toca **"Invitar empleado"**
3. Completa:

| Campo | Ejemplo |
|-------|---------|
| Nombre | María González |
| Correo | maria@gimnasio.com |
| Rol | Cajero |
| Sede | Sede Norte |

4. Toca **"Enviar invitación"**

✅ **El empleado recibe un correo para crear su contraseña**

---

### Roles y permisos

| Rol | Qué puede hacer |
|-----|-----------------|
| **Dueño (Super Admin)** | Todo: ver todas las sedes, agregar empleados, editar configuraciones, ver todos los reportes |
| **Administrador de sede** | Ver y editar clientes de su sede, registrar pagos, ver reportes de su sede |
| **Cajero** | Ver clientes (solo lectura), registrar pagos, NO puede editar clientes ni ver reportes financieros |
| **Entrenador** | Solo ver clientes y su estado de pago (no puede cobrar) |

**Ejemplo práctico:**
- Dueño: Ve todas las sedes
- Admin sede Norte: Solo ve clientes de sede Norte
- Cajero: Solo puede cobrar, no puede eliminar clientes
- Entrenador: Ve qué clientes están morosos para no dejarlos pasar

---

### Editar o desactivar empleado

1. **Configuración** → **"Usuarios"**
2. Toca el empleado
3. Puedes:
   - Cambiar su rol
   - Cambiar su sede
   - **Desactivar** (ya no podrá iniciar sesión)

---

## ❓ Preguntas frecuentes

### 1. ¿Qué hago si la app no sincroniza los pagos offline?

**Solución:**
1. Verifica que tengas internet (abre Google.com)
2. Cierra y abre la app
3. Ve a **Configuración** → **"Sincronizar ahora"**
4. Espera unos segundos

### 2. ¿Puedo cobrar un monto diferente al plan?

No, el sistema está diseñado para cobrar exactamente el precio del plan. Si necesitas un descuento o cobro especial, contacta al administrador.

### 3. ¿Qué pasa si cobro por error a un cliente?

1. Ve al perfil del cliente
2. En el historial de pagos, toca el pago incorrecto
3. Toca **"Anular pago"** (solo administradores)
4. Registra el pago correcto

### 4. ¿Cómo veo cuánto dinero lleva el día?

En el **Dashboard** (pantalla principal), la tarjeta **"Ingresos hoy"** muestra el total acumulado.

### 5. ¿Puedo usar la app en mi tablet?

¡Sí! La app se adapta a cualquier pantalla. Instálala igual que en el celular.

### 6. ¿Los clientes pueden ver su estado?

No en esta versión. Solo los empleados del gimnasio tienen acceso.

### 7. ¿Qué hago si un cliente cambia de plan (ej: de mensual a trimestral)?

1. Ve al perfil del cliente
2. Edita su información
3. Cambia el campo **"Plan"** al nuevo
4. Registra el pago correspondiente

### 8. ¿Puedo exportar los reportes a Excel?

Sí:
1. Ve al reporte que quieras
2. Toca el botón **"Exportar"** (icono de hoja de cálculo)
3. Se descargará un archivo `.csv` que puedes abrir con Excel

---

## 📞 Soporte técnico

### ¿Necesitas ayuda?

| Problema | Contacto |
|----------|----------|
| **Error técnico** (la app no funciona) | soporte@gymmanager.com |
| **Olvidé mi contraseña** | Usa "¿Olvidaste tu contraseña?" en la pantalla de login |
| **Quiero agregar una nueva sede** | Solo el dueño puede hacerlo desde Configuración |
| **Facturación / planes** | ventas@gymmanager.com |

### Tiempos de respuesta

- Correo electrónico: 24 horas
- Emergencias (app caída): +52 555 123 4567 (9 AM - 6 PM)

### Reportar un bug

Si encuentras un error:

1. Toma captura de pantalla
2. Describe qué estabas haciendo
3. Envía a: bugs@gymmanager.com
4. Incluye:
   - Tu nombre
   - Sede
   - Dispositivo (iPhone 12, Samsung S21, etc.)

---

## 📝 Notas de versión

**Versión 1.0.0 (MVP) - Abril 2026**

- ✅ Registro de clientes
- ✅ Cobros online y offline
- ✅ Reporte de morosos
- ✅ Múltiples sedes
- ✅ Roles: Dueño, Admin, Cajero, Entrenador
- ✅ Instalable como app (PWA)

**Próximas funciones (versión 2.0):**
- Envío de recordatorios por WhatsApp
- Escaneo de código QR para registrar ingreso
- Múltiples monedas
- Reportes avanzados con gráficos interactivos

---

**¡Gracias por usar GymManager! 💪**

*¿Tienes sugerencias para mejorar este manual? Escríbenos a docs@gymmanager.com*