import pygame
import random
import heapq
import concurrent.futures

# Inicializar pygame
pygame.init()

# Configuración de la pantalla
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Roomba Cat & Mouse")

# Colores
WHITE = (255, 255, 255)
RED   = (255, 0, 0)
BLUE  = (0, 0, 255)
GREEN = (0, 255, 0)

# Definición de las zonas (x, y, ancho, alto)
zones = {
    'Zona 1': (50, 50, 200, 80),    # Arriba izquierda
    'Zona 2': (250, 50, 200, 120),   # Arriba medio
    'Zona 3': (450, 50, 300, 480),   # Derecha
    'Zona 4': (50, 127, 120, 350),   # Abajo izquierda
    'Zona 5': (170, 250, 280, 180)   # Abajo medio
}

# (Opcional) Conexiones entre zonas para otros propósitos
zone_connections = {
    'Zona 1': ['Zona 2', 'Zona 4', 'Zona 5'],
    'Zona 2': ['Zona 1', 'Zona 3', 'Zona 5'],
    'Zona 3': ['Zona 2', 'Zona 5'],
    'Zona 4': ['Zona 1', 'Zona 5'],
    'Zona 5': ['Zona 1', 'Zona 2', 'Zona 3', 'Zona 4']
}

def is_inside_zone(x, y):
    """Verifica si la posición (x, y) está dentro de alguna de las zonas."""
    for _, (zx, zy, zw, zh) in zones.items():
        if zx <= x <= zx + zw and zy <= y <= zy + zh:
            return True
    return False

def get_random_position():
    """
    Devuelve una posición aleatoria, alineada a una cuadrícula de 10 píxeles,
    dentro de alguna de las zonas.
    """
    while True:
        zone = random.choice(list(zones.values()))
        min_x = zone[0] // 10
        max_x = (zone[0] + zone[2] - 10) // 10
        min_y = zone[1] // 10
        max_y = (zone[1] + zone[3] - 10) // 10
        x = random.randint(min_x, max_x) * 10
        y = random.randint(min_y, max_y) * 10
        if is_inside_zone(x, y):
            return x, y

def manhattan_distance(a, b):
    """Calcula la distancia Manhattan entre dos puntos."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# A* (se conserva para referencia; en este ejemplo la mosca se mueve de forma aleatoria)
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

# Clase para los personajes. Permite asignar un sprite opcional.
class Roomba:
    def __init__(self, color, speed, sprite=None):
        self.x, self.y = get_random_position()
        self.color = color
        self.speed = speed
        self.sprite = sprite
        # Si el personaje es el automático (mosca: RED), se utiliza un historial
        # para evitar pisar las mismas celdas repetidamente.
        if self.color == RED:
            self.visited = set()
        else:
            self.visited = None

    def draw(self, screen):
        if self.sprite:
            screen.blit(self.sprite, (self.x, self.y))
        else:
            pygame.draw.circle(screen, self.color, (self.x, self.y), 10)

    def move_randomly_towards(self, target):
        """
        Movimiento aleatorio evitando pisar repetidamente las mismas celdas.
        Si se queda sin opciones, se reinicia su historial para "desbuguearse".
        """
        current = (self.x, self.y)
        possible_moves = [(10, 0), (-10, 0), (0, 10), (0, -10)]
        neighbors = []
        for dx, dy in possible_moves:
            candidate = (self.x + dx, self.y + dy)
            if is_inside_zone(*candidate):
                neighbors.append(candidate)
        if not neighbors:
            return  # No hay movimiento posible
        non_visited = [nb for nb in neighbors if nb not in self.visited]
        if not non_visited:
            self.visited.clear()  # Permite pisar celdas si está atascado
            non_visited = neighbors
        # Con 70% de probabilidad se selecciona el vecino que minimiza la distancia al objetivo,
        # y con 30% se elige uno aleatoriamente.
        if random.random() < 0.7:
            chosen = min(non_visited, key=lambda nb: manhattan_distance(nb, target))
        else:
            chosen = random.choice(non_visited)
        self.x, self.y = chosen
        self.visited.add(chosen)

# Cargar el sprite de la mosca y escalarlo
fly_sprite = pygame.image.load('fly.gif').convert_alpha()
fly_sprite = pygame.transform.scale(fly_sprite, (20, 20))

# Cargar el sprite de la chancla para el jugador y escalarlo
chancla_sprite = pygame.image.load('chancla.jpg').convert_alpha()
chancla_sprite = pygame.transform.scale(chancla_sprite, (30, 30))

# Cargar el sprite de gente durmiendo (sustituyendo a los quesos) y escalarlo
sleeping_sprite = pygame.image.load('sleeping.png').convert_alpha()
sleeping_sprite = pygame.transform.scale(sleeping_sprite, (30, 30))

# Instanciar personajes:
# La mosca se mueve automáticamente y se muestra con su sprite.
fly = Roomba(RED, 3, sprite=fly_sprite)
# El jugador (controlado por el teclado) se muestra con el sprite de chancla.
cat = Roomba(BLUE, 2, sprite=chancla_sprite)

# Generar posiciones para la "gente durmiendo" (sustituyen a los quesos)
sleeping_positions = [get_random_position() for _ in range(5)]

def calculate_cleaning_time():
    rate = 3  # Valor arbitrario, en cm²/segundo
    with concurrent.futures.ThreadPoolExecutor() as executor:
        areas = list(executor.map(lambda z: z[2] * z[3], zones.values()))
    return sum(areas) / rate

time_to_clean = calculate_cleaning_time()

def move_cat(keys):
    # Movimiento del jugador (sprite de chancla) mediante el teclado
    if keys[pygame.K_LEFT] and is_inside_zone(cat.x - cat.speed, cat.y):
        cat.x -= cat.speed
    if keys[pygame.K_RIGHT] and is_inside_zone(cat.x + cat.speed, cat.y):
        cat.x += cat.speed
    if keys[pygame.K_UP] and is_inside_zone(cat.x, cat.y - cat.speed):
        cat.y -= cat.speed
    if keys[pygame.K_DOWN] and is_inside_zone(cat.x, cat.y + cat.speed):
        cat.y += cat.speed

# Bucle principal del juego
running = True
clock = pygame.time.Clock()

while running:
    screen.fill(WHITE)
    
    # Dibujar las zonas enteramente en verde
    for _, (x, y, w, h) in zones.items():
        pygame.draw.rect(screen, GREEN, (x, y, w, h))
    
    # Dibujar "gente durmiendo" usando el sprite sleeping_sprite
    for pos in sleeping_positions:
        screen.blit(sleeping_sprite, pos)
    
    # Movimiento automático de la mosca hacia el primer "dormido" en la lista
    if sleeping_positions:
        target = sleeping_positions[0]
        fly.move_randomly_towards(target)
        # Si la mosca está cerca del objetivo, se "recoge" (se elimina) la persona durmiendo.
        if abs(fly.x - target[0]) < 10 and abs(fly.y - target[1]) < 10:
            sleeping_positions.pop(0)
    
    # Comprobación de colisión: si el jugador (chancla) atrapa a la mosca
    if abs(fly.x - cat.x) < 10 and abs(fly.y - cat.y) < 10:
        print("El jugador atrapó a la mosca. Fin del juego.")
        running = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    keys = pygame.key.get_pressed()
    move_cat(keys)
    
    # Dibujar personajes
    fly.draw(screen)
    cat.draw(screen)
    
    if not sleeping_positions:
        print("La mosca ha recogido a toda la gente durmiendo. Fin del juego.")
        running = False

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
