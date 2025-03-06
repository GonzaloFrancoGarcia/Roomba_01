import concurrent.futures
import threading
import time
import random
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
        # Generar una mota en una posición aleatoria dentro del rectángulo de la zona
        x = random.randint(x0, x0 + width)
        y = random.randint(y0, y0 + height)
        with lock:
            dust_particles[zona].append((x, y))
            total = len(dust_particles[zona])
        print(f"{zona}: Generada mota en ({x}, {y}). Total: {total}")

def mover_roomba(roomba_pos, roomba_vel, dust_particles, lock, stop_event, window_size, zone_rects):
    """
    Actualiza continuamente la posición del Roomba y limpia las motas
    que se encuentren en su radio de acción, limitando su movimiento a la
    unión de las zonas definidas en 'zone_rects'. El Roomba puede pasar de
    una zona a otra si estas están juntas.
    """
    cleaning_radius = 10  # radio (píxeles) para limpiar una mota
    dt = 0.05  # intervalo en segundos
    last_print = time.time()
    window_width, window_height = window_size

    def allowed_position(x, y):
        """Retorna True si el punto (x, y) se encuentra dentro de alguna de las zonas."""
        for rect in zone_rects.values():
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return True
        return False

    while not stop_event.is_set():
        time.sleep(dt)
        with lock:
            # Intentar mover diagonalmente
            new_x = roomba_pos[0] + roomba_vel[0]
            new_y = roomba_pos[1] + roomba_vel[1]
            if allowed_position(new_x, new_y):
                roomba_pos[0] = new_x
                roomba_pos[1] = new_y
            else:
                # Si el movimiento diagonal no es permitido, se intenta moverse solo horizontalmente
                if allowed_position(roomba_pos[0] + roomba_vel[0], roomba_pos[1]):
                    roomba_pos[0] += roomba_vel[0]
                    # Rebota verticalmente
                    roomba_vel[1] = -roomba_vel[1]
                # O, si no, se intenta moverse solo verticalmente
                elif allowed_position(roomba_pos[0], roomba_pos[1] + roomba_vel[1]):
                    roomba_pos[1] += roomba_vel[1]
                    # Rebota horizontalmente
                    roomba_vel[0] = -roomba_vel[0]
                else:
                    # Si ninguna opción es válida, se rebotan ambos componentes
                    roomba_vel[0] = -roomba_vel[0]
                    roomba_vel[1] = -roomba_vel[1]

            # Procesar la limpieza de motas
            for zona in dust_particles:
                new_list = []
                for (x, y) in dust_particles[zona]:
                    if (x - roomba_pos[0])**2 + (y - roomba_pos[1])**2 >= cleaning_radius**2:
                        new_list.append((x, y))
                    else:
                        print(f"Roomba limpió mota en {zona} en ({x}, {y})")
                dust_particles[zona] = new_list

            # Mostrar información en terminal cada segundo
            if time.time() - last_print >= 1:
                total_dust = sum(len(lst) for lst in dust_particles.values())
                print(f"Roomba en {roomba_pos}; Polvo total restante: {total_dust}")
                last_print = time.time()

