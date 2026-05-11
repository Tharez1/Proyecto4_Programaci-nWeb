import json
import s3image
import sys
import redis
import redis.exceptions
import os
import time
import signal
import uuid

WORKER_ID = str (uuid.uuid4())

REDIS_HOST = os.environ.get('REDIS_HOST')
if not REDIS_HOST:
    print("Error: La variable de entorno REDIS_HOST no está definida", flush=True)
    sys.exit(1)

r = redis.Redis(host=REDIS_HOST, decode_responses=True)

redis_ready = False
while not redis_ready:
    try:
        if r.ping():
            print("Redis is connected", flush=True)
            redis_ready = True
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
        print(f"Redis connection error: {e}", flush=True)
        print("Waiting for redis", flush=True)
        time.sleep(3)

print("Redis is active", flush=True)

run = True
stop_after_next = len(sys.argv) > 1 and sys.argv[1] == 'stop'


def handle_signal(signum, frame):
    global run
    print(f"\nSeñal {signum} recibida, deteniendo worker...", flush=True)
    run = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

while run:
    if stop_after_next:
        run = False

    try:
        # timeout=2 permite salir del bloqueo periódicamente para revisar `run`
        result = r.brpop('message_queue', timeout=2)
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
        print(f"Redis connection error: {e}", flush=True)
        print("Waiting for redis", flush=True)
        time.sleep(3)

    if result is None:
        continue

    queue, message = result
    print(f'Worker:{WORKER_ID} Procesando: {message}', flush=True)

#   try:
#       body = json.loads(message)
#       bucket_name = body['Records'][0]['s3']['bucket']['name']
#       key = body['Records'][0]['s3']['object']['key']
#       filename = key.split('/')[-1]

#       s3image.download_file(bucket_name, key, 'image.jpg')
#       print('imagen recibida', flush=True)

#       s3image.resize_image('image.jpg', 'new.jpg')
#       print('imagen transformada', flush=True)

#       s3image.upload_file('new.jpg', bucket_name,
#                           f'small/{filename}', extra_args={'ACL': 'public-read'})
#       print('imagen almacenada', flush=True)

#   except Exception as e:
#       print(f"Error procesando mensaje: {e}", flush=True)
        # No hacer re-queue automático para evitar loops infinitos

print("Worker detenido.", flush=True)
