# cliente.py
import socket
import threading
import time
import json
import pygame

# Variables globales para el estado recibido y la sincronización
server_state = None
state_lock = threading.Lock()
stop_receptor = False

def recibir_estado(client_socket):
    """
    Función que se ejecuta en un hilo y recibe continuamente el estado del mundo
    (en formato JSON) enviado por el servidor.
    """
    client_socket.settimeout(1.0)
    global server_state, stop_receptor
    while not stop_receptor:
        try:
            data = client_socket.recv(4096)
            if data:
                with state_lock:
                    server_state = json.loads(data.decode())
            else:
                # Si data es vacío, se considera que la conexión se ha cerrado.
                break
        except socket.timeout:
            continue
        except Exception as e:
            print("Error recibiendo datos:", e)
            break

def main():
    host = "127.0.0.1"
    puerto = 8809
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, puerto))
    except Exception as e:
        print("No se pudo conectar al servidor:", e)
        return

    # Lanzar el hilo receptor para obtener el estado enviado por el servidor.
    receptor = threading.Thread(target=recibir_estado, args=(client_socket,), daemon=True)
    receptor.start()

    # Inicialización de Pygame
    pygame.init()
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 600
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Cliente Roomba - Visualización del Mundo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 16)

    # Cargar assets (imágenes/sprites)
    mosquito_sprite = pygame.image.load("mosquito.png").convert_alpha()
    player_sprite   = pygame.image.load("slipper.png").convert_alpha()  # Opcional, si se quiere representar algún "jugador"
    sleeping_sprite = pygame.image.load("sleeping.png").convert_alpha()
    mosquito_size = (10, 10)
    player_size   = (20, 20)
    sleeping_size = (30, 30)
    mosquito_sprite = pygame.transform.scale(mosquito_sprite, mosquito_size)
    player_sprite   = pygame.transform.scale(player_sprite, player_size)
    sleeping_sprite = pygame.transform.scale(sleeping_sprite, sleeping_size)

    running = True
    # (Opcional) Si se desea enviar comandos al servidor usando las flechas,
    # se pueden detectar las teclas y enviarlas en cada ciclo.
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Manejo de teclas para enviar comandos de control al servidor:
        keys = pygame.key.get_pressed()
        try:
            if keys[pygame.K_LEFT]:
                client_socket.sendall("MOVE LEFT".encode())
            if keys[pygame.K_RIGHT]:
                client_socket.sendall("MOVE RIGHT".encode())
            if keys[pygame.K_UP]:
                client_socket.sendall("MOVE UP".encode())
            if keys[pygame.K_DOWN]:
                client_socket.sendall("MOVE DOWN".encode())
        except Exception as e:
            print("Error enviando comando:", e)

        screen.fill((0, 0, 0))
        
        # Obtener el estado actual enviado por el servidor
        with state_lock:
            current_state = server_state
        
        if current_state is not None:
            # Suponemos que el estado recibido incluye:
            #   "mosquito_pos", "mosquito_vel", "dust_particles" (un diccionario por zona) y "level"
            mosquito_pos   = current_state.get("mosquito_pos", [300, 300])
            dust_particles = current_state.get("dust_particles", {})
            level          = current_state.get("level", 1)
            
            # Dibujar el "mosquito" (por ejemplo, como un círculo rojo)
            pygame.draw.circle(screen, (255, 0, 0), (int(mosquito_pos[0]), int(mosquito_pos[1])), 10)
            level_text = font.render(f"Nivel: {level}", True, (255,255,255))
            screen.blit(level_text, (10, 10))
            
            # Para simplificar, definimos las zonas fijas (deben coincidir con la configuración en RoombaWorld)
            zone_rects = {
                "Zona 1": (50, 41, 500, 150),
                "Zona 2": (50, 190, 101, 220),
                "Zona 3": (241, 190, 309, 220),
                "Zona 4": (50, 408, 500, 150)
            }
            # Dibujar las zonas y la "gente durmiendo"
            for zona, rect in zone_rects.items():
                pygame.draw.rect(screen, (70,70,200), rect, 2)
                zone_text = font.render(zona, True, (200,200,200))
                screen.blit(zone_text, (rect[0] + 5, rect[1] + 5))
                # Mostrar cuenta de partículas
                count = len(dust_particles.get(zona, []))
                count_text = font.render(f"Gente: {count}", True, (200,200,200))
                screen.blit(count_text, (rect[0] + 5, rect[1] + 30))
                # Dibujar cada partícula en la zona (usando el sprite "sleeping")
                for (x, y) in dust_particles.get(zona, []):
                    screen.blit(sleeping_sprite, (x - sleeping_size[0]//2, y - sleeping_size[1]//2))
            
            # (Opcional) Dibujar el "jugador" si se requiere una representación (aunque la simulación
            # se centra en la lógica del mundo)
            # Aquí podrías agregar código para representar un jugador, si es necesario.

        pygame.display.flip()
        clock.tick(60)
    
    global stop_receptor
    stop_receptor = True
    client_socket.close()
    pygame.quit()

if __name__ == '__main__':
    main()
