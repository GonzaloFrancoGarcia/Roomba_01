import socket
import threading
import time
import json
import pygame

# Variables globales para almacenar el estado recibido y sincronizar el acceso.
server_state = None
state_lock = threading.Lock()
stop_receptor = False

def recibir_estado(client_socket):
    """
    En un hilo se recibe continuamente el estado del mundo (en JSON) enviado por el servidor.
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

def main():
    host = "127.0.0.1"
    puerto = 8809
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, puerto))
    except Exception as e:
        print("No se pudo conectar al servidor:", e)
        return

    # Iniciar el hilo receptor para obtener el estado.
    receptor = threading.Thread(target=recibir_estado, args=(client_socket,), daemon=True)
    receptor.start()

    pygame.init()
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 600
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Cliente Roomba - Visualización del Mundo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 16)
    
    # Cargar recursos gráficos.
    mosquito_sprite = pygame.image.load("mosquito.png").convert_alpha()
    player_sprite = pygame.image.load("slipper.png").convert_alpha()  # (opcional, para representar un "jugador")
    sleeping_sprite = pygame.image.load("sleeping.png").convert_alpha()
    mosquito_size = (10, 10)
    player_size = (20, 20)
    sleeping_size = (30, 30)
    mosquito_sprite = pygame.transform.scale(mosquito_sprite, mosquito_size)
    player_sprite = pygame.transform.scale(player_sprite, player_size)
    sleeping_sprite = pygame.transform.scale(sleeping_sprite, sleeping_size)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Detectar teclas y enviar comandos al servidor para modificar la dirección.
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
        
        screen.fill((0,0,0))
        with state_lock:
            current_state = server_state
        if current_state is not None:
            # Se asume que el estado enviado incluye: mosquito_pos, dust_particles, level, zone_rects.
            mosquito_pos = current_state.get("mosquito_pos", [300,300])
            dust_particles = current_state.get("dust_particles", {})
            level = current_state.get("level", 1)
            # El servidor envía zone_rects; si no, definimos unas zonas fijas:
            zone_rects = current_state.get("zone_rects", {
                "Zona 1": (50, 41, 500, 150),
                "Zona 2": (50, 190, 101, 220),
                "Zona 3": (241, 190, 309, 220),
                "Zona 4": (50, 408, 500, 150)
            })
            
            # Dibujar el mosquito como un círculo rojo.
            pygame.draw.circle(screen, (255,0,0), (int(mosquito_pos[0]), int(mosquito_pos[1])), 10)
            nivel_text = font.render(f"Nivel: {level}", True, (255,255,255))
            screen.blit(nivel_text, (10, 10))
            
            # Dibujar las zonas y sus partículas ("gente durmiendo")
            for zona, rect in zone_rects.items():
                pygame.draw.rect(screen, (70,70,200), rect, 2)
                txt_zone = font.render(zona, True, (200,200,200))
                screen.blit(txt_zone, (rect[0] + 5, rect[1] + 5))
                count = len(dust_particles.get(zona, []))
                txt_count = font.render(f"Gente: {count}", True, (200,200,200))
                screen.blit(txt_count, (rect[0] + 5, rect[1] + 30))
                for (x, y) in dust_particles.get(zona, []):
                    screen.blit(sleeping_sprite, (x - sleeping_size[0]//2, y - sleeping_size[1]//2))
            
            # (Opcional) Puedes dibujar un "jugador"; aquí simplemente se muestra un sprite en una posición fija.
            screen.blit(player_sprite, (50, WINDOW_HEIGHT - 70))
        
        pygame.display.flip()
        clock.tick(60)
    global stop_receptor
    stop_receptor = True
    client_socket.close()
    pygame.quit()

if __name__ == '__main__':
    main()
