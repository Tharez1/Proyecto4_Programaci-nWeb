import sys
import os
import time
import signal
import json
import redis
import boto3
from botocore.exceptions import ClientError
import s3image

# CLIENTE S3
s3 = boto3.client('s3')

# URL SQS
SQS_URL = os.environ.get('SQS_URL')
SQS_URL = 'https://sqs.us-east-1.amazonaws.com/467468288419/MyQueue'

# REDIS
REDIS_HOST = os.environ.get('REDIS_HOST')

if not REDIS_HOST:
    print(
        "Error: La variable de entorno REDIS_HOST no está definida",
        flush=True
    )
    sys.exit(1)

r = redis.Redis(
    host=REDIS_HOST,
    decode_responses=True
)

# ESPERAR REDIS
redis_ready = False

while not redis_ready:

    try:

        if r.ping():
            print("Redis is connected", flush=True)
            redis_ready = True

    except (
        redis.exceptions.ConnectionError,
        redis.exceptions.TimeoutError
    ) as e:

        print(f"Redis connection error: {e}", flush=True)
        print("Waiting for redis", flush=True)

        time.sleep(3)

    except Exception as e:

        print(f"Waiting for redis: {e}", flush=True)

        time.sleep(3)

print("Redis is active", flush=True)

# VALIDAR SQS
if not SQS_URL:

    print(
        "Error: La variable de entorno SQS_URL no está definida",
        flush=True
    )

    sys.exit(1)

# CLIENTE SQS
client = boto3.client(
    'sqs',
    region_name='us-east-1'
)

run = True

stop_after_next = (
    len(sys.argv) > 1 and sys.argv[1] == 'stop'
)


# MANEJO DE SEÑALES
def handle_signal(signum, frame):

    global run

    print(
        f"\nSeñal {signum} recibida, deteniendo worker...",
        flush=True
    )

    run = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


# LOOP PRINCIPAL
while run:

    if stop_after_next:
        run = False

    try:

        message = client.receive_message(
            QueueUrl=SQS_URL,
            WaitTimeSeconds=2
        )

    except ClientError as e:

        if e.response['Error']['Code'] == 'QueueDoesNotExist':

            print("The queue does not exist.")

        else:

            raise e

        time.sleep(3)

        continue

    # SI HAY MENSAJES
    if (
        message and
        'Messages' in message and
        message['Messages']
    ):

        try:

            receipt_handle = (
                message['Messages'][0]['ReceiptHandle']
            )

            body = json.loads(
                message['Messages'][0]['Body']
            )

            print(json.dumps(body, indent=2))

            # IGNORAR EVENTOS DE PRUEBA
            if 'Records' not in body:

                print("Evento ignorado")

                client.delete_message(
                    QueueUrl=SQS_URL,
                    ReceiptHandle=receipt_handle
                )

                continue

            # DATOS S3
            bucket_name = (
                body['Records'][0]['s3']['bucket']['name']
            )

            key = (
                body['Records'][0]['s3']['object']['key']
            )

            # IGNORAR CARPETAS
            if key.endswith('/'):

                print("Carpeta ignorada")

                client.delete_message(
                    QueueUrl=SQS_URL,
                    ReceiptHandle=receipt_handle
                )

                continue

            # SOLO PROCESAR img/
            if not key.startswith("img/"):

                print("Archivo ignorado:", key)

                client.delete_message(
                    QueueUrl=SQS_URL,
                    ReceiptHandle=receipt_handle
                )

                continue

            filename = key.split('/')[-1]

            # LEER METADATA
            response = s3.head_object(
                Bucket=bucket_name,
                Key=key
            )

            process_type = (
                response['Metadata']
                .get('process_type', 'small')
            )

            print("TIPO:", process_type)

            message_id = (
                message['Messages'][0]['MessageId']
            )

            print(
                message_id,
                bucket_name,
                key,
                receipt_handle
            )

            # ESTADO REDIS
            r.set(filename, "processing")

            # DESCARGAR IMAGEN
            s3image.download_file(
                bucket_name,
                key,
                'image.jpg'
            )

            print('imagen recibida')

            # SMALL
            if process_type == "small":

                s3image.resize_image(
                    'image.jpg',
                    'small.jpg'
                )

                s3image.upload_file(
                    'small.jpg',
                    bucket_name,
                    f'small/{filename}',
                    extra_args={
                        'ACL': 'public-read'
                    }
                )

                print('Imagen redimensionada')

            # MINI
            elif process_type == "mini":

                s3image.resize_image(
                    'image.jpg',
                    'mini.jpg'
                )

                s3image.upload_file(
                    'mini.jpg',
                    bucket_name,
                    f'mini/{filename}',
                    extra_args={
                        'ACL': 'public-read'
                    }
                )

                print('Miniatura generada')

            # BOTH
            elif process_type == "both":

                # SMALL
                s3image.resize_image(
                    'image.jpg',
                    'small.jpg'
                )

                s3image.upload_file(
                    'small.jpg',
                    bucket_name,
                    f'small/{filename}',
                )

                # MINI
                s3image.resize_image(
                    'image.jpg',
                    'mini.jpg'
                )

                s3image.upload_file(
                    'mini.jpg',
                    bucket_name,
                    f'mini/{filename}',
             )

                print('small y mini generadas')

            print('imagen almacenada')

            # BORRAR MENSAJE SQS
            client.delete_message(
                QueueUrl=SQS_URL,
                ReceiptHandle=receipt_handle
            )

            print('mensaje eliminado')

            # ESTADO FINAL
            ok = r.set(filename, "completed")

            assert ok

        except Exception as e:

            print("ERROR:", e)

            if 'filename' in locals():
                r.set(filename, "error")

            try:

                client.delete_message(
                    QueueUrl=SQS_URL,
                    ReceiptHandle=receipt_handle
                )

            except:
                pass

print("Worker detenido.", flush=True)