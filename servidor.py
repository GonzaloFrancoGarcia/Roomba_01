import socket
import logging
 
# Configuración del logging para registrar la actividad
logging.basicConfig(filename='servidor.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
 
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
    # Configurar el socket del servidor
    host = '127.0.0.1'
    puerto = 8809
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, puerto))
    server_socket.listen(5)
    print(f"Servidor escuchando en {host}:{puerto}...")
 
    while True:
        conexion, direccion = server_socket.accept()
        print(f"Conexión establecida con {direccion}")
        try:
            datos = conexion.recv(1024)
            if not datos:
                continue
 
            # Intentar convertir los datos recibidos a entero
            try:
                numero = int(datos.decode().strip())
            except ValueError:
                respuesta = "Error: Entrada no es un número entero."
                conexion.send(respuesta.encode())
                logging.error(f"Datos inválidos recibidos: {datos.decode().strip()}")
                conexion.close()
                continue
 
            # Verificar si el número es primo
            if isprime(numero):
                respuesta = f"El número {numero} es primo."
            else:
                respuesta = f"El número {numero} no es primo."
 
            # Enviar la respuesta al cliente
            conexion.send(respuesta.encode())
            logging.info(f"Recibido: {numero} - Respuesta: {respuesta}")
        except Exception as e:
            logging.error(f"Error en la conexión: {e}")
        finally:
            conexion.close()
 
if __name__ == '__main__':
    iniciar_servidor()