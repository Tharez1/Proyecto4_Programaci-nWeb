import os
import sys
import redis
import json

def main():
    if len(sys.argv) < 2:
        print("Uso: python enqueue_images.py <ruta>")
        sys.exit(1)

    path = sys.argv[1]

    if not os.path.isdir(path):
        print(f"Error: '{path}' no es un directorio válido")
        sys.exit(1)

    redis_host = os.environ.get('REDIS_HOST')
    if not redis_host:
        print("Error: La variable de entorno REDIS_HOST no está definida")
        sys.exit(1)

    r = redis.Redis(host=redis_host, decode_responses=True)

    extensions = {'.jpeg', '.jpg', '.png'}
    count = 0

    for filename in os.listdir(path):
        ext = os.path.splitext(filename)[1].lower()

        if ext in extensions:
            data = {
                'filename': filename
            }
            data_string = json.dumps(data)
            r.lpush('message_queue', data_string)
            print(f"Enviado: {data}")
            count += 1

    print(f"Total de imágenes enviadas: {count}")


if __name__ == '__main__':
    main()
