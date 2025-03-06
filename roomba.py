import pygame
import random
import heapq
import concurrent.futures

# Inicializar pygame
pygame.init()

# Configuración de la pantalla
WIDTH, HEIGHT = 600, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Roomba Cat & Mouse")

# Colores
WHITE = (255, 255, 255)
RED   = (255, 0, 0)
BLUE  = (0, 0, 255)
GREEN = (0, 255, 0)

# --- Configuración de las zonas ---
# Valores originales (ancho, alto):
# 'Zona 1': (500,150), 'Zona 2': (101,480), 'Zona 3': (309,480), 'Zona 4': (90,220)

# Organización en dos filas:
# Fila superior: zona 2 y zona 3, ambas con altura 480.
# Total ancho fila 1 = 101 + 309 = 410, se centra en 600 con margen X = (600-410)//2 = 95.
zona2 = (50, 180, 101, 480)          # (x, y, ancho, alto)
zona3 = (240, 180, 309, 480)      # (196, 0, 309, 480)

# Fila inferior: zona 1 y zona 4.
# Los tamaños son: Zona 1: 500×150 y Zona 4: 90×220.
# La altura de fila inferior será la máxima de ambas: max(150,220) = 220.
# Ancho total fila 2 = 500 + 90 = 590, margen X = (600-590)//2 = 5.
zona1 = (50, 30, 500, 150)           # (x, y, ancho, alto)
zona4 = (151, 440, 90, 220)        # (505,480,90,220)

zones = {
    'Zona 1': zona1,
    'Zona 2': zona2,
    'Zona 3': zona3,
    'Zona 4': zona4
}
# --- Fin de configuración de zonas ---

def is_inside_zone(x, y):
    """Verifica si la posición (x, y) está contenida en alguna de las zonas."""
    for _, (zx, zy, zw, zh) in zones.items():
        if zx <= x <= zx + zw and zy <= y <= zy + zh:
            return True
    return False

def get_random_position():
    """
    Devuelve una posición aleatoria, alineada a una cuadrícula de 10 píxeles,
    que se encuentre dentro de alguna de las zonas.
    """
    while True:
        zone = random.choice(list(zones.values()))
        zx, zy, zw, zh = zone
        min_x = zx // 10
        max_x = (zx + zw - 10) // 10
        min_y = zy // 10
        max_y = (zy + zh - 10) // 10
        x = random.randint(min_x, max_x) * 10
        y = random.randint(min_y, max_y) * 10
        if is_inside_zone(x, y):
            return x, y

