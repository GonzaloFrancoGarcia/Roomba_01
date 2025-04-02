import socket
import threading
import time
import json
import pygame

# Variables globales para almacenar el estado recibido del servidor
server_state = None
state_lock = threading.Lock()
stop_receptor = False

def recibir_estado(client_socket):
    """
    Hilo receptor que actualiza continuamente la variable global server_state
    con el estado en formato JSON enviado por el servidor.
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
                break
        except socket.timeout:
            continue
        except Exception as e:
            print("Error recibiendo datos:", e)
            break

def allowed_player_center(x, y, zone_rects):
    """
    Verifica si el punto (x, y) (la posición central del jugador)
    se encuentra dentro de alguna de las zonas definidas en zone_rects.
    """
    for rect in zone_rects.values():
        rx, ry, rw, rh = rect
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            return True
    return False

def main():
    host = "127.0.0.1"
    puerto = 8809
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, puerto))
    except Exception as e:
        print("No se pudo conectar al servidor:", e)
        return

    # Inicia el hilo receptor para obtener el estado desde el servidor
    receptor = threading.Thread(target=recibir_estado, args=(client_socket,), daemon=True)
    receptor.start()

    pygame.init()
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 600
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Cliente Roomba - Visualización del Mundo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 16)
    
    # Cargar recursos gráficos
    mosquito_sprite = pygame.image.load("mosquito.png").convert_alpha()
    player_sprite   = pygame.image.load("slipper.png").convert_alpha()  # Sprite de la chancla (jugador)
    sleeping_sprite = pygame.image.load("sleeping.png").convert_alpha()
    
    # Ajustamos el tamaño de los sprites para que coincida con el juego original:
    mosquito_size = (10, 10)
    player_size   = (20, 20)
    sleeping_size = (30, 30)
    mosquito_sprite = pygame.transform.scale(mosquito_sprite, mosquito_size)
    player_sprite   = pygame.transform.scale(player_sprite, player_size)
    sleeping_sprite = pygame.transform.scale(sleeping_sprite, sleeping_size)
    
    # Posición inicial del jugador (chancla) – se mueve localmente
    player_pos = [100, WINDOW_HEIGHT - 70]
    player_speed = 5
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Detectar teclas para mover al jugador (chancla) localmente
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:
            dx = -player_speed
        if keys[pygame.K_RIGHT]:
            dx = player_speed
        if keys[pygame.K_UP]:
            dy = -player_speed
        if keys[pygame.K_DOWN]:
            dy = player_speed
        
        # Calcula la nueva posición (candidata del centro del jugador)
        candidate_x = player_pos[0] + dx
        candidate_y = player_pos[1] + dy
        
        # Obtener las zonas (del estado recibido, o en defecto, usar unas zonas por defecto)
        with state_lock:
            current_state = server_state
        if current_state is not None:
            zone_rects = current_state.get("zone_rects", {
                "Zona 1": (50, 41, 500, 150),
                "Zona 2": (50, 190, 101, 220),
                "Zona 3": (241, 190, 309, 220),
                "Zona 4": (50, 408, 500, 150)
            })
        else:
            zone_rects = {
                "Zona 1": (50, 41, 500, 150),
                "Zona 2": (50, 190, 101, 220),
                "Zona 3": (241, 190, 309, 220),
                "Zona 4": (50, 408, 500, 150)
            }
        
        # Actualiza la posición solo si el centro candidato se encuentra dentro de alguna zona
        if allowed_player_center(candidate_x, candidate_y, zone_rects):
            player_pos[0] = candidate_x
            player_pos[1] = candidate_y
        
        screen.fill((0, 0, 0))
        
        if current_state is not None:
            # Extraer el estado enviado por el servidor
            mosquito_pos = current_state.get("mosquito_pos", [300,300])
            dust_particles = current_state.get("dust_particles", {})
            level = current_state.get("level", 1)
            
            # Dibujar el sprite del mosquito (asumiendo que el servidor lo actualiza correctamente)
            screen.blit(mosquito_sprite, (
                int(mosquito_pos[0]) - mosquito_size[0] // 2,
                int(mosquito_pos[1]) - mosquito_size[1] // 2)
            )
            
            # Dibujar cada zona y las partículas (gente durmiendo)
            for zona, rect in zone_rects.items():
                pygame.draw.rect(screen, (70,70,200), rect, 2)
                zone_text = font.render(zona, True, (200,200,200))
                screen.blit(zone_text, (rect[0] + 5, rect[1] + 5))
                count = len(dust_particles.get(zona, []))
                count_text = font.render(f"Gente: {count}", True, (200,200,200))
                screen.blit(count_text, (rect[0] + 5, rect[1] + 30))
                for (x, y) in dust_particles.get(zona, []):
                    screen.blit(sleeping_sprite, (x - sleeping_size[0] // 2, y - sleeping_size[1] // 2))
            
            # Mostrar información del nivel
            level_text = font.render(f"Nivel: {level}", True, (255,255,255))
            screen.blit(level_text, (10, 10))
        
        # Dibujar el sprite del jugador (chancla)
        screen.blit(player_sprite, (int(player_pos[0]) - player_size[0] // 2, int(player_pos[1]) - player_size[1] // 2))
        
        pygame.display.flip()
        clock.tick(60)
    
    global stop_receptor
    stop_receptor = True
    client_socket.close()
    pygame.quit()

if __name__ == '__main__':
    main()
