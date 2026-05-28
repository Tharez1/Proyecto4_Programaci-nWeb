# Equipo 
 Lavenant Baldenebro Gilberto 
 Landon Donovan Enciso 
 Tristán Montes de Oca
 
 
# Procesador de Imágenes Distribuido

Aplicación web para procesar imágenes de forma distribuida usando workers en Docker, AWS SQS como cola de mensajes y Redis para el estado de las tareas.

## Arquitectura

```
Usuario
  │
  ▼
Frontend (HTML/CSS/JS)
  │  sube imagen
  ▼
FastAPI (Backend)
  │  guarda en S3 (img/)
  │  registra estado en Redis → "pendiente"
  │  SSE stream al frontend
  ▼
AWS S3 (tristan-web)
  │  evento ObjectCreated
  ▼
AWS SQS (MyQueue)
  │  mensaje en cola
  ▼
Workers x3 (Docker)
  │  descarga imagen de S3
  │  procesa (resize / filtro / conversión)
  │  sube resultado a S3
  │  actualiza Redis → "completed"
  ▼
Redis
  └── estado de cada tarea (pendiente / processing / completed / error)
```

## Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | FastAPI + Uvicorn |
| Cola de mensajes | AWS SQS |
| Almacenamiento | AWS S3 |
| Estado de tareas | Redis |
| Contenedores | Docker + Docker Compose |

## Estructura del proyecto

```
worker-redis-image/
├── docker-compose.yml
├── fast/                  # Backend FastAPI
│   ├── Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   ├── static/
│   │   └── app.js
│   └── templates/
│       └── index.html
└── worker-sqs/            # Worker de procesamiento
    ├── Dockerfile
    ├── requirements.txt
    ├── s3image.py
    └── worker.py
```

## Procesamiento disponible

| `process_type` | Descripción | Carpeta destino en S3 |
|---|---|---|
| `small` | Redimensiona al 50% | `small/` |
| `mini` | Redimensiona al 20% | `mini/` |
| `both` | Genera small y mini | `small/` y `mini/` |
| `filter:grayscale` | Escala de grises | `filtered/` |
| `filter:sepia` | Tono sepia | `filtered/` |
| `filter:blur` | Desenfoque gaussiano | `filtered/` |
| `filter:sharpen` | Nitidez | `filtered/` |
| `filter:contour` | Contorno | `filtered/` |
| `filter:emboss` | Relieve | `filtered/` |
| `filter:flip_h` | Espejo horizontal | `filtered/` |
| `filter:flip_v` | Espejo vertical | `filtered/` |
| `convert:PNG` | Convierte a PNG | `converted/` |
| `convert:WEBP` | Convierte a WEBP | `converted/` |
| `convert:JPEG` | Convierte a JPEG | `converted/` |
| `convert:GIF` | Convierte a GIF | `converted/` |
| `convert:BMP` | Convierte a BMP | `converted/` |

## Requisitos

- Docker y Docker Compose
- AWS EC2 con IAM Role que tenga permisos de S3 y SQS
- Bucket S3 con notificaciones configuradas a SQS para el prefijo `img/`

## Configuración AWS

### S3 — Event Notification
- **Bucket:** `tristan-web`
- **Prefix:** `img/`
- **Event type:** `s3:ObjectCreated:*`
- **Destination:** SQS → `MyQueue`

### SQS — Access Policy
```json
{
  "Effect": "Allow",
  "Principal": { "Service": "s3.amazonaws.com" },
  "Action": "sqs:SendMessage",
  "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:MyQueue",
  "Condition": {
    "ArnLike": {
      "aws:SourceArn": "arn:aws:s3:::tristan-web"
    }
  }
}
```

## Instalación y uso

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/worker-redis-image.git
cd worker-redis-image
```

### 2. Levantar los contenedores
```bash
docker compose up --build -d
```

### 3. Verificar que todo esté corriendo
```bash
docker compose ps
```

Debes ver:
```
NAME                          STATUS
redis                         Up (healthy)
worker-redis-image-fast-1     Up
worker-redis-image-worker-1   Up
worker-redis-image-worker-2   Up
worker-redis-image-worker-3   Up
```

### 4. Abrir la app
```
http://<IP-de-tu-EC2>:8000
```

### 5. Ver logs de los workers en tiempo real
```bash
docker compose logs -f worker
```

## Flujo de una tarea

1. El usuario sube una imagen desde el frontend
2. FastAPI la guarda en `s3://tristan-web/img/` con el `process_type` como metadata
3. Redis registra el estado como `pendiente`
4. S3 envía un evento a SQS
5. Uno de los 3 workers toma el mensaje de SQS
6. El worker descarga la imagen, la procesa y sube el resultado a S3
7. Redis actualiza el estado a `completed`
8. El frontend recibe la actualización en tiempo real via SSE

## Estado de tareas (SSE)

El frontend se conecta al endpoint `/status/stream/{filename}` usando Server-Sent Events y muestra el estado en tiempo real:

| Estado | Descripción |
|---|---|
| `pendiente` | Imagen subida, esperando worker |
| `processing` | Worker procesando la imagen |
| `completed` | Procesamiento completado |
| `error` | Error durante el procesamiento |

