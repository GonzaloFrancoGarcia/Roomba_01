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

def mover_roomba(roomba_pos, roomba_vel, dust_particles, lock, stop_event, window_size):
    """
    Actualiza continuamente la posición del Roomba y limpia las motas
    que se encuentren en su radio de acción.
    """
    cleaning_radius = 10  # radio (píxeles) para limpiar una mota
    dt = 0.05  # intervalo en segundos
    last_print = time.time()
    window_width, window_height = window_size

    while not stop_event.is_set():
        time.sleep(dt)
        with lock:
            # Actualizar posición
            roomba_pos[0] += roomba_vel[0]
            roomba_pos[1] += roomba_vel[1]
            # Rebote en los bordes de la ventana
            if roomba_pos[0] <= 0 or roomba_pos[0] >= window_width:
                roomba_vel[0] = -roomba_vel[0]
            if roomba_pos[1] <= 0 or roomba_pos[1] >= window_height:
                roomba_vel[1] = -roomba_vel[1]
            
            # Revisar cada zona y eliminar motas en el radio de limpieza
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
    # Actualizamos las zonas según el plano:
    # (ancho, alto) en cm.
    zonas = {
        'Zona 1': (500, 150),
        'Zona 2': (101, 220),
        'Zona 3': (309, 220),
        'Zona 4': (500, 150)
    }
    # Usamos estas dimensiones para calcular áreas
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
    # Definimos el tamaño de la ventana de forma que se vea todo el cuarto.
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 600
    # Calculamos la escala para convertir de cm a píxeles
    SCALE = min(WINDOW_WIDTH / ROOM_WIDTH_CM, WINDOW_HEIGHT / ROOM_HEIGHT_CM)
    
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Simulación Roomba - Limpieza de Polvo (Plano)")
    clock = pygame.time.Clock()
    
    # Posiciones (top-left) de cada zona en coordenadas del cuarto (en cm), según el plano:
    zone_positions = {
        'Zona 1': (50, 31),     # Centrada en la parte superior: margen de 30 cm a izquierda.
        'Zona 2': (50, 180),    # En la parte inferior de ZONA 1, al borde izquierdo.
        'Zona 3': (240, 180),  # Justo a la derecha de ZONA 2.
        'Zona 4': (50, 397)    # En la parte inferior, centrada (margen de 30 cm).
    }
    
    # Calcular el rectángulo visual para cada zona (en píxeles)
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
    
    # Eventos para detener hilos
    dust_stop_event = threading.Event()       # Detiene la generación de polvo luego de cierto tiempo
    roomba_stop_event = threading.Event()     # Se activa al cerrar la ventana
    
    # ===================== HILOS DE GENERACIÓN DE POLVO =====================
    dust_threads = []
    for zona, rect in zone_rects.items():
        t = threading.Thread(target=generar_dust,
                             args=(zona, dust_particles, lock, dust_stop_event, rect))
        t.start()
        dust_threads.append(t)
    
    # ===================== HILO DE MOVIMIENTO Y LIMPIEZA DEL ROOMBA =====================
    # Iniciar Roomba en el centro de la ventana (en píxeles)
    roomba_pos = [WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2]
    roomba_vel = [random.choice([-2, 2]), random.choice([-2, 2])]
    roomba_thread = threading.Thread(target=mover_roomba,
                                     args=(roomba_pos, roomba_vel, dust_particles, lock,
                                           roomba_stop_event, (WINDOW_WIDTH, WINDOW_HEIGHT)))
    roomba_thread.start()
    
    # La generación de polvo se realizará durante 10 segundos.
    simulation_duration = 10
    dust_gen_start = time.time()
    
    # ===================== BUCLE PRINCIPAL DE PYGAME =====================
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Detener la creación de polvo tras simulation_duration
        if time.time() - dust_gen_start > simulation_duration and not dust_stop_event.is_set():
            dust_stop_event.set()
        
        screen.fill((30, 30, 30))  # Fondo oscuro
        font = pygame.font.SysFont(None, 24)
        
        # Dibujar cada zona con su nombre y contador de motas
        for zona, rect in zone_rects.items():
            pygame.draw.rect(screen, (70, 70, 200), rect, 2)
            text_zone = font.render(zona, True, (200, 200, 200))
            screen.blit(text_zone, (rect[0] + 5, rect[1] + 5))
            with lock:
                dust_count = len(dust_particles[zona])
            text_dust = font.render(f"Polvo: {dust_count}", True, (200, 200, 200))
            screen.blit(text_dust, (rect[0] + 5, rect[1] + 30))
        
        # Dibujar las motas de polvo (círculos amarillos)
        with lock:
            dust_copy = {zona: dust_particles[zona][:] for zona in dust_particles}
            current_roomba_pos = roomba_pos[:]
        for zona, dust_list in dust_copy.items():
            for (x, y) in dust_list:
                pygame.draw.circle(screen, (255, 255, 0), (x, y), 3)
        
        # Dibujar la Roomba (círculo verde) y mostrar su posición
        pygame.draw.circle(screen, (0, 255, 0), (int(current_roomba_pos[0]), int(current_roomba_pos[1])), 8)
        text_roomba = font.render(f"Roomba: ({int(current_roomba_pos[0])}, {int(current_roomba_pos[1])})", True, (0, 255, 0))
        screen.blit(text_roomba, (WINDOW_WIDTH - 220, WINDOW_HEIGHT - 30))
        
        pygame.display.flip()
        clock.tick(30)  # 30 FPS
    
    # ===================== FINALIZACIÓN =====================
    roomba_stop_event.set()
    for t in dust_threads:
        t.join()
    roomba_thread.join()
    pygame.quit()

if __name__ == '__main__':
    main()