def main():
    # ===================== DIMENSIONES Y CÁLCULO DE ÁREAS =====================
    # Actualizamos las zonas según el plano: (ancho, alto) en cm.
    zonas = {
        'Zona 1': (500, 150),
        'Zona 2': (101, 220),
        'Zona 3': (309, 220),
        'Zona 4': (500, 150)
    }
    tasa_limpeza = 1000  # cm²/s (dato referencial)
    areas = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_zona = {
            executor.submit(calcular_area, largo, ancho): zona
            for zona, (largo, ancho) in zonas.items()
        }
        for future in concurrent.futures.as_completed(future_to_zona):
            zona = future_to_zona[future]
            try:
                area = future.result()
                areas[zona] = area
                print(f"{zona}: Área {area} cm²")
            except Exception as e:
                print(f"{zona} error: {e}")
    
    superficie_total = sum(areas.values())
    tiempo_limpeza = superficie_total / tasa_limpeza
    print(f"\nSuperficie Total a limpiar: {superficie_total} cm²")
    print(f"Tiempo estimado de limpieza (seg): {tiempo_limpeza:.2f}\n")
    
    # ===================== CONFIGURAR PYGAME Y COORDENADAS =====================
    # Dimensiones del cuarto en cm (según el plano)
    ROOM_WIDTH_CM = 600
    ROOM_HEIGHT_CM = 600
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 600
    SCALE = min(WINDOW_WIDTH / ROOM_WIDTH_CM, WINDOW_HEIGHT / ROOM_HEIGHT_CM)
    
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Simulación Roomba - Limpieza de Polvo (Plano)")
    clock = pygame.time.Clock()
    
    # Posiciones (top-left) de cada zona en cm, según el plano:
    zone_positions = {
        'Zona 1': (50, 31),
        'Zona 2': (50, 180),
        'Zona 3': (240, 180),
        'Zona 4': (50, 398)
    }
    
    zone_rects = {}
    for zona, (largo, alto) in zonas.items():
        pos = zone_positions[zona]
        zone_rects[zona] = (int(pos[0] * SCALE),
                            int(pos[1] * SCALE),
                            int(largo * SCALE),
                            int(alto * SCALE))
    
    # ===================== VARIABLES COMPARTIDAS =====================
    dust_particles = {zona: [] for zona in zonas}
    lock = threading.Lock()
    
    dust_stop_event = threading.Event()   # Detiene la generación de polvo tras cierto tiempo
    roomba_stop_event = threading.Event() # Se activa al cerrar la ventana
    
    # ===================== HILOS DE GENERACIÓN DE POLVO =====================
    dust_threads = []
    for zona, rect in zone_rects.items():
        t = threading.Thread(target=generar_dust,
                             args=(zona, dust_particles, lock, dust_stop_event, rect))
        t.start()
        dust_threads.append(t)
    
    # ===================== HILO DE MOVIMIENTO Y LIMPIEZA DEL ROOMBA =====================
    roomba_pos = [WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2]
    roomba_vel = [random.choice([-2, 2]), random.choice([-2, 2])]
    roomba_thread = threading.Thread(target=mover_roomba,
                                     args=(roomba_pos, roomba_vel, dust_particles, lock,
                                           roomba_stop_event, (WINDOW_WIDTH, WINDOW_HEIGHT), zone_rects))
    roomba_thread.start()
    
    simulation_duration = 10
    dust_gen_start = time.time()
    
    # ===================== BUCLE PRINCIPAL DE PYGAME =====================
    running = True
    font = pygame.font.SysFont(None, 24)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        if time.time() - dust_gen_start > simulation_duration and not dust_stop_event.is_set():
            dust_stop_event.set()
        
        screen.fill((30, 30, 30))
        
        # Dibujar cada zona
        for zona, rect in zone_rects.items():
            pygame.draw.rect(screen, (70, 70, 200), rect, 2)
            text_zone = font.render(zona, True, (200, 200, 200))
            screen.blit(text_zone, (rect[0] + 5, rect[1] + 5))
            with lock:
                dust_count = len(dust_particles[zona])
            text_dust = font.render(f"Polvo: {dust_count}", True, (200, 200, 200))
            screen.blit(text_dust, (rect[0] + 5, rect[1] + 30))
        
        # Dibujar motas de polvo
        with lock:
            dust_copy = {zona: dust_particles[zona][:] for zona in dust_particles}
            current_roomba_pos = roomba_pos[:]
        for zona, dust_list in dust_copy.items():
            for (x, y) in dust_list:
                pygame.draw.circle(screen, (255, 255, 0), (x, y), 3)
        
        # Dibujar la Roomba y mostrar su posición
        pygame.draw.circle(screen, (0, 255, 0),
                           (int(current_roomba_pos[0]), int(current_roomba_pos[1])), 8)
        text_roomba = font.render(
            f"Roomba: ({int(current_roomba_pos[0])}, {int(current_roomba_pos[1])})", True, (0, 255, 0))
        screen.blit(text_roomba, (WINDOW_WIDTH - 220, WINDOW_HEIGHT - 30))
        
        pygame.display.flip()
        clock.tick(30)
    
    # ===================== FINALIZACIÓN =====================
    roomba_stop_event.set()
    for t in dust_threads:
        t.join()
    roomba_thread.join()
    pygame.quit()

if __name__ == '__main__':
    main()
