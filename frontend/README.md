# GymManager Frontend

Frontend de la aplicación GymManager - Sistema de gestión de gimnasios con PWA, modo offline y sincronización automática.

## Características

- **React 18+** con TypeScript y Vite
- **PWA** con service worker y caching (Workbox)
- **Firebase Auth** para autenticación
- **Dexie.js** para almacenamiento offline (IndexedDB)
- **TailwindCSS** para estilos personalizados
- **React Router** para navegación y rutas protegidas
- **React Hook Form** para formularios
- **Zustand** para estado global
- **React Hot Toast** para notificaciones
- **Modo offline** con sincronización automática
- **Diseño responsive** y moderno

## Requisitos Previos

- Node.js 18+ 
- npm o yarn
- Firebase project configurado
- Backend API corriendo

## Instalación

1. **Clonar el repositorio** (si no está hecho):
```bash
git clone <repository-url>
cd gymmanager/frontend
```

2. **Instalar dependencias**:
```bash
npm install
# o
yarn install
```

3. **Configurar variables de entorno**:
```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:
```env
# Firebase Configuration
VITE_FIREBASE_API_KEY=tu_api_key
VITE_FIREBASE_AUTH_DOMAIN=tu_auth_domain
VITE_FIREBASE_PROJECT_ID=tu_project_id
VITE_FIREBASE_STORAGE_BUCKET=tu_storage_bucket
VITE_FIREBASE_MESSAGING_SENDER_ID=tu_sender_id
VITE_FIREBASE_APP_ID=tu_app_id

# API Configuration
VITE_API_BASE_URL=http://localhost:8000

# App Configuration
VITE_APP_NAME=GymManager
VITE_APP_VERSION=1.0.0
VITE_ENABLE_OFFLINE=true
```

## Configuración de Firebase

1. Ve a la [Consola de Firebase](https://console.firebase.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita **Authentication** -> **Email/Password**
4. Habilita **Firestore Database**
5. Copia las credenciales al archivo `.env`

## Ejecución

### Modo Desarrollo
```bash
npm run dev
# o
yarn dev
```

La aplicación estará disponible en `http://localhost:5173`

### Modo Producción
```bash
npm run build
npm run preview
# o
yarn build
yarn preview
```

## Scripts Disponibles

- `npm run dev` - Iniciar servidor de desarrollo
- `npm run build` - Compilar para producción
- `npm run preview` - Previsualizar build de producción
- `npm run lint` - Ejecutar ESLint
- `npm run type-check` - Verificar tipos TypeScript

## Estructura del Proyecto

```
src/
|-- components/          # Componentes reutilizables
|   |-- Layout.tsx
|   |-- ProtectedRoute.tsx
|   |-- OfflineIndicator.tsx
|-- hooks/              # Custom hooks
|   |-- useAuth.ts
|   |-- useOffline.ts
|   |-- useClients.ts
|-- pages/              # Páginas de la aplicación
|   |-- LoginPage.tsx
|   |-- DashboardPage.tsx
|   |-- ClientsPage.tsx
|   |-- ...
|-- services/           # Servicios y API
|   |-- api.ts
|   |-- firebase.ts
|   |-- offlineService.ts
|-- types/              # Tipos TypeScript
|   |-- index.ts
|-- App.tsx             # Componente principal
|-- main.tsx            # Punto de entrada
|-- index.css           # Estilos globales
```

## Características PWA

La aplicación es una **Progressive Web App** con:

- **Instalable** en dispositivos móviles
- **Funciona offline** con sincronización automática
- **Notificaciones push** (configurable)
- **Caching inteligente** de recursos
- **Shortcuts** para acciones rápidas

## Modo Offline

- **Clientes**: Cache local de últimos 200 clientes
- **Pagos**: Guardar pagos pendientes offline
- **Sincronización**: Automática al reconectar
- **Conflictos**: Resolución por timestamp

## Roles y Permisos

- **super_admin**: Acceso completo a todas las funciones
- **branch_admin**: Administración de sucursal específica
- **cashier**: Registro de pagos y gestión de clientes
- **trainer**: Gestión básica de clientes

## Rutas de la Aplicación

### Públicas
- `/login` - Inicio de sesión

### Protegidas
- `/dashboard` - Panel principal
- `/clients` - Lista de clientes
- `/clients/:id` - Detalle de cliente
- `/clients/new` - Nuevo cliente
- `/reports` - Reportes
- `/admin` - Administración (solo super_admin)

## Desarrollo

### Agregar Nuevas Páginas

1. Crear componente en `src/pages/`
2. Agregar ruta en `src/App.tsx`
3. Proteger con `ProtectedRoute` si es necesario

### Agregar Nuevos Componentes

1. Crear en `src/components/`
2. Exportar y usar donde sea necesario
3. Seguir convención de nombres PascalCase

### Estilos Personalizados

- Editar `src/index.css` para estilos globales
- Editar `tailwind.config.js` para configuración Tailwind
- Usar clases de Tailwind para componentes

## Build y Deploy

### Build para Producción
```bash
npm run build
```

### Deploy en Vercel
```bash
npm install -g vercel
vercel --prod
```

### Deploy en Netlify
```bash
npm run build
# Subir carpeta dist/ a Netlify
```

## Problemas Comunes

### TypeScript Errors
Los errores de TypeScript son normales antes de instalar dependencias. Después de `npm install` deberían desaparecer.

### Firebase Connection
- Verificar credenciales en `.env`
- Habilitar Email/Password en Firebase Auth
- Configurar Firestore rules

### Offline Mode
- Verificar que `VITE_ENABLE_OFFLINE=true`
- Usar browser compatible con IndexedDB
- Limpiar cache si hay problemas

## Soporte

Para reportar issues o solicitar características:
1. Crear issue en el repositorio
2. Describir el problema detalladamente
3. Incluir logs y screenshots si es posible

## Licencia

MIT License - Ver archivo LICENSE para detalles
