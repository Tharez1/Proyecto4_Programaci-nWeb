import sys
import redis
import redis.exceptions
import os
import time
import signal


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
    except Exception as e:
        print(f"Waiting for redis: {e}", flush=True)
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
        result = r.brpop('message_queue', timeout=2)
    except redis.exceptions.RedisError as e:
        print(f"Error de Redis: {e}", flush=True)
        time.sleep(3)
        continue

    if result is None:
        continue

    queue, message = result
    print(f'Imagen "{message}" procesada exitosamente', flush=True)

print("Worker detenido.", flush=True)
