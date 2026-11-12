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

### Usarlo en Mac

Funciona igual en Mac con Apple Silicon o Intel: las imágenes de Docker son multiplataforma.

1. Instala [Docker Desktop para Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
   y ábrelo.
2. Clona el proyecto:
   ```bash
   git clone https://github.com/estebanMns/Bandit.git
   cd Bandit
   ```
3. Copia tu `.env` al Mac por un medio privado (AirDrop, USB o un gestor de contraseñas), nunca
   por git ni por chat. **Debe tener la misma `CAMERA_ENCRYPTION_KEY`**: sin ella Bandit no puede
   leer las cámaras ya guardadas en Supabase. Para probar, deja `DEMO_ADMIN=true`.
4. Arranca y abre <http://localhost:8080>. Con el modo de prueba entras con `admin` / `admin`.
   ```bash
   docker compose up -d --build
   ```
5. Comprueba si el Mac alcanza la cámara directamente:
   ```bash
   nc -vz 192.168.1.102 554
   ```
   Si dice `succeeded`, registra en **Cámaras** la URL `rtsp://` directa de la cámara, sin puente
   ni nube. Si no, usa el puente (`bash relay/iniciar-puente.sh`, que también corre en macOS) o la
   nube de Imou.

### Cuentas y roles

| Rol | Cómo se crea | Alcance |
|---|---|---|
| Dueño | Registro en `/registrarse` | Administra solo su local |
| Operador | Un administrador, por `POST /api/auth/users` | Vigila y decide en su local |
| Administrador | `BOOTSTRAP_ADMIN_EMAIL` y `BOOTSTRAP_ADMIN_PASSWORD` en `.env`, opcional | Ve todos los locales y sincroniza el directorio |
| Administrador de prueba | `DEMO_ADMIN=true` en `.env`: usuario `admin`, clave `admin` | Igual que un administrador. Con `false` la cuenta se borra al arrancar |

La extracción del directorio corre sola al arrancar y cada día. Un dueño o un administrador puede
pedir una manual desde **Actividad IA**, como máximo cada 30 minutos. El registro no verifica el correo y está limitado a 5 cuentas por hora por conexión.

### Funciones que requieren credenciales

| Función | Variables | Sin ellas |
|---|---|---|
| Detección y extracción con Gemini | `GEMINI_API_KEY` | El video funciona, pero no hay detección ni extracción |
| Alertas por WhatsApp | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | El aviso falla de forma visible y se puede reintentar |
| Web Push | `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | No aparece la opción de notificaciones |
| Cámaras Imou por su nube | `IMOU_APP_ID`, `IMOU_APP_SECRET`, `IMOU_API_URL` | Solo se pueden usar cámaras `rtsp://` |

### Plantilla de WhatsApp

Crea en Meta una plantilla de utilidad llamada `bandit_incidente`, en español y con este cuerpo:

```text
Alerta de {{1}}, ubicado en {{2}}.
Situación: {{3}}. Hora: {{4}}.
Detalle: {{5}}.
Mensaje confirmado por el personal del local.
```

Acuerda con el CAI el uso de su número antes de registrarlo.

### Cámara Imou sin acceso por la red local

Si el servidor de Bandit no alcanza la cámara por la red, Bandit puede pedir el video a la nube de
Imou. Crea una aplicación en [open.imoulife.com](https://open.imoulife.com) con la misma cuenta de
Imou Life y copia su **App ID** y **App Secret** en `IMOU_APP_ID` e `IMOU_APP_SECRET`. En
`IMOU_API_URL` usa el centro de datos de tu cuenta: `openapi-or` para América, `openapi-fk` para
Europa u `openapi-sg` para Asia.

En **Cámaras** registra `imou://<número de serie>/<canal>?stream=1`. El número de serie está en la
etiqueta y en Imou Life. Para una cámara de dos lentes, registra una cámara por canal (`0` y `1`).
`stream=1` es la calidad ligera, suficiente para Gemini; `stream=0` es la alta. El video llega por
internet con unos segundos de retraso y consume la cuota de tu aplicación en Imou.

### Cámara que solo responde a otro equipo

Algunas cámaras Imou o Dahua dejan de contestarle a un equipo concreto. Si la cámara responde
desde otro equipo de la misma red, como una máquina virtual en modo puente, usa ese equipo como
puente:

```bash
bash relay/iniciar-puente.sh
```

El script descarga MediaMTX, pide la IP y el código de la cámara sin mostrarlos y genera una clave
de solo lectura. Al terminar imprime dos URL, `rtsp://bandit:<clave>@<ip-del-puente>:8554/lente1` y
`/lente2`. Regístralas en **Cámaras** como dos cámaras. El puente debe quedar encendido; si se
apaga, Bandit marca la cámara como caída y reintenta.

### Primeros pasos y búsqueda de cámaras

Al registrarse, o al entrar sin local o sin cámaras, Bandit abre `/empezar`, un asistente de cuatro
pasos: el local, el WhatsApp del CAI, las cámaras y listo. En el paso de cámaras, **Buscar cámaras en
mi red** revisa tu Wi-Fi (solo redes privadas de hasta 256 direcciones). Prueba las rutas de video
conocidas de cada marca con la clave que escribes y, si ninguna funciona, le pide a Gemini otras rutas
para probar. Gemini solo recibe la marca, los puertos y las cabeceras, nunca la clave. La URL se arma
en tu navegador y se guarda cifrada.

### Directorio por prioridad

El directorio muestra primero a quien tiene la recompensa más alta publicada por la Policía, luego
según la gravedad del delito publicado (una lista fija y visible: homicidio; secuestro, extorsión o
terrorismo; delito sexual; tráfico, armas o concierto para delinquir; hurto u otros) y luego en el
orden de la página de la Policía. Bandit no califica a las personas.

Si `GEMINI_MODEL` se queda sin cuota (error `429 RESOURCE_EXHAUSTED`), define
`GEMINI_DIRECTORY_MODEL`, por ejemplo `gemini-3.5-flash`, para extraer el directorio con otro modelo.
El panel **Actividad IA** muestra el error exacto de cada extracción.

### Probar alertas con fotos

Sin cámara, puedes comprobar con Gemini real que Bandit detecta una situación y crea la alerta.
Pon fotos `.jpg` en `backend/evaluation/frames/<situación>/` (`weapon`, `robbery`, `fight`, `fire`,
`medical` o `none`); esa carpeta no se sube a GitHub. Luego, desde la carpeta `Bandit`:

```bash
docker compose cp backend/evaluation/frames backend:/app/var/pruebas
docker compose exec backend python -m bandit.tools.simulate_alert /app/var/pruebas/weapon --local "Tu local"
```

El script muestra qué vio Gemini en cada foto. Si ve la misma situación en dos fotos seguidas,
crea la alerta en la cámara "Prueba (fotos)" del local: aparece en Eventos, el Monitor y el Panel.
No envía WhatsApp a menos que un operador confirme la alerta. Bandit detecta situaciones; no
identifica personas.

### Panel de actividad de la IA

**Actividad IA** muestra, por cámara, el último fotograma que analizó Gemini, el nivel de
movimiento, su última respuesta (situación, confianza, severidad y descripción) y cuántas
detecciones seguidas lleva antes de alertar. También muestra las consultas del día frente al tope
y la galería de los más buscados con el estado de la última extracción. El fotograma analizado solo
vive en memoria. La extracción corre sola al arrancar si el directorio está vacío o es viejo, y un
dueño puede pedir una manual cada 30 minutos.

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
