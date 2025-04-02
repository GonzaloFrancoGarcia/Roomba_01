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

def find_zone(x, y, zone_rects):
    """
    Retorna la clave de la zona en la que se encuentra el punto (x, y).
    Si (x, y) no está en ninguna zona, retorna None.
    """
    for zone, rect in zone_rects.items():
        rx, ry, rw, rh = rect
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            return zone
    return None

def main():
    host = "127.0.0.1"
    puerto = 8809
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, puerto))
    except Exception as e:
        print("No se pudo conectar al servidor:", e)
        return

    # Inicia el hilo receptor para leer el estado del mundo desde el servidor.
    receptor = threading.Thread(target=recibir_estado, args=(client_socket,), daemon=True)
    receptor.start()

    pygame.init()
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 600
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Cliente Roomba - Visualización del Mundo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 16)
    
    # Definimos un diccionario fijo para las zonas (como en roomba.py)
    fixed_zone_rects = {
        "Zona 1": (50, 41, 500, 150),
        "Zona 2": (50, 190, 101, 220),
        "Zona 3": (241, 190, 309, 220),
        "Zona 4": (50, 408, 500, 150)
    }
    
    # Cargar recursos gráficos
    mosquito_sprite = pygame.image.load("mosquito.png").convert_alpha()
    player_sprite   = pygame.image.load("slipper.png").convert_alpha()  # Jugador (chancla)
    sleeping_sprite = pygame.image.load("sleeping.png").convert_alpha()
    
    # Ajustar tamaños de sprites según lo esperado:
    mosquito_size = (10, 10)
    player_size   = (20, 20)
    sleeping_size = (30, 30)
    mosquito_sprite = pygame.transform.scale(mosquito_sprite, mosquito_size)
    player_sprite   = pygame.transform.scale(player_sprite, player_size)
    sleeping_sprite = pygame.transform.scale(sleeping_sprite, sleeping_size)
    
    # Inicializar la posición del jugador. Para fomentar movimientos entre zonas (1,2,3),
    # ubicamos el centro en una posición que pertenezca a, por ejemplo, Zona 1.
    player_pos = [100, 100]  
    player_speed = 5
    
    # Determinar la zona en la que se encuentra inicialmente el jugador
    current_zone = find_zone(player_pos[0], player_pos[1], fixed_zone_rects)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Detectar teclas para mover al jugador (chancla)
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
        
        # Calcular la posición candidata para el centro del jugador.
        candidate_x = player_pos[0] + dx
        candidate_y = player_pos[1] + dy
        
        # Verificar en qué zona caería el centro candidato.
        candidate_zone = find_zone(candidate_x, candidate_y, fixed_zone_rects)
        # Si se encuentra una zona, se actualiza el jugador y se permite la transición de zona.
        if candidate_zone is not None:
            player_pos[0] = candidate_x
            player_pos[1] = candidate_y
            current_zone = candidate_zone  # Actualizamos la zona actual del jugador.
        # Sino, no se actualiza la posición, manteniendo la restricción.
        
        screen.fill((0, 0, 0))
        
        # Obtener el estado del mundo del servidor (o usar valores predeterminados)
        with state_lock:
            current_state = server_state
        if current_state is not None:
            mosquito_pos = current_state.get("mosquito_pos", [300,300])
            dust_particles = current_state.get("dust_particles", {})
            level = current_state.get("level", 1)
            zone_rects = current_state.get("zone_rects", fixed_zone_rects)
        else:
            mosquito_pos = [300,300]
            dust_particles = {}
            level = 1
            zone_rects = fixed_zone_rects
        
        # Dibujar el sprite del mosquito
        screen.blit(mosquito_sprite, (
            int(mosquito_pos[0]) - mosquito_size[0] // 2,
            int(mosquito_pos[1]) - mosquito_size[1] // 2)
        )
        
        # Dibujar cada zona y sus partículas ("gente durmiendo")
        for zona, rect in zone_rects.items():
            pygame.draw.rect(screen, (70,70,200), rect, 2)
            zone_text = font.render(zona, True, (200,200,200))
            screen.blit(zone_text, (rect[0] + 5, rect[1] + 5))
            count = len(dust_particles.get(zona, []))
            count_text = font.render(f"Gente: {count}", True, (200,200,200))
            screen.blit(count_text, (rect[0] + 5, rect[1] + 30))
            for (x, y) in dust_particles.get(zona, []):
                screen.blit(sleeping_sprite, (x - sleeping_size[0]//2, y - sleeping_size[1]//2))
        
        # Mostrar el nivel
        level_text = font.render(f"Nivel: {level}", True, (255,255,255))
        screen.blit(level_text, (10, 10))
        
        # Dibujar el sprite del jugador (chancla)
        screen.blit(player_sprite, (
            int(player_pos[0]) - player_size[0] // 2,
            int(player_pos[1]) - player_size[1] // 2)
        )
        
        pygame.display.flip()
        clock.tick(60)
    
    global stop_receptor
    stop_receptor = True
    client_socket.close()
    pygame.quit()

if __name__ == '__main__':
    main()
