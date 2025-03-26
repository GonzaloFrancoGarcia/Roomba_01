import socket
import logging

# Configuración del registro de actividad
logging.basicConfig(
    filename='servidor.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def isprime(n):
    """Determina si n es un número primo."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

def iniciar_servidor():
    host = '127.0.0.1'
    puerto = 8809
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, puerto))
    server_socket.listen(5)
    print(f"Servidor escuchando en {host}:{puerto}...")
    logging.info(f"Servidor iniciado en {host}:{puerto}")

    while True:
        conexion, direccion = server_socket.accept()
        print(f"Conexión establecida con {direccion}")
        try:
            datos = conexion.recv(1024)
            if not datos:
                conexion.close()
                continue
            entrada = datos.decode().strip()
            try:
                numero = int(entrada)
            except ValueError:
                respuesta = f"Error: La entrada '{entrada}' no es un número entero."
                conexion.send(respuesta.encode())
                logging.error(respuesta)
                conexion.close()
                continue

            if isprime(numero):
                respuesta = f"El número {numero} es primo."
            else:
                respuesta = f"El número {numero} no es primo."

            conexion.send(respuesta.encode())
            logging.info(f"Recibido: {numero} - Respuesta: {respuesta}")
        except Exception as e:
            logging.error(f"Error en la conexión: {e}")
        finally:
            conexion.close()

if __name__ == '__main__':
    iniciar_servidor()
