# Bandit

Monitoreo de incidentes para restaurantes, bares y locales similares. Bandit se conecta a cámaras
RTSP, usa Gemini para detectar **situaciones** de riesgo (armas, atracos, peleas, fuego o
emergencias de salud) y, cuando un operador confirma una, envía un WhatsApp al CAI que el local
registró. También mantiene un directorio informativo con el listado público de los más buscados
de la Policía Nacional.

## Límites del sistema

- No hay reconocimiento facial, plantillas biométricas ni identificación de personas.
- El video y el directorio están aislados. `import-linter` impide en CI que se conecten.
- Ninguna alerta externa sale sin la confirmación de un operador autenticado.

## Puesta en marcha

Requisitos: Docker Desktop.

```bash
cp .env.example .env
```

Completa en `.env`, como mínimo, `DATABASE_URL`, `CAMERA_ENCRYPTION_KEY` y `REVALIDATE_SECRET`.

### Base de datos

**Con Supabase:** en **Connect** elige **Session pooler** y copia la URI. Cambia el inicio por
`postgresql+asyncpg://`. El usuario debe ser `postgres.<id-del-proyecto>`. No uses la conexión
directa, que solo funciona por IPv6, ni el Transaction pooler. Las migraciones crean las tablas
y activan RLS para bloquear la API pública de Supabase.

**Con PostgreSQL local:** define `POSTGRES_PASSWORD`, usa el mismo valor en `DATABASE_URL` y
agrega `--profile db-local` al comando de abajo.

### Arrancar

```bash
docker compose up -d --build
```

Abre <http://localhost:8080>, pulsa **Crear cuenta** y registra tu local. Luego sigue la guía
en `/guia`.

### Cuentas y roles

| Rol | Cómo se crea | Alcance |
|---|---|---|
| Dueño | Registro en `/registrarse` | Administra solo su local |
| Operador | Un administrador, por `POST /api/auth/users` | Vigila y decide en su local |
| Administrador | `BOOTSTRAP_ADMIN_EMAIL` y `BOOTSTRAP_ADMIN_PASSWORD` en `.env`, opcional | Ve todos los locales y sincroniza el directorio |

La sincronización manual del directorio requiere un administrador. La extracción programada corre
sola. El registro no verifica el correo y está limitado a 5 cuentas por hora por conexión.

### Funciones que requieren credenciales

| Función | Variables | Sin ellas |
|---|---|---|
| Detección y extracción con Gemini | `GEMINI_API_KEY` | El video funciona, pero no hay detección ni extracción |
| Alertas por WhatsApp | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | El aviso falla de forma visible y se puede reintentar |
| Web Push | `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | No aparece la opción de notificaciones |

### Plantilla de WhatsApp

Crea en Meta una plantilla de utilidad llamada `bandit_incidente`, en español y con este cuerpo:

```text
Alerta de {{1}}, ubicado en {{2}}.
Situación: {{3}}. Hora: {{4}}.
Detalle: {{5}}.
Mensaje confirmado por el personal del local.
```

Acuerda con el CAI el uso de su número antes de registrarlo.

## Arquitectura

Monolito modular: un solo backend desplegable, con módulos de fronteras verificadas.

```text
backend/src/bandit/
  shared/         fan-out, bus de eventos, reloj, configuración y base de datos
  identity/       usuarios, roles, sesiones y CSRF
  establishments/ locales y WhatsApp del CAI
  cameras/        registro cifrado, captura RTSP y fan-out de fotogramas
  analysis/       filtro de movimiento y clasificación de escenas con Gemini
  incidents/      ciclo de vida, confirmación humana, evidencia y auditoría
  directory/      agente de extracción y consulta del directorio
  notifications/  WhatsApp y Web Push
  realtime/       WebSocket de eventos
  bootstrap.py    raíz de composición
frontend/src/
  app/            rutas de Next.js
  features/       video, eventos, incidentes, directorio y demás funciones
  components/     componentes compartidos
```

Cada módulo separa `domain`, `application`, `infrastructure` y `api`. Los módulos se comunican por
eventos, y `bootstrap.py` los conecta.

### Dónde está cada requisito técnico

| Requisito | Ubicación |
|---|---|
| SOLID y POO | Puertos en `*/domain/ports.py`, casos de uso en `*/application/`, adaptadores en `*/infrastructure/` |
| Event loop | `cameras/application/supervisor.py`, `analysis/application/camera_analysis.py` |
| WebSocket | `/ws/video/{camera_id}` y `/ws/events/{establishment_id}` |
| Fan-out | `shared/fanout.py`, `shared/events.py`, `features/live/events.shared-worker.ts` |
| Web Worker | `features/video/video.worker.ts` |
| SharedArrayBuffer | `features/video/frameRing.ts` |
| SharedWorker | `features/live/events.shared-worker.ts` |
| Service Worker | `public/sw.js` |
| SSG | `/`, `/guia`, `/privacidad`, `/sin-conexion` |
| ISR | `/directorio`, `/directorio/[slug]` |
| SSR | `/incidentes`, `/incidentes/[id]` |
| CSR | `/monitor`, `/ajustes/camaras`, `/ajustes/local` |

## Desarrollo y pruebas

```bash
# Backend
cd backend
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && lint-imports && pytest

# Frontend
cd frontend
npm ci
npm run lint && npm run typecheck && npm test && npm run build
```

Las pruebas de navegador corren contra el stack levantado:

```bash
cd frontend
E2E_ADMIN_EMAIL=... E2E_ADMIN_PASSWORD=... E2E_RTSP_URL=rtsp://... npm run test:e2e
```

La prueba del incidente necesita uno pendiente en la base de datos.

### Elegir la configuración de Gemini

Guarda fotogramas de tu cámara en `backend/evaluation/frames/<situación>/*.jpg`, con carpetas como
`none`, `fight` y `robbery`. Luego ejecuta:

```bash
cd backend
GEMINI_API_KEY=... python scripts/evaluate_model.py evaluation/frames
```

El informe compara aciertos, falsos positivos, latencia y costo mínimo por modelo y resolución.

## Antes de usarlo en un local real

- Avisa a los clientes que hay videovigilancia y adapta `/privacidad` con asesoría legal
  (Ley 1581 de 2012).
- Mide la calidad del modelo con tus cámaras. Un falso positivo puede enviar a la policía a una
  situación inexistente, por eso la confirmación humana es obligatoria.
- Usa HTTPS y `COOKIE_SECURE=true`. Service Worker y Web Push lo exigen fuera de `localhost`.
- WhatsApp no sustituye a la línea 123.
- Si lo publicas en internet, agrega verificación de correo o invitaciones. El registro abierto
  permite que cualquiera cree cuentas y apunte a direcciones RTSP desde tu servidor, y el tope
  diario de Gemini lo comparten todos los locales.
