# servidor.py
import socket
import threading
import time
import json
import pygame
from roomba import RoombaWorld  # Importamos la clase que encapsula la lógica del "mundo"

def manejar_cliente(conn, addr, world):
    """
    Función que se ejecuta en un hilo para cada cliente conectado.
    Envía periódicamente el estado (mensaje JSON) del mundo y, además, escucha comandos entrantes.
    """
    print(f"Conexión establecida con {addr}")
    conn.settimeout(1.0)
    try:
        while True:
            # Adquirir el estado actual del mundo de forma segura
            with world.lock:
                state_to_send = {
                    "mosquito_pos": world.mosquito_pos,
                    "mosquito_vel": world.mosquito_vel,
                    "dust_particles": world.dust_particles,
                    "level": world.level
                }
            mensaje = json.dumps(state_to_send)
            try:
                conn.sendall(mensaje.encode())
            except Exception as e:
                print(f"Error enviando datos a {addr}: {e}")
                break

            # Intentar leer comandos del cliente
            try:
                data = conn.recv(1024)
                if data:
                    comando = data.decode().strip()
                    print(f"Comando recibido de {addr}: {comando}")
                    with world.lock:
                        # Ejemplo: aplicar cambios sobre el estado en función del comando recibido.
                        # Aquí se pueden definir distintos comandos de control.
                        if comando == "MOVE LEFT":
                            world.mosquito_vel[0] = -abs(world.mosquito_vel[0])
                        elif comando == "MOVE RIGHT":
                            world.mosquito_vel[0] = abs(world.mosquito_vel[0])
                        elif comando == "MOVE UP":
                            world.mosquito_vel[1] = -abs(world.mosquito_vel[1])
                        elif comando == "MOVE DOWN":
                            world.mosquito_vel[1] = abs(world.mosquito_vel[1])
                else:
                    # Si no se reciben datos, se asume que el cliente cerró la conexión
                    break
            except socket.timeout:
                # No hay nuevo comando, continuar
                pass
            except Exception as e:
                print(f"Error recibiendo datos de {addr}: {e}")
                break

            time.sleep(0.05)
    finally:
        conn.close()
        print(f"Cerrada conexión con {addr}")

def iniciar_servidor(world, host="127.0.0.1", puerto=8809):
    """
    Función principal del servidor TCP. Se encarga de crear el socket, escuchar conexiones
    y lanzar un hilo de atención para cada cliente.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, puerto))
    server_socket.listen(5)
    print(f"Servidor escuchando en {host}:{puerto}...")

    try:
        while True:
            conn, addr = server_socket.accept()
            hilo_cliente = threading.Thread(target=manejar_cliente, args=(conn, addr, world), daemon=True)
            hilo_cliente.start()
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario.")
    finally:
        server_socket.close()

def main():
    # Inicializar pygame (necesario para cargar sonidos en la lógica, si es que se usan)
    pygame.init()
    pygame.mixer.init()
    # Cargamos el sonido utilizado por la simulación (por ejemplo, para reproducir cuando el mosquito “pica”)
    bite_sound = pygame.mixer.Sound("mosquito_bite.mp3")
    bite_sound.set_volume(1.0)

    # Crear una instancia del mundo de simulación (la lógica ya encapsulada en RoombaWorld)
    world = RoombaWorld(window_size=(600,600), tasa_limpeza=1000, velocidad_base=10)
    
    # Iniciar el hilo de simulación del mosquito (la lógica interna de movimiento y picadura)
    mosquito_thread = threading.Thread(target=world.mover_mosquito, args=(bite_sound,), daemon=True)
    mosquito_thread.start()
    
    # Iniciar los hilos de generación de partículas ("dust") en cada zona
    dust_stop_events = {}
    dust_threads = []
    for zona in world.zonas:
        stop_event = threading.Event()
        dust_stop_events[zona] = stop_event
        # El método generar_dust requiere: (zona, stop_event, nivel)
        t = threading.Thread(target=world.generar_dust, args=(zona, stop_event, world.level), daemon=True)
        t.start()
        dust_threads.append(t)
    
    # Iniciar el servidor TCP que enviará el estado y recibirá comandos de control
    iniciar_servidor(world, host="127.0.0.1", puerto=8809)
    
    # En caso de salida, se detienen los hilos de simulación y se unen
    world.mosquito_stop_event.set()
    for e in dust_stop_events.values():
        e.set()
    mosquito_thread.join()
    for t in dust_threads:
        t.join()

if __name__ == '__main__':
    main()
