import concurrent.futures
import threading
import time
import random
import math
import pygame

def calcular_area(largo, ancho):
    """Calcula el área de una zona (cm²)."""
    return largo * ancho

def generar_dust(zona, dust_particles, lock, stop_event, zona_rect, nivel):
    """
    Genera "gente durmiendo" en la zona (representado por círculos grises).
    Se utiliza un delay mayor en niveles bajos para que en el nivel 1 aparezca menos gente.
    """
    x0, y0, width, height = zona_rect
    while not stop_event.is_set():
        # Para que en niveles bajos (nivel 1) aparezca menos gente, se usa un delay mayor.
        delay = random.uniform(6.0, 8.0) / nivel
        time.sleep(delay)
        x = random.randint(x0, x0 + width)
        y = random.randint(y0, y0 + height)
        with lock:
            dust_particles[zona].append((x, y))
        print(f"{zona}: Gente durmiendo generada en ({x}, {y}). Total: {len(dust_particles[zona])}")

def mover_mosquito(mosquito_pos, mosquito_vel, dust_particles, lock, stop_event, window_size, zone_rects, velocidad_base, tasa_limpeza):
    """
    Controla el movimiento del mosquito (equivalente al Roomba) con los siguientes comportamientos:
      - Por defecto se mueve aleatoriamente dentro de las zonas.
      - Si pasan 5 segundos sin picar a nadie, se activa el modo SEEK y se dirige hacia la gente durmiendo más cercana.
      - En modo SEEK, si pasan 10 segundos sin picar, se cancela el modo y vuelve a movimiento aleatorio.
      - En modo aleatorio, si se acerca (umbral 30 píxeles) a alguien, ajusta su dirección para acercarse.
      
    "Picar" significa eliminar a la gente durmiendo (se borran sus coordenadas).
    """
    cleaning_radius = 10  # Radio en píxeles para "picar"
    dt = 0.05           # Intervalo de actualización en segundos
    last_print = time.time()
    window_width, window_height = window_size

    last_collection_time = time.time()  # Último momento en que se picó gente
    in_seek_mode = False
    seek_start_time = None

    def allowed_position(x, y):
        for rect in zone_rects.values():
            rx, ry, rw, rh = rect
            if rx <= x <= rx+rw and ry <= y <= ry+rh:
                return True
        return False

    while not stop_event.is_set():
        time.sleep(dt)
        with lock:
            current_time = time.time()
            # Activar modo SEEK después de 5 segundos sin picar.
            if not in_seek_mode and (current_time - last_collection_time > 5):
                in_seek_mode = True
                seek_start_time = current_time
                print("Modo SEEK activado: 5 segundos sin picar gente.")
            # Si en modo SEEK pasan 5 segundos sin picar, cancelar el modo y volver a aleatorio.
            if in_seek_mode and (current_time - seek_start_time > 5):
                in_seek_mode = False
                mosquito_vel[0] = random.choice([-1, 1]) * velocidad_base * (tasa_limpeza / 1000)
                mosquito_vel[1] = random.choice([-1, 1]) * velocidad_base * (tasa_limpeza / 1000)
                last_collection_time = current_time
                print("Modo SEEK cancelado: 5 segundos sin picar, volviendo a aleatorio.")

            # Modo SEEK: buscar la gente durmiendo más cercana y ajustar la dirección.
            if in_seek_mode:
                candidate = None
                best_dist = float('inf')
                for zona in dust_particles:
                    for (x, y) in dust_particles[zona]:
                        dist = (x - mosquito_pos[0])**2 + (y - mosquito_pos[1])**2
                        if dist < best_dist:
                            best_dist = dist
                            candidate = (x, y)
                if candidate is not None:
                    dx = candidate[0] - mosquito_pos[0]
                    dy = candidate[1] - mosquito_pos[1]
                    norm = math.sqrt(dx*dx + dy*dy)
                    if norm > 0:
                        speed = math.sqrt(mosquito_vel[0]**2 + mosquito_vel[1]**2)
                        mosquito_vel[0] = speed * dx / norm
                        mosquito_vel[1] = speed * dy / norm
                    print("Modo SEEK: ajustando dirección hacia la gente durmiendo más cercana.")

            # Modo aleatorio: si se está cerca (umbral 30 píxeles) de alguien, ajustar dirección.
            if not in_seek_mode:
                near_threshold = 30  # píxeles
                candidate_near = None
                best_dist_near = float('inf')
                for zona in dust_particles:
                    for (x, y) in dust_particles[zona]:
                        dx = x - mosquito_pos[0]
                        dy = y - mosquito_pos[1]
                        dist = math.sqrt(dx*dx + dy*dy)
                        if dist < near_threshold and dist < best_dist_near:
                            best_dist_near = dist
                            candidate_near = (x, y)
                if candidate_near is not None:
                    dx = candidate_near[0] - mosquito_pos[0]
                    dy = candidate_near[1] - mosquito_pos[1]
                    norm = math.sqrt(dx*dx + dy*dy)
                    if norm > 0:
                        speed = math.sqrt(mosquito_vel[0]**2 + mosquito_vel[1]**2)
                        mosquito_vel[0] = speed * dx / norm
                        mosquito_vel[1] = speed * dy / norm
                    print("Aleatorio: acercándose a gente durmiendo cercana.")

            # Calcular la nueva posición candidata.
            new_x = mosquito_pos[0] + mosquito_vel[0]
            new_y = mosquito_pos[1] + mosquito_vel[1]
            if allowed_position(new_x, new_y):
                mosquito_pos[0] = new_x
                mosquito_pos[1] = new_y
            else:
                if allowed_position(mosquito_pos[0] + mosquito_vel[0], mosquito_pos[1]):
                    mosquito_pos[0] += mosquito_vel[0]
                    mosquito_vel[1] = -mosquito_vel[1]
                elif allowed_position(mosquito_pos[0], mosquito_pos[1] + mosquito_vel[1]):
                    mosquito_pos[1] += mosquito_vel[1]
                    mosquito_vel[0] = -mosquito_vel[0]
                else:
                    mosquito_vel[0] = -mosquito_vel[0]
                    mosquito_vel[1] = -mosquito_vel[1]

            # Proceso de "picadura": si el mosquito está dentro del radio, se elimina esa gente durmiendo.
            cleaned = False
            for zona in dust_particles:
                new_list = []
                for (x, y) in dust_particles[zona]:
                    if (x - mosquito_pos[0])**2 + (y - mosquito_pos[1])**2 >= cleaning_radius**2:
                        new_list.append((x, y))
                    else:
                        cleaned = True
                        print(f"Mosquito picó gente en {zona} en ({x}, {y})")
                dust_particles[zona] = new_list

            if cleaned:
                last_collection_time = current_time
                if in_seek_mode:
                    in_seek_mode = False
                    print("Gente picada en modo SEEK; volviendo a aleatorio.")

            if time.time() - last_print >= 1:
                total = sum(len(lst) for lst in dust_particles.values())
                print(f"Mosquito en {mosquito_pos}; Gente durmiendo restante: {total}")
                last_print = time.time()

def allowed_position_general(x, y, zone_rects):
    """Verifica si (x, y) está dentro de alguna zona (usado por el jugador)."""
    for rect in zone_rects.values():
        rx, ry, rw, rh = rect
        if rx <= x <= rx+rw and ry <= y <= ry+rh:
            return True
    return False

def main():
    # ===================== DIMENSIONES Y CÁLCULO DE ÁREAS =====================
    zonas = {
        'Zona 1': (500, 150),
        'Zona 2': (101, 220),
        'Zona 3': (309, 220),
        'Zona 4': (500, 150)
    }
    tasa_limpeza = 1000  # Base para la velocidad del mosquito
    areas = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_zona = {executor.submit(calcular_area, largo, ancho): zona for zona, (largo, ancho) in zonas.items()}
        for future in concurrent.futures.as_completed(future_to_zona):
            zona = future_to_zona[future]
            try:
                areas[zona] = future.result()
                print(f"{zona}: Área {areas[zona]} cm²")
            except Exception as e:
                print(f"{zona} error: {e}")
    superficie_total = sum(areas.values())
    tiempo_limpeza = superficie_total / tasa_limpeza
    print(f"\nSuperficie Total a dormir: {superficie_total} cm²")
    print(f"Tiempo estimado: {tiempo_limpeza:.2f} seg\n")
    
    # ===================== CONFIGURAR PYGAME =====================
    ROOM_WIDTH_CM = 600
    ROOM_HEIGHT_CM = 600
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 600
    SCALE = min(WINDOW_WIDTH/ROOM_WIDTH_CM, WINDOW_HEIGHT/ROOM_HEIGHT_CM)
    
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Simulación Mosquito - Jugador vs Mosquito")
    clock = pygame.time.Clock()
    
    zone_positions = {
        'Zona 1': (50, 31),
        'Zona 2': (50, 180),
        'Zona 3': (240, 180),
        'Zona 4': (50, 397)
    }
    
    zone_rects = {}
    for zona, (largo, alto) in zonas.items():
        pos = zone_positions[zona]
        zone_rects[zona] = (int(pos[0]*SCALE),
                            int(pos[1]*SCALE),
                            int(largo*SCALE),
                            int(alto*SCALE))
    
    # ===================== VARIABLES COMPARTIDAS Y PERSONAJES =====================
    dust_particles = {zona: [] for zona in zonas}  # Representa la gente durmiendo.
    lock = threading.Lock()
    mosquito_stop_event = threading.Event()
    
    velocidad_base = 10  # Factor base para la velocidad.
    # Para el nivel 1, la velocidad del mosquito es: velocidad_base * (tasa_limpeza/1000).
    mosquito_vel = [
        random.choice([-1, 1]) * velocidad_base * (tasa_limpeza/1000),
        random.choice([-1, 1]) * velocidad_base * (tasa_limpeza/1000)
    ]
    mosquito_pos = [WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2]
    
    mosquito_thread = threading.Thread(
        target=mover_mosquito,
        args=(mosquito_pos, mosquito_vel, dust_particles, lock, mosquito_stop_event,
              (WINDOW_WIDTH, WINDOW_HEIGHT), zone_rects, velocidad_base, tasa_limpeza)
    )
    mosquito_thread.start()
    
    # Configuración del jugador.
    player_radius = 8
    player_pos = [int(100 * SCALE), int(100 * SCALE)]
    player_speed = 5
    game_over = False
    
    # ===================== BUCLE DE NIVELES =====================
    running = True
    level = 1
    font = pygame.font.SysFont(None, 24)
    
    while running:
        # Aquí comprobamos si vamos a iniciar un nuevo nivel.
        # Si ya se alcanza el nivel 3, no iniciamos un nuevo nivel y mostramos GAME OVER.
        if level >= 3:
            screen.fill((0, 0, 0))
            game_over_msg = font.render("GAME OVER", True, (255, 0, 0))
            screen.blit(game_over_msg, (WINDOW_WIDTH//2 - game_over_msg.get_width()//2,
                                        WINDOW_HEIGHT//2 - game_over_msg.get_height()//2))
            pygame.display.flip()
            time.sleep(3)
            break  # Salir del bucle de niveles.
        
        # Actualiza la velocidad del mosquito en función del nivel: en nivel 1, es rápido,
        # y en niveles superiores se reduce (dividiendo por el nivel).
        with lock:
            mosquito_vel[0] = random.choice([-1, 1]) * (velocidad_base / level) * (tasa_limpeza/1000)
            mosquito_vel[1] = random.choice([-1, 1]) * (velocidad_base / level) * (tasa_limpeza/1000)
        
        # Reiniciar la gente durmiendo para el nuevo nivel.
        with lock:
            for zona in dust_particles:
                dust_particles[zona].clear()
        
        current_dust_stop_event = threading.Event()
        # En niveles superiores se genera más gente (el delay se reduce proporcionalmente al nivel).
        current_simulation_duration = 10 * level
        dust_threads = []
        for zona, rect in zone_rects.items():
            t = threading.Thread(
                target=generar_dust,
                args=(zona, dust_particles, lock, current_dust_stop_event, rect, level)
            )
            t.start()
            dust_threads.append(t)
        
        level_start_time = time.time()
        level_complete = False
        
        while running and not level_complete and not game_over:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    dx, dy = 0, 0
                    if event.key == pygame.K_LEFT:
                        dx = -player_speed
                    elif event.key == pygame.K_RIGHT:
                        dx = player_speed
                    elif event.key == pygame.K_UP:
                        dy = -player_speed
                    elif event.key == pygame.K_DOWN:
                        dy = player_speed
                    candidate_x = player_pos[0] + dx
                    candidate_y = player_pos[1] + dy
                    if allowed_position_general(candidate_x, candidate_y, zone_rects):
                        player_pos[0] = candidate_x
                        player_pos[1] = candidate_y
            
            with lock:
                current_mosquito_pos = mosquito_pos[:]
            mosquito_radius = 8
            collision_threshold = mosquito_radius + player_radius + 2
            dist = math.sqrt((player_pos[0] - current_mosquito_pos[0])**2 +
                             (player_pos[1] - current_mosquito_pos[1])**2)
            if dist < collision_threshold:
                game_over = True
                running = False
                current_dust_stop_event.set()
            
            if time.time() - level_start_time > current_simulation_duration and not current_dust_stop_event.is_set():
                current_dust_stop_event.set()
            
            screen.fill((30, 30, 30))
            for zona, rect in zone_rects.items():
                pygame.draw.rect(screen, (70,70,200), rect, 2)
                text_zone = font.render(zona, True, (200,200,200))
                screen.blit(text_zone, (rect[0] + 5, rect[1] + 5))
                with lock:
                    dust_count = len(dust_particles[zona])
                text_dust = font.render(f"Gente: {dust_count}", True, (200,200,200))
                screen.blit(text_dust, (rect[0] + 5, rect[1] + 30))
            
            with lock:
                dust_copy = {z: dust_particles[z][:] for z in dust_particles}
                current_mosquito_pos = mosquito_pos[:]
            for zona, dust_list in dust_copy.items():
                for (x, y) in dust_list:
                    pygame.draw.circle(screen, (128,128,128), (x, y), 4)
            
            pygame.draw.circle(screen, (0,255,0),
                               (int(current_mosquito_pos[0]), int(current_mosquito_pos[1])), 8)
            text_mosquito = font.render(f"Mosquito: ({int(current_mosquito_pos[0])}, {int(current_mosquito_pos[1])})", True, (0,255,0))
            screen.blit(text_mosquito, (WINDOW_WIDTH - 220, WINDOW_HEIGHT - 30))
            
            pygame.draw.circle(screen, (255,0,0),
                               (int(player_pos[0]), int(player_pos[1])), player_radius)
            text_player = font.render(f"Jugador: ({int(player_pos[0])}, {int(player_pos[1])})", True, (255,0,0))
            screen.blit(text_player, (20, WINDOW_HEIGHT - 30))
            
            info_lines = [
                f"Nivel: {level}",
                f"Gente total: {sum(len(lst) for lst in dust_particles.values())}",
                f"Superficie: {superficie_total} cm²",
                f"Tiempo estimado: {tiempo_limpeza:.2f} seg"
            ]
            info_x = 320
            info_y = 10
            for line in info_lines:
                info_surface = font.render(line, True, (255,255,255))
                screen.blit(info_surface, (info_x, info_y))
                info_y += info_surface.get_height() + 5
            
            pygame.display.flip()
            clock.tick(30)
            
            with lock:
                if current_dust_stop_event.is_set() and sum(len(lst) for lst in dust_particles.values()) == 0:
                    level_complete = True
        
        for t in dust_threads:
            t.join()
        
        if game_over:
            break
        
        # Mostrar mensaje de nivel completado.
        if running:
            level_msg = font.render(f"Nivel {level} completado!", True, (0,255,255))
            screen.blit(level_msg, (WINDOW_WIDTH//2 - level_msg.get_width()//2, WINDOW_HEIGHT//2))
            pygame.display.flip()
            time.sleep(2)
        level += 1
    
    # Pantalla final: si el jugador colisionó con el mosquito, ha eliminado al mosquito.
    if game_over:
        screen.fill((0,0,0))
        win_msg = font.render("¡Has eliminado al mosquito!", True, (0,255,0))
        screen.blit(win_msg, (WINDOW_WIDTH//2 - win_msg.get_width()//2,
                              WINDOW_HEIGHT//2 - win_msg.get_height()//2))
        pygame.display.flip()
        time.sleep(3)
    
    mosquito_stop_event.set()
    mosquito_thread.join()
    pygame.quit()

def allowed_position_general(x, y, zone_rects):
    """Función genérica para verificar si (x, y) está dentro de alguna zona."""
    for rect in zone_rects.values():
        rx, ry, rw, rh = rect
        if rx <= x <= rx+rw and ry <= y <= ry+rh:
            return True
    return False

if __name__ == '__main__':
    main()
