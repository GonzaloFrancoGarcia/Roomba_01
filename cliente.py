import socket

def iniciar_cliente():
    host = '127.0.0.1'
    puerto = 8809
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, puerto))
        numero = input("Introduce un número entero: ").strip()
        client_socket.send(numero.encode())
        respuesta = client_socket.recv(1024).decode()
        print("Respuesta del servidor:", respuesta)
    except Exception as e:
        print(f"Error en la conexión: {e}")
    finally:
        client_socket.close()

if __name__ == '__main__':
    iniciar_cliente()
