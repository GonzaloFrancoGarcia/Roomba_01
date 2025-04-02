import socket
import threading
import time
import json
import pygame
from roomba import RoombaWorld  # Se importa la clase que gestiona la lógica del mundo

def manejar_cliente(conn, addr, world):
    """
    Hilo por cliente: Envía periódicamente el estado del mundo (JSON).
    En esta versión se ignoran los comandos entrantes para que la simulación (mosquito)
    no se vea afectada por el input del cliente.
    """
    print(f"Conexión establecida con {addr}")
    conn.settimeout(1.0)
    try:
        while True:
            with world.lock:
                state_to_send = {
                    "mosquito_pos": world.mosquito_pos,
                    "mosquito_vel": world.mosquito_vel,
                    "dust_particles": world.dust_particles,
                    "level": world.level,
                    "zone_rects": world.zone_rects
                }
            mensaje = json.dumps(state_to_send)
            try:
                conn.sendall(mensaje.encode())
            except Exception as e:
                print(f"Error enviando datos a {addr}: {e}")
                break

            # Se reciben y se ignoran comandos, para que la simulación siga inalterada.
            try:
                data = conn.recv(1024)
                if data:
                    print(f"Comando recibido (ignorando) de {addr}: {data.decode().strip()}")
                else:
                    break
            except socket.timeout:
                pass
            except Exception as e:
                print(f"Error recibiendo datos de {addr}: {e}")
                break

            time.sleep(0.05)
    finally:
        conn.close()
        print(f"Conexión cerrada con {addr}")

def iniciar_servidor(world, host="127.0.0.1", puerto=8809):
    """
    Configura el socket TCP y lanza un hilo para cada cliente conectado.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, puerto))
    server_socket.listen(5)
    print(f"Servidor escuchando en {host}:{puerto}...")
    
    try:
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=manejar_cliente, args=(conn, addr, world), daemon=True).start()
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario.")
    finally:
        server_socket.close()

def main():
    # Inicializar pygame y el mixer necesarios para la simulación
    pygame.init()
    pygame.mixer.init()

    # Cargar el sonido para "mosquito_bite"
    bite_sound = pygame.mixer.Sound("mosquito_bite.mp3")
    bite_sound.set_volume(1.0)
    
    # Instanciar el mundo de simulación
    world = RoombaWorld(window_size=(600,600), tasa_limpeza=1000, velocidad_base=10)
    
    # Iniciar el hilo de movimiento del mosquito
    mosquito_thread = threading.Thread(target=world.mover_mosquito, args=(bite_sound,), daemon=True)
    mosquito_thread.start()
    
    # Iniciar hilos para generar partículas ("dust") en cada zona
    dust_stop_events = {}
    dust_threads = []
    for zona in world.zonas:
        stop_event = threading.Event()
        dust_stop_events[zona] = stop_event
        t = threading.Thread(target=world.generar_dust, args=(zona, stop_event, world.level), daemon=True)
        t.start()
        dust_threads.append(t)
    
    # Iniciar el servidor TCP que envía el estado del mundo
    iniciar_servidor(world, host="127.0.0.1", puerto=8809)
    
    # Si se interrumpe, detener hilos
    world.mosquito_stop_event.set()
    for e in dust_stop_events.values():
        e.set()
    mosquito_thread.join()
    for t in dust_threads:
        t.join()

if __name__ == '__main__':
    main()
