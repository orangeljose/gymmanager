# GymManager - Deployment Guide

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Estrategia de Despliegue](#estrategia-de-despliegue)
3. [Backend - Flask en producción](#backend---flask-en-producción)
   - [Opción A: Render.com (Recomendado para MVP)](#opción-a-rendercom-recomendado-para-mvp)
   - [Opción B: Google Cloud Run](#opción-b-google-cloud-run)
   - [Opción C: Railway.app (Alternativa simple)](#opción-c-railwayapp-alternativa-simple)
4. [Frontend - React PWA](#frontend---react-pwa)
   - [Build de producción](#build-de-producción)
   - [Firebase Hosting (Recomendado)](#firebase-hosting-recomendado)
   - [Vercel / Netlify (Alternativa)](#vercel--netlify-alternativa)
5. [Configuración de Firebase para Producción](#configuración-de-firebase-para-producción)
   - [Reglas de seguridad definitivas](#reglas-de-seguridad-definitivas)
   - [Variables de entorno](#variables-de-entorno)
6. [CI/CD con GitHub Actions](#cicd-con-github-actions)
7. [Monitoreo y Logs](#monitoreo-y-logs)
8. [Checklist de lanzamiento](#checklist-de-lanzamiento)
9. [Solución de problemas comunes](#solución-de-problemas-comunes)

---

## 📦 Requisitos Previos

Antes de desplegar, asegúrate de tener:

- [ ] Cuenta en [Firebase](https://console.firebase.google.com/) (plan Blaze recomendado para producción)
- [ ] Cuenta en [GitHub](https://github.com/) (para CI/CD)
- [ ] Dominio propio (opcional, pero recomendado)
- [ ] Clave de servicio de Firebase (`serviceAccountKey.json`)
- [ ] Proyecto probado localmente

---

## 🎯 Estrategia de Despliegue

### Arquitectura objetivo
┌─────────────────┐
│ Usuario final │
└────────┬────────┘
│ HTTPS
┌────────▼────────┐
│ Firebase Hosting│ ← Frontend (React PWA)
│ (CDN global) │
└────────┬────────┘
│ API calls
┌────────▼────────┐
│ Render.com │ ← Backend (Flask)
│ o Cloud Run │
└────────┬────────┘
│
┌────────▼────────┐
│ Firestore │ ← Base de datos
│ (Firebase) │
└─────────────────┘


### Costos mensuales estimados (producción baja)

| Servicio | Plan | Costo mensual |
|----------|------|---------------|
| Firebase Hosting | Blaze (pago por uso) | ~$0 (dentro del free tier) |
| Firestore | Blaze | ~$0 - $5 (dependiendo de uso) |
| Render.com | Starter ($7/mes) o Free tier | $0 - $7 |
| Dominio .com | Cloudflare | ~$10/año |
| **Total estimado** | | **$0 - $15/mes** |

---

## 🐍 Backend - Flask en producción

### Opción A: Render.com (Recomendado para MVP)

**Ventajas:** Free tier disponible, fácil configuración, auto HTTPS.

#### Paso 1: Preparar el backend

```bash
# Estructura que debe tener tu backend/
backend/
├── app.py
├── requirements.txt
├── runtime.txt          # Especifica versión de Python
├── .env                 # NO subir a git
├── serviceAccountKey.json  # NO subir a git
└── ...
Crear runtime.txt:

text
python-3.11.8
Crear render.yaml (opcional, para despliegue automático):

yaml
services:
  - type: web
    name: gymmanager-api
    runtime: python
    repo: https://github.com/tuusuario/gymmanager
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: FLASK_ENV
        value: production
      - key: FIREBASE_CREDENTIALS_JSON
        value: '{"type":"service_account","project_id":"tu-proyecto","private_key":"-----BEGIN PRIVATE KEY-----\n...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"..."}'
      - key: CORS_ORIGINS
        value: https://tu-app.firebaseapp.com
Paso 2: Subir a GitHub
bash
# Crear .gitignore para no subir secretos
echo "serviceAccountKey.json" >> .gitignore
echo ".env" >> .gitignore

git init
git add .
git commit -m "Initial backend commit"
git branch -M main
git remote add origin https://github.com/tuusuario/gymmanager-backend.git
git push -u origin main
Paso 3: Desplegar en Render
Ve a render.com y crea una cuenta (con GitHub)

Haz clic en "New +" → "Web Service"

Conecta tu repositorio de GitHub

Configura:

Name: gymmanager-api

Environment: Python

Build Command: pip install -r requirements.txt

Start Command: gunicorn app:app

Agrega variables de entorno:

FLASK_ENV: production

CORS_ORIGINS: https://tu-app.firebaseapp.com

Sube serviceAccountKey.json manualmente:

En Render: Dashboard → Secrets → Add Secret

Nombre: FIREBASE_CREDENTIALS

Valor: (contenido del archivo JSON)

Haz clic en "Create Web Service"

✅ URL de tu API: https://gymmanager-api.onrender.com

Opción B: Google Cloud Run (Más escalable)
Ventajas: Mejor integración con Firebase, autoescalado.

bash
# 1. Instalar Google Cloud SDK
curl https://sdk.cloud.google.com | bash
gcloud init

# 2. Crear Dockerfile
Dockerfile:

dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

COPY . .

ENV FLASK_ENV=production
ENV PORT=8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
bash
# 3. Construir y subir imagen
gcloud builds submit --tag gcr.io/tu-proyecto/gymmanager-api

# 4. Desplegar en Cloud Run
gcloud run deploy gymmanager-api \
  --image gcr.io/tu-proyecto/gymmanager-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars "FLASK_ENV=production"
Opción C: Railway.app (Alternativa simple)
bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. En la raíz del backend
railway init

# 4. Desplegar
railway up

# 5. Agregar variables de entorno (por web o CLI)
railway variables set FLASK_ENV=production
railway variables set CORS_ORIGINS=https://tu-app.firebaseapp.com
⚛️ Frontend - React PWA
Build de producción
bash
# 1. Configurar variables de entorno para producción
# Crear .env.production en frontend/
.env.production:

env
VITE_API_URL=https://gymmanager-api.onrender.com/api
VITE_FIREBASE_API_KEY=tu_api_key
VITE_FIREBASE_AUTH_DOMAIN=tu-proyecto.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=tu-proyecto
VITE_FIREBASE_STORAGE_BUCKET=tu-proyecto.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abcdef
bash
# 2. Buildear la app
cd frontend
npm run build

# 3. Verificar el build
ls -la dist/
# Debe incluir index.html, assets/, manifest.json, service-worker.js
Firebase Hosting (Recomendado)
Ventajas: CDN global, SSL gratis, integración perfecta con Firebase.

Paso 1: Instalar Firebase CLI
bash
npm install -g firebase-tools
firebase login
Paso 2: Inicializar Hosting
bash
# En la raíz del proyecto (no dentro de frontend/)
firebase init hosting

# Seleccionar:
# - Project: gymmanager-v1
# - Public directory: frontend/dist
# - Configure as single-page app: Yes
# - Set up automatic builds with GitHub: No (por ahora)
# - Overwrite index.html: No
Paso 3: Desplegar
bash
# Build primero
cd frontend && npm run build && cd ..

# Desplegar
firebase deploy --only hosting

# 🔥 URL: https://tu-proyecto.firebaseapp.com
Paso 4: (Opcional) Conectar dominio personalizado
Firebase Console → Hosting → Agregar dominio personalizado

Verificar propiedad del dominio (Google Search Console)

Actualizar DNS (agregar registro TXT y CNAME)

Esperar propagación (minutos a horas)

Vercel / Netlify (Alternativa)
Vercel:

bash
# 1. Instalar Vercel CLI
npm install -g vercel

# 2. En frontend/
vercel

# 3. Configurar:
# - Link to existing project? No
# - Project name: gymmanager
# - Directory: ./
# - Override settings? No

# 4. Para producción
vercel --prod
Netlify:

bash
# 1. Instalar Netlify CLI
npm install -g netlify-cli

# 2. Build y deploy
cd frontend
npm run build
netlify deploy --prod --dir=dist

# 3. Configurar redirects para SPA
# Crear frontend/dist/_redirects
echo "/* /index.html 200" > frontend/dist/_redirects
🔧 Configuración de Firebase para Producción
Reglas de seguridad definitivas
Antes de lanzar a producción, actualiza las reglas de Firestore:

javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Helper functions
    function isAuthenticated() {
      return request.auth != null;
    }
    
    function getUserRole() {
      let userDoc = get(/databases/$(database)/documents/users/$(request.auth.uid));
      return userDoc.data.role;
    }
    
    function getUserBusinessId() {
      let userDoc = get(/databases/$(database)/documents/users/$(request.auth.uid));
      return userDoc.data.businessId;
    }
    
    function hasRole(requiredRole) {
      return isAuthenticated() && getUserRole() == requiredRole;
    }
    
    function hasAnyRole(roles) {
      return isAuthenticated() && roles.contains(getUserRole());
    }
    
    function belongsToBusiness(docBusinessId) {
      return isAuthenticated() && docBusinessId == getUserBusinessId();
    }
    
    // BUSINESSES
    match /businesses/{business} {
      allow read: if isAuthenticated();
      allow write: if hasRole('super_admin');
    }
    
    // BRANCHES
    match /branches/{branch} {
      allow read: if isAuthenticated();
      allow create: if hasAnyRole(['super_admin', 'branch_admin']);
      allow update, delete: if hasRole('super_admin') || 
        (hasRole('branch_admin') && resource.data.managerId == request.auth.uid);
    }
    
    // MEMBERSHIP PLANS
    match /membership_plans/{plan} {
      allow read: if isAuthenticated();
      allow write: if hasAnyRole(['super_admin', 'branch_admin']);
    }
    
    // CLIENTS
    match /clients/{client} {
      allow read: if isAuthenticated();
      allow create: if hasAnyRole(['super_admin', 'branch_admin']);
      allow update: if hasAnyRole(['super_admin', 'branch_admin']) && 
        belongsToBusiness(resource.data.businessId);
      allow delete: if hasRole('super_admin');
    }
    
    // USERS
    match /users/{userId} {
      allow read: if isAuthenticated();
      allow write: if hasRole('super_admin') || request.auth.uid == userId;
    }
    
    // PAYMENTS
    match /payments/{payment} {
      allow read: if isAuthenticated();
      allow write: if hasAnyRole(['super_admin', 'branch_admin', 'cashier']) &&
        belongsToBusiness(resource.data.businessId);
    }
    
    // REPORTS (funciones que requieren Cloud Function)
    match /reports/{report} {
      allow read: if false;  // Solo accesible via Cloud Functions
    }
  }
}
Aplicar reglas:

bash
firebase deploy --only firestore:rules
Variables de entorno en producción
Backend (.env en producción):

env
FLASK_ENV=production
<<<<<<< HEAD
FIREBASE_CREDENTIALS_JSON='{"type": "service_account", ...}'
=======
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"tu-proyecto","private_key":"-----BEGIN PRIVATE KEY-----\n...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"..."}
>>>>>>> a920d38ca4ace10988e7cc2a1fa164966c9eb881
CORS_ORIGINS=https://tu-app.firebaseapp.com,https://tudominio.com
RATE_LIMIT_PER_MINUTE=100
LOG_LEVEL=WARNING
Frontend (.env.production):

env
VITE_API_URL=https://gymmanager-api.onrender.com/api
VITE_ENVIRONMENT=production
VITE_ENABLE_OFFLINE=true
🔄 CI/CD con GitHub Actions
Workflow completo (backend + frontend)
Crear .github/workflows/deploy.yml:

yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Run tests
        run: |
          cd backend
          pip install -r requirements.txt
          python -m pytest tests/ -v

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Render
        env:
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
        run: |
          curl -X POST "https://api.render.com/deploy/srv-${{ secrets.RENDER_SERVICE_ID }}?key=$RENDER_API_KEY"

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          
      - name: Build frontend
        run: |
          cd frontend
          npm ci
          npm run build
          
      - name: Deploy to Firebase Hosting
        uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: '${{ secrets.GITHUB_TOKEN }}'
          firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT }}'
          projectId: gymmanager-v1
          entryPoint: ./frontend
Configurar secrets en GitHub:

RENDER_API_KEY - De Render Dashboard

RENDER_SERVICE_ID - ID del servicio en Render

FIREBASE_SERVICE_ACCOUNT - JSON de la cuenta de servicio

📊 Monitoreo y Logs
Backend (Render.com)
python
# Configurar logging en app.py
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
Ver logs:

Render Dashboard → Logs

O vía CLI: render logs

Firebase Monitoring
bash
# Ver logs de Firestore
firebase functions:log

# Monitoreo de rendimiento
firebase apps:list
Frontend (Sentry para errores)
bash
npm install @sentry/react
javascript
// main.tsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "https://tu-dsn@sentry.io/project-id",
  environment: "production",
  tracesSampleRate: 0.1,  // Solo 10% de transacciones
});
✅ Checklist de lanzamiento
Antes del lanzamiento (1 semana)
Seguridad

Reglas de Firestore actualizadas (no modo prueba)

Variables de entorno en producción

HTTPS habilitado (automático en Render + Firebase)

Rate limiting configurado (100/min)

[ Rendimiento

Prueba de carga con Artillery o k6

Firestore índices optimizados

Imágenes optimizadas (WebP)

Pruebas

Todos los endpoints probados en staging

Offline-first funcionando

Sincronización de pagos offline

Día del lanzamiento
Backup de base de datos

bash
# Exportar Firestore
gcloud firestore export gs://tu-bucket/backup-$(date +%Y%m%d)
Desplegar backend

bash
# Render: Activar "Auto-deploy" en el dashboard
# O manual: git push origin main
Desplegar frontend

bash
firebase deploy --only hosting
Verificar

Health check: curl https://api.gymmanager.com/health

PWA instalable: Lighthouse audit

Login funciona

Registro de pagos funciona

Post-lanzamiento (primeras 24h)
Monitorear logs por errores 500

Verificar uso de Firestore (no exceder free tier)

Revisar métricas de Render (CPU, memoria)

Enviar feedback a usuarios beta

🐛 Solución de problemas comunes
Error: CORS policy blocked
Solución: Verificar variable CORS_ORIGINS en backend:

python
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
Error: Firebase: Error (auth/network-request-failed)
Solución: PWA offline no tiene conexión. Implementar retry logic:

javascript
const syncOfflinePayments = async () => {
  if (navigator.onLine) {
    await syncPayments();
  } else {
    setTimeout(() => syncOfflinePayments(), 30000); // Reintentar en 30s
  }
};
Error: Too many requests (429) en Firestore
Solución: Implementar exponential backoff:

python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def write_to_firestore(data):
    db.collection('payments').add(data)
Error: Service worker registration failed
Solución: Verificar manifest.json y HTTPS:

javascript
// serviceWorker.js
if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('SW registered:', reg))
      .catch(err => console.log('SW error:', err));
  });
}
Error: Firestore index not found
Solución: Firebase genera URL para crear índice automáticamente:

bash
# Crear índices faltantes
firebase firestore:indexes
📚 Referencias útiles
Render Flask Deployment Guide

Firebase Hosting Documentation

PWA Deployment Checklist

Firestore Production Checklist

🚀 Próximos pasos después del deployment
Configurar monitoreo (Sentry + Firebase Analytics)

Implementar backups automáticos (Cloud Scheduler + Firestore export)

Agregar dominio personalizado (opcional)

Configurar notificaciones push (FCM para recordatorios)

Lanzar programa beta con 5 gimnasios reales