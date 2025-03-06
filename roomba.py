import concurrent.futures
import threading
import time
import random
import math
import pygame

def calcular_area(largo, ancho):
    """Calcula el área de una zona (cm²)."""
    return largo * ancho

def generar_dust(zona, dust_particles, lock, stop_event, zona_rect):
    """
    Genera motas de polvo aleatoriamente dentro del rectángulo visual de la zona.
    Cada intervalo aleatorio (entre 0.5 y 2.0 s) se añade una mota (coordenada) a la lista.
    """
    x0, y0, width, height = zona_rect
    while not stop_event.is_set():
        time.sleep(random.uniform(0.5, 2.0))
        # Generar una mota en una posición aleatoria dentro del área visual de la zona.
        x = random.randint(x0, x0 + width)
        y = random.randint(y0, y0 + height)
        with lock:
            dust_particles[zona].append((x, y))
        print(f"{zona}: Generada mota en ({x}, {y}). Total: {len(dust_particles[zona])}")

def mover_roomba(roomba_pos, roomba_vel, dust_particles, lock, stop_event, window_size, zone_rects, velocidad_base, tasa_limpeza):
    """
    Actualiza continuamente la posición del Roomba y limpia las motas que se encuentren en su radio.
    
    Comportamientos:
      - Por defecto, se mueve de forma aleatoria (limitado a las zonas).
      - Si pasan 20 segundos sin limpiar ninguna mota, se activa el modo SEEK, en el que el Roomba se dirige
        hacia la mota más cercana.
      - En modo SEEK, si pasan 10 segundos sin limpiar ninguna mota (por ejemplo, si la dirección lo lleva a una pared),
        se cancela el modo SEEK y vuelve al movimiento aleatorio.
      - Además, en el modo aleatorio, si el Roomba se acerca a una mota (por casualidad), ajusta su dirección
        para ir a recogerla.
    """
    cleaning_radius = 10  # radio (píxeles) para limpiar una mota
    dt = 0.05           # intervalo en segundos
    last_print = time.time()
    window_width, window_height = window_size

    # Tiempo del último momento en que se limpió alguna mota.
    last_collection_time = time.time()
    in_seek_mode = False
    seek_start_time = None

    def allowed_position(x, y):
        """Retorna True si (x, y) está dentro de alguna de las zonas en zone_rects."""
        for rect in zone_rects.values():
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return True
        return False

    while not stop_event.is_set():
        time.sleep(dt)
        with lock:
            current_time = time.time()

            # Si han pasado 20 segundos sin limpiar, activar modo SEEK (si aún no está activo).
            if not in_seek_mode and (current_time - last_collection_time > 20):
                in_seek_mode = True
                seek_start_time = current_time
                print("Modo SEEK activado: 20 segundos sin limpiar polvo.")
            # Si en modo SEEK pasan 10 segundos sin limpiar, cancelar SEEK.
            if in_seek_mode and (current_time - seek_start_time > 10):
                in_seek_mode = False
                # Restablecer la velocidad aleatoria.
                roomba_vel[0] = random.choice([-1, 1]) * velocidad_base * (tasa_limpeza / 1000)
                roomba_vel[1] = random.choice([-1, 1]) * velocidad_base * (tasa_limpeza / 1000)
                last_collection_time = current_time
                print("Modo SEEK cancelado: 10 segundos sin recoger mota, volviendo a aleatorio.")

            # En modo SEEK, buscar la mota más cercana y ajustar la dirección.
            if in_seek_mode:
                candidate = None
                best_dist = float('inf')
                for zona in dust_particles:
                    for (x, y) in dust_particles[zona]:
                        dist = (x - roomba_pos[0])**2 + (y - roomba_pos[1])**2
                        if dist < best_dist:
                            best_dist = dist
                            candidate = (x, y)
                if candidate is not None:
                    dx = candidate[0] - roomba_pos[0]
                    dy = candidate[1] - roomba_pos[1]
                    norm = math.sqrt(dx*dx + dy*dy)
                    if norm > 0:
                        speed = math.sqrt(roomba_vel[0]**2 + roomba_vel[1]**2)
                        roomba_vel[0] = speed * dx / norm
                        roomba_vel[1] = speed * dy / norm
                    print("Modo SEEK: Ajustando dirección hacia la mota más cercana.")

            # En modo aleatorio, si se pasa cerca de una mota, ajustar la dirección para recogerla.
            if not in_seek_mode:
                near_threshold = 30  # Umbral de cercanía (píxeles); ajústalo según convenga.
                candidate_near = None
                best_dist_near = float('inf')
                for zona in dust_particles:
                    for (x, y) in dust_particles[zona]:
                        dx = x - roomba_pos[0]
                        dy = y - roomba_pos[1]
                        dist = math.sqrt(dx*dx + dy*dy)
                        if dist < near_threshold and dist < best_dist_near:
                            best_dist_near = dist
                            candidate_near = (x, y)
                if candidate_near is not None:
                    dx = candidate_near[0] - roomba_pos[0]
                    dy = candidate_near[1] - roomba_pos[1]
                    norm = math.sqrt(dx*dx + dy*dy)
                    if norm > 0:
                        speed = math.sqrt(roomba_vel[0]**2 + roomba_vel[1]**2)
                        roomba_vel[0] = speed * dx / norm
                        roomba_vel[1] = speed * dy / norm
                    print("Movimiento aleatorio: acercándose a una mota cercana.")

            # Calcular la nueva posición tentativa.
            new_x = roomba_pos[0] + roomba_vel[0]
            new_y = roomba_pos[1] + roomba_vel[1]
            if allowed_position(new_x, new_y):
                roomba_pos[0] = new_x
                roomba_pos[1] = new_y
            else:
                if allowed_position(roomba_pos[0] + roomba_vel[0], roomba_pos[1]):
                    roomba_pos[0] += roomba_vel[0]
                    roomba_vel[1] = -roomba_vel[1]
                elif allowed_position(roomba_pos[0], roomba_pos[1] + roomba_vel[1]):
                    roomba_pos[1] += roomba_vel[1]
                    roomba_vel[0] = -roomba_vel[0]
                else:
                    roomba_vel[0] = -roomba_vel[0]
                    roomba_vel[1] = -roomba_vel[1]

            # Proceso de limpieza: eliminar motas dentro del radio.
            cleaned_this_iteration = False
            for zona in dust_particles:
                new_list = []
                for (x, y) in dust_particles[zona]:
                    if (x - roomba_pos[0])**2 + (y - roomba_pos[1])**2 >= cleaning_radius**2:
                        new_list.append((x, y))
                    else:
                        cleaned_this_iteration = True
                        print(f"Roomba limpió mota en {zona} en ({x}, {y})")
                dust_particles[zona] = new_list

            # Si se ha limpiado alguna mota, actualizar el temporizador y salir de SEEK si estaba activo.
            if cleaned_this_iteration:
                last_collection_time = current_time
                if in_seek_mode:
                    in_seek_mode = False
                    print("Mota limpiada en modo SEEK; volviendo a movimiento aleatorio.")

            if time.time() - last_print >= 1:
                total_dust = sum(len(lst) for lst in dust_particles.values())
                print(f"Roomba en {roomba_pos}; Polvo total restante: {total_dust}")
                last_print = time.time()

def main():
    # ===================== DIMENSIONES Y CÁLCULO DE ÁREAS =====================
    zonas = {
        'Zona 1': (500, 150),
        'Zona 2': (101, 220),
        'Zona 3': (309, 220),
        'Zona 4': (500, 150)
    }
    tasa_limpeza = 1000  # cm²/s; valor base para la velocidad del Roomba.
    areas = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_zona = {
            executor.submit(calcular_area, largo, ancho): zona 
            for zona, (largo, ancho) in zonas.items()
        }
        for future in concurrent.futures.as_completed(future_to_zona):
            zona = future_to_zona[future]
            try:
                areas[zona] = future.result()
                print(f"{zona}: Área {areas[zona]} cm²")
            except Exception as e:
                print(f"{zona} error: {e}")
    superficie_total = sum(areas.values())
    tiempo_limpeza = superficie_total / tasa_limpeza
    print(f"\nSuperficie Total a limpiar: {superficie_total} cm²")
    print(f"Tiempo estimado de limpieza (seg): {tiempo_limpeza:.2f}\n")
    
    # ===================== CONFIGURAR PYGAME =====================
    ROOM_WIDTH_CM = 600
    ROOM_HEIGHT_CM = 600
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 600
    SCALE = min(WINDOW_WIDTH / ROOM_WIDTH_CM, WINDOW_HEIGHT / ROOM_HEIGHT_CM)
    
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Simulación Roomba - Comportamientos Avanzados")
    clock = pygame.time.Clock()
    
    # Posiciones (top-left, en cm) de cada zona según el plano.
    zone_positions = {
        'Zona 1': (50, 31),
        'Zona 2': (50, 180),
        'Zona 3': (240, 180),
        'Zona 4': (50, 397)
    }
    
    zone_rects = {}
    for zona, (largo, alto) in zonas.items():
        pos = zone_positions[zona]
        zone_rects[zona] = (
            int(pos[0] * SCALE),
            int(pos[1] * SCALE),
            int(largo * SCALE),
            int(alto * SCALE)
        )
    
    # ===================== VARIABLES COMPARTIDAS =====================
    dust_particles = {zona: [] for zona in zonas}
    lock = threading.Lock()
    roomba_stop_event = threading.Event()
    
    velocidad_base = 2  # Factor base para la velocidad
    roomba_vel = [
        random.choice([-1, 1]) * velocidad_base * (tasa_limpeza / 1000),
        random.choice([-1, 1]) * velocidad_base * (tasa_limpeza / 1000)
    ]
    roomba_pos = [WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2]
    
    roomba_thread = threading.Thread(
        target=mover_roomba,
        args=(roomba_pos, roomba_vel, dust_particles, lock, roomba_stop_event,
              (WINDOW_WIDTH, WINDOW_HEIGHT), zone_rects, velocidad_base, tasa_limpeza)
    )
    roomba_thread.start()
    
    # ===================== BUCLE DE NIVELES =====================
    running = True
    level = 1
    font = pygame.font.SysFont(None, 24)
    
    while running:
        with lock:
            for zona in dust_particles:
                dust_particles[zona].clear()
        
        current_dust_stop_event = threading.Event()
        current_simulation_duration = 10 * level
        
        dust_threads = []
        for zona, rect in zone_rects.items():
            t = threading.Thread(
                target=generar_dust,
                args=(zona, dust_particles, lock, current_dust_stop_event, rect)
            )
            t.start()
            dust_threads.append(t)
        
        level_start_time = time.time()
        level_complete = False
        
        while running and not level_complete:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            if time.time() - level_start_time > current_simulation_duration and not current_dust_stop_event.is_set():
                current_dust_stop_event.set()
            
            screen.fill((30, 30, 30))
            for zona, rect in zone_rects.items():
                pygame.draw.rect(screen, (70, 70, 200), rect, 2)
                text_zone = font.render(zona, True, (200, 200, 200))
                screen.blit(text_zone, (rect[0] + 5, rect[1] + 5))
                with lock:
                    dust_count = len(dust_particles[zona])
                text_dust = font.render(f"Polvo: {dust_count}", True, (200, 200, 200))
                screen.blit(text_dust, (rect[0] + 5, rect[1] + 30))
            
            with lock:
                dust_copy = {z: dust_particles[z][:] for z in dust_particles}
                current_roomba_pos = roomba_pos[:]
            for zona, dust_list in dust_copy.items():
                for (x, y) in dust_list:
                    pygame.draw.circle(screen, (255, 255, 0), (x, y), 3)
            
            pygame.draw.circle(screen, (0, 255, 0),
                               (int(current_roomba_pos[0]), int(current_roomba_pos[1])), 8)
            text_roomba = font.render(f"Roomba: ({int(current_roomba_pos[0])}, {int(current_roomba_pos[1])})", True, (0, 255, 0))
            screen.blit(text_roomba, (WINDOW_WIDTH - 220, WINDOW_HEIGHT - 30))
            
            with lock:
                total_dust = sum(len(lst) for lst in dust_particles.values())
            info_lines = [
                f"Nivel: {level}",
                f"Polvo total: {total_dust}",
                f"Superficie total: {superficie_total} cm²",
                f"Tiempo estimado: {tiempo_limpeza:.2f} seg"
            ]
            info_x = 320
            info_y = 10
            for line in info_lines:
                info_surface = font.render(line, True, (255, 255, 255))
                screen.blit(info_surface, (info_x, info_y))
                info_y += info_surface.get_height() + 5
            
            pygame.display.flip()
            clock.tick(30)
            
            with lock:
                if current_dust_stop_event.is_set() and total_dust == 0:
                    level_complete = True
        
        for t in dust_threads:
            t.join()
        
        if running:
            level_msg = font.render(f"Nivel {level} completado!", True, (0, 255, 255))
            screen.blit(level_msg, 
                        (WINDOW_WIDTH // 2 - level_msg.get_width() // 2, WINDOW_HEIGHT // 2))
            pygame.display.flip()
            time.sleep(2)
        
        level += 1
    
    roomba_stop_event.set()
    roomba_thread.join()
    pygame.quit()

if __name__ == '__main__':
    main()