def manhattan_distance(a, b):
    """Calcula la distancia Manhattan entre dos puntos."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# A* se mantiene para referencia, aunque en este ejemplo la mosca se mueve de forma aleatoria.
def astar(start, goal):
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    tolerance = 10  # Umbral en píxeles
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    while open_set:
        _, current = heapq.heappop(open_set)
        if heuristic(current, goal) < tolerance:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path = path[::-1]
            path.append(goal)
            return path
        for dx, dy in [(10, 0), (-10, 0), (0, 10), (0, -10)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if not is_inside_zone(*neighbor):
                continue
            tentative_g_score = g_score[current] + 10
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return []

# Clase para los personajes.
# Se añade un método get_rect para obtener el rectángulo de colisión basado en el sprite,
# inflándolo para que la detección sea más amplia y evite la sensación de "traspaso".
class Roomba:
    def __init__(self, color, speed, sprite=None):
        self.x, self.y = get_random_position()
        self.color = color
        self.speed = speed
        self.sprite = sprite
        if self.color == RED:
            self.visited = set()
        else:
            self.visited = None

    def get_rect(self):
        """Devuelve un pygame.Rect basado en el sprite o un rectángulo por defecto, inflado para colisiones amplias."""
        if self.sprite:
            rect = self.sprite.get_rect(topleft=(self.x, self.y))
            return rect.inflate(20, 20)  # Incrementa la caja 20 píxeles en ancho y alto
        else:
            return pygame.Rect(self.x - 10, self.y - 10, 20, 20).inflate(20, 20)

    def draw(self, screen):
        if self.sprite:
            screen.blit(self.sprite, (self.x, self.y))
        else:
            pygame.draw.circle(screen, self.color, (self.x, self.y), 10)

    def move_randomly_towards(self, target):
        """
        Movimiento aleatorio que evita repetir celdas visitadas. Si queda sin opciones,
        reinicia el historial para "desbuguearse".
        """
        current = (self.x, self.y)
        possible_moves = [(10, 0), (-10, 0), (0, 10), (0, -10)]
        neighbors = []
        for dx, dy in possible_moves:
            candidate = (self.x + dx, self.y + dy)
            if is_inside_zone(*candidate):
                neighbors.append(candidate)
        if not neighbors:
            return
        non_visited = [nb for nb in neighbors if nb not in self.visited]
        if not non_visited:
            self.visited.clear()
            non_visited = neighbors
        if random.random() < 0.7:
            chosen = min(non_visited, key=lambda nb: manhattan_distance(nb, target))
        else:
            chosen = random.choice(non_visited)
        self.x, self.y = chosen
        self.visited.add(chosen)

# --- Cargar los sprites ---
# Usamos los nombres y tamaños indicados.
fly_sprite = pygame.image.load('fly.gif').convert_alpha()
fly_sprite = pygame.transform.scale(fly_sprite, (20, 20))

chancla_sprite = pygame.image.load('chancla.jpg').convert_alpha()
chancla_sprite = pygame.transform.scale(chancla_sprite, (30, 30))

sleeping_sprite = pygame.image.load('minarro.jpg').convert_alpha()
sleeping_sprite = pygame.transform.scale(sleeping_sprite, (30, 30))
# --- Fin de carga de sprites ---

# Instanciar personajes:
# La mosca (personaje automático, color RED) se muestra con fly_sprite.
fly = Roomba(RED, 3, sprite=fly_sprite)
# El jugador se muestra con el sprite de chancla.
cat = Roomba(BLUE, 2, sprite=chancla_sprite)

# Generar posiciones para "la gente durmiendo" (antes quesos)
sleeping_positions = [get_random_position() for _ in range(5)]

def calculate_cleaning_time():
    rate = 3  # Valor arbitrario en cm²/segundo
    with concurrent.futures.ThreadPoolExecutor() as executor:
        areas = list(executor.map(lambda z: z[2] * z[3], zones.values()))
    return sum(areas) / rate

time_to_clean = calculate_cleaning_time()

def move_cat(keys):
    # Movimiento del jugador (sprite de chancla) controlado por teclas
    if keys[pygame.K_LEFT] and is_inside_zone(cat.x - cat.speed, cat.y):
        cat.x -= cat.speed
    if keys[pygame.K_RIGHT] and is_inside_zone(cat.x + cat.speed, cat.y):
        cat.x += cat.speed
    if keys[pygame.K_UP] and is_inside_zone(cat.x, cat.y - cat.speed):
        cat.y -= cat.speed
    if keys[pygame.K_DOWN] and is_inside_zone(cat.x, cat.y + cat.speed):
        cat.y += cat.speed

# --- Bucle principal del juego ---
running = True
clock = pygame.time.Clock()

while running:
    screen.fill(WHITE)
    
    # Dibujar las zonas (rectángulos) en verde
    for _, (x, y, w, h) in zones.items():
        pygame.draw.rect(screen, GREEN, (x, y, w, h))
    
    # Dibujar "la gente durmiendo" usando el sprite sleeping_sprite.
    # Se infla el rectángulo de cada objeto para ampliar la detección de colisiones.
    for pos in sleeping_positions:
        target_rect = sleeping_sprite.get_rect(topleft=pos).inflate(20, 20)
        screen.blit(sleeping_sprite, pos)
    
    # Movimiento automático de la mosca hacia el primer "dormido"
    if sleeping_positions:
        target = sleeping_positions[0]
        fly.move_randomly_towards(target)
        target_rect = sleeping_sprite.get_rect(topleft=target).inflate(20, 20)
        if fly.get_rect().colliderect(target_rect):
            sleeping_positions.pop(0)
    
    # Comprobar colisión entre el jugador y la mosca usando sus cajas (rectángulos inflados)
    if fly.get_rect().colliderect(cat.get_rect()):
        print("El jugador atrapó a la mosca. Fin del juego.")
        running = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    keys = pygame.key.get_pressed()
    move_cat(keys)
    
    # Dibujar los personajes
    fly.draw(screen)
    cat.draw(screen)
    
    if not sleeping_positions:
        print("La mosca ha recogido a toda la gente durmiendo. Fin del juego.")
        running = False

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
