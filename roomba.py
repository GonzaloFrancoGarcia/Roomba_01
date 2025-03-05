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

# Definición de las zonas con sus dimensiones (x, y, ancho, alto)
zones = {
    'Zona 1': (50, 50, 200, 80),   # Arriba izq
    'Zona 2': (250, 50, 200, 120),  # Arriba medio
    'Zona 3': (450, 50, 300, 480),  # Derecha
    'Zona 4': (50, 127, 120, 350),  # Abajo izq
    'Zona 5': (170, 250, 280, 180)  # Abajo medio
}

# Conexiones entre zonas (pueden ser útiles para otros propósitos)
zone_connections = {
    'Zona 1': ['Zona 2', 'Zona 4', 'Zona 5'],
    'Zona 2': ['Zona 1', 'Zona 3', 'Zona 5'],
    'Zona 3': ['Zona 2', 'Zona 5'],
    'Zona 4': ['Zona 1', 'Zona 5'],
    'Zona 5': ['Zona 1', 'Zona 2', 'Zona 3', 'Zona 4']
}

def is_inside_zone(x, y):
    for _, (zx, zy, zw, zh) in zones.items():
        if zx <= x <= zx + zw and zy <= y <= zy + zh:
            return True
    return False

def get_random_position():
    while True:
        zone = random.choice(list(zones.values()))
        x = random.randint(zone[0], zone[0] + zone[2] - 10)
        y = random.randint(zone[1], zone[1] + zone[3] - 10)
        if is_inside_zone(x, y):
            return x, y

# Algoritmo A* para encontrar la mejor ruta (con tolerancia ya implementada)
def astar(start, goal):
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    tolerance = 10  # Umbral para considerar que se ha alcanzado el objetivo
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    
    while open_set:
        _, current = heapq.heappop(open_set)
        
        # Si estamos lo suficientemente cerca del objetivo
        if heuristic(current, goal) < tolerance:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path = path[::-1]
            path.append(goal)  # Aseguramos que el camino finaliza en el objetivo
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

# Creación de los personajes
class Roomba:
    def __init__(self, color, speed):
        self.x, self.y = get_random_position()
        self.color = color
        self.speed = speed
        self.path = []
    
    def move_towards(self, target_x, target_y):
        # Aplicamos aleatoriedad solo para el ratón (color RED)
        if self.color == RED:
            # Si no existe ya un camino calculado, lo calculamos con un objetivo modificado
            if not self.path:
                # Añadimos un offset aleatorio al objetivo para que no sea tan directo
                offset_x = random.randint(-30, 30)
                offset_y = random.randint(-30, 30)
                new_target = (target_x + offset_x, target_y + offset_y)
                # Verificamos que el nuevo objetivo esté dentro de alguna zona; si no, usamos el objetivo original.
                if not is_inside_zone(new_target[0], new_target[1]):
                    new_target = (target_x, target_y)
                self.path = astar((self.x, self.y), new_target)
            
            # Con una probabilidad del 30% se realiza un movimiento aleatorio (desviación)
            if self.path and random.random() < 0.3:
                neighbors = [(10, 0), (-10, 0), (0, 10), (0, -10)]
                random.shuffle(neighbors)
                for dx, dy in neighbors:
                    nx, ny = self.x + dx, self.y + dy
                    if is_inside_zone(nx, ny):
                        self.x, self.y = nx, ny
                        self.path = []  # Se reinicia la ruta para recalcular en el siguiente paso
                        return
            if self.path:
                self.x, self.y = self.path.pop(0)
        else:
            # Para otros personajes (por ejemplo, si quisiéramos modificar el comportamiento) 
            if not self.path:
                self.path = astar((self.x, self.y), (target_x, target_y))
            if self.path:
                self.x, self.y = self.path.pop(0)
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), 10)

# Instanciar personajes
mouse = Roomba(RED, 3)
cat = Roomba(BLUE, 2)
cheeses = [get_random_position() for _ in range(5)]

def calculate_cleaning_time():
    rate = 3
    with concurrent.futures.ThreadPoolExecutor() as executor:
        areas = list(executor.map(lambda z: z[2] * z[3], zones.values()))
    return sum(areas) / rate

time_to_clean = calculate_cleaning_time()

def move_cat(keys):
    if keys[pygame.K_LEFT] and is_inside_zone(cat.x - cat.speed, cat.y):
        cat.x -= cat.speed
    if keys[pygame.K_RIGHT] and is_inside_zone(cat.x + cat.speed, cat.y):
        cat.x += cat.speed
    if keys[pygame.K_UP] and is_inside_zone(cat.x, cat.y - cat.speed):
        cat.y -= cat.speed
    if keys[pygame.K_DOWN] and is_inside_zone(cat.x, cat.y + cat.speed):
        cat.y += cat.speed

running = True
clock = pygame.time.Clock()

while running:
    screen.fill(WHITE)
    
    # Dibujar zonas en verde
    for _, (x, y, w, h) in zones.items():
        pygame.draw.rect(screen, GREEN, (x, y, w, h))
    
    # Dibujar quesos
    for cheese in cheeses:
        pygame.draw.circle(screen, (255, 255, 0), cheese, 5)
    
    # Movimiento automático del ratón: se dirige al primer queso de la lista
    if cheeses:
        target = cheeses[0]
        mouse.move_towards(*target)
        if abs(mouse.x - target[0]) < 5 and abs(mouse.y - target[1]) < 5:
            cheeses.pop(0)
    
    # Si el gato atrapa al ratón
    if abs(mouse.x - cat.x) < 10 and abs(mouse.y - cat.y) < 10:
        print("El gato atrapó al ratón. Fin del juego.")
        running = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    keys = pygame.key.get_pressed()
    move_cat(keys)
    
    mouse.draw(screen)
    cat.draw(screen)
    
    if not cheeses:
        print("El ratón ha recogido todos los quesos. Fin del juego.")
        running = False

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
