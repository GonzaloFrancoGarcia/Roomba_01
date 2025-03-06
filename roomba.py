import concurrent.futures
import threading
import time
import random
import pygame

def calcular_area(largo, ancho):
    """Calcula el área de una zona multiplicando el largo por el ancho."""
    return largo * ancho

def generar_dust(zona, dust_particles, lock, stop_event, zona_rect):
    """
    Genera motas de polvo aleatorias dentro del rectángulo visual
    correspondiente a la zona.
    
    Cada iteración espera un intervalo aleatorio y luego agrega una coordenada
    (x, y) a la lista de partículas en esa zona.
    """
    x0, y0, width, height = zona_rect
    while not stop_event.is_set():
        # Espera un tiempo aleatorio entre 0.5 y 2.0 segundos
        time.sleep(random.uniform(0.5, 2.0))
        # Genera coordenadas aleatorias dentro de la zona
        x = random.randint(x0, x0 + width)
        y = random.randint(y0, y0 + height)
        with lock:
            dust_particles[zona].append((x, y))
        print(f"{zona}: Se generó una mota de polvo en ({x}, {y}), total: {len(dust_particles[zona])}")

def main():
    # -------------------- Cálculo de Áreas --------------------
    # Definición de las zonas: (largo, ancho) en cm.
    zonas = {
        'Zona 1': (500, 150),
        'Zona 2': (480, 101),
        'Zona 3': (309, 480),
        'Zona 4': (90, 220)
    }
    
    # Tasa de limpieza (por ejemplo, 1000 cm²/s)
    tasa_limpeza = 1000  # cm²/s
    
    areas = {}
    # Calcular las áreas de forma concurrente
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_zona = {
            executor.submit(calcular_area, largo, ancho): zona
            for zona, (largo, ancho) in zonas.items()
        }
        for future in concurrent.futures.as_completed(future_to_zona):
            zona = future_to_zona[future]
            try:
                area = future.result()
            except Exception as exc:
                print(f"{zona} generó una excepción: {exc}")
            else:
                areas[zona] = area
                print(f"{zona}: {area} cm²")
    
    # Superficie total y tiempo estimado de limpieza
    superficie_total = sum(areas.values())
    tiempo_limpeza = superficie_total / tasa_limpeza
    print(f"\nSuperficie total a limpiar: {superficie_total} cm²")
    print(f"Tiempo estimado de limpieza según el área: {tiempo_limpeza:.2f} segundos\n")
    
    # -------------------- Preparación de Pygame --------------------
    pygame.init()
    WINDOW_WIDTH, WINDOW_HEIGHT = 600, 400
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Simulación Roomba con Polvo")
    clock = pygame.time.Clock()
    
    # Factor de escala para transformar dimensiones (cm) en píxeles
    SCALE = 0.3
    
    # Posiciones (top-left) para cada zona en la ventana (definidas arbitrariamente)
    zone_positions = {
        'Zona 1': (50, 50),
        'Zona 2': (300, 50),
        'Zona 3': (50, 200),
        'Zona 4': (300, 200)
    }
    
    # Calcular el rectángulo visual para cada zona: (x, y, ancho, alto) en píxeles
    zone_rects = {}
    for zona, (largo, ancho) in zonas.items():
        pos = zone_positions[zona]
        width = int(largo * SCALE)
        height = int(ancho * SCALE)
        zone_rects[zona] = (pos[0], pos[1], width, height)
    
    # -------------------- Configuración de la Simulación de Polvo --------------------
    # Diccionario para almacenar posiciones (x,y) de las motas generadas por zona
    dust_particles = {zona: [] for zona in zonas}
    lock = threading.Lock()
    stop_event = threading.Event()
    
    # Iniciar un hilo para cada zona que genere polvo
    threads = []
    for zona, rect in zone_rects.items():
        thread = threading.Thread(target=generar_dust,
                                  args=(zona, dust_particles, lock, stop_event, rect))
        thread.start()
        threads.append(thread)
    
    # Duración de la simulación de generación de polvo (segundos)
    simulation_duration = 10
    sim_start_time = time.time()
    
    # -------------------- Bucle Principal de Pygame --------------------
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Una vez transcurrido el tiempo de simulación, detenemos la generación de polvo
        if time.time() - sim_start_time > simulation_duration:
            stop_event.set()
        
        # Fondo oscuro
        screen.fill((30, 30, 30))
        
        # Fuente para mostrar textos (nombre de zona y cantidad de polvo)
        font = pygame.font.SysFont(None, 24)
        
        # Dibujar cada zona y mostrar su nombre y la cantidad de motas
        for zona, rect in zone_rects.items():
            # Dibujar el contorno del rectángulo (zona)
            pygame.draw.rect(screen, (70, 70, 200), rect, 2)
            # Escribir el nombre de la zona
            text_zone = font.render(zona, True, (200, 200, 200))
            screen.blit(text_zone, (rect[0] + 5, rect[1] + 5))
            # Con el lock, obtener el número de partículas en la zona
            with lock:
                dust_count = len(dust_particles[zona])
            text_dust = font.render(f"Polvo: {dust_count}", True, (200, 200, 200))
            screen.blit(text_dust, (rect[0] + 5, rect[1] + 30))
        
        # Dibujar las motas de polvo: se representan como círculos amarillos
        with lock:
            # Se crea una copia de seguridad para evitar conflictos con hilos
            dust_copy = {zona: dust_particles[zona][:] for zona in dust_particles}
        for zona, dust_list in dust_copy.items():
            for (x, y) in dust_list:
                pygame.draw.circle(screen, (255, 255, 0), (x, y), 3)
        
        # Si la simulación de polvo ya terminó, mostrar un mensaje en pantalla
        if time.time() - sim_start_time > simulation_duration:
            font_big = pygame.font.SysFont(None, 36)
            text_fin = font_big.render("Simulación finalizada", True, (255, 100, 100))
            screen.blit(text_fin, (WINDOW_WIDTH // 2 - text_fin.get_width() // 2,
                                   WINDOW_HEIGHT - 40))
        
        pygame.display.flip()
        clock.tick(30)  # 30 FPS
    
    # -------------------- Finalización --------------------
    # Aseguramos que todos los hilos de polvo han terminado
    for thread in threads:
        thread.join()
    
    pygame.quit()

if __name__ == '__main__':
    main()
