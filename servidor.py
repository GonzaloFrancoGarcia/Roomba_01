import socket
import threading
import time
import json
import pygame
from roomba import RoombaWorld   # Asegúrate de que roomba.py exporte la clase RoombaWorld

def manejar_cliente(conn, addr, world):
    """
    Se ejecuta en cada hilo para atender a un cliente: 
      - Envía periódicamente el estado actual del mundo (en JSON).
      - Recibe comandos de control (por ejemplo, para ajustar el movimiento).
    """
    print(f"Conexión establecida con {addr}")
    conn.settimeout(1.0)
    try:
        while True:
            # Con lock, obtener una copia del estado actual del mundo.
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

            # Se intenta recibir comandos que modifiquen, por ejemplo, la dirección.
            try:
                data = conn.recv(1024)
                if data:
                    comando = data.decode().strip()
                    print(f"Comando recibido de {addr}: {comando}")
                    with world.lock:
                        if comando == "MOVE LEFT":
                            world.mosquito_vel[0] = -abs(world.mosquito_vel[0])
                        elif comando == "MOVE RIGHT":
                            world.mosquito_vel[0] = abs(world.mosquito_vel[0])
                        elif comando == "MOVE UP":
                            world.mosquito_vel[1] = -abs(world.mosquito_vel[1])
                        elif comando == "MOVE DOWN":
                            world.mosquito_vel[1] = abs(world.mosquito_vel[1])
                else:
                    # Si data está vacío, se asume que el cliente cerró la conexión.
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
    Crea un socket TCP y lanza un hilo por cada cliente que se conecte.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, puerto))
    server_socket.listen(5)
    print(f"Servidor escuchando en {host}:{puerto}...")
    
    try:
        while True:
            conn, addr = server_socket.accept()
            hilo = threading.Thread(target=manejar_cliente, args=(conn, addr, world), daemon=True)
            hilo.start()
    except KeyboardInterrupt:
        print("Servidor detenido por el usuario.")
    finally:
        server_socket.close()

def main():
    # Inicializar pygame y el mixer, ya que la lógica de RoombaWorld utiliza sonidos.
    pygame.init()
    pygame.mixer.init()
    
    # Cargar el sonido que se usará en la simulación.
    bite_sound = pygame.mixer.Sound("mosquito_bite.mp3")
    bite_sound.set_volume(1.0)
    
    # Crear la instancia del mundo de simulación (RoombaWorld)
    world = RoombaWorld(window_size=(600,600), tasa_limpeza=1000, velocidad_base=10)
    
    # Iniciar el hilo que actualiza el movimiento del mosquito.
    mosquito_thread = threading.Thread(target=world.mover_mosquito, args=(bite_sound,), daemon=True)
    mosquito_thread.start()
    
    # Iniciar hilos para generar "dust"/partículas en cada zona.
    dust_stop_events = {}
    dust_threads = []
    for zona in world.zonas:
        stop_event = threading.Event()
        dust_stop_events[zona] = stop_event
        t = threading.Thread(target=world.generar_dust, args=(zona, stop_event, world.level), daemon=True)
        t.start()
        dust_threads.append(t)
    
    # Iniciar el servidor TCP para enviar el estado del mundo y recibir comandos.
    iniciar_servidor(world, host="127.0.0.1", puerto=8809)
    
    # Al final, al interrumpir la aplicación, detener todos los hilos.
    world.mosquito_stop_event.set()
    for e in dust_stop_events.values():
        e.set()
    mosquito_thread.join()
    for t in dust_threads:
        t.join()

if __name__ == '__main__':
    main()
