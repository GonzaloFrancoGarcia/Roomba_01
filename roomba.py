import pygame
import concurrent.futures
import random

# Inicializar pygame
pygame.init()

# Dimensiones de la pantalla
WIDTH, HEIGHT = 600, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bebé Roomba y Padre Roomba")

# Definición de zonas de limpieza
zonas = {
    'Zona 1': (50, 50, 200, 100),  # (x, y, ancho, alto)
    'Zona 2': (300, 50, 180, 100),
    'Zona 3': (100, 200, 250, 150),
    'Zona 4': (400, 300, 90, 220)
}

# Crear una superficie para almacenar las huellas del bebé
huellas_superficie = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
huellas_superficie.fill((0, 0, 0, 0))  # Transparente

# Crear una superficie para almacenar las áreas limpiadas
zona_superficie = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
zona_superficie.fill((0, 0, 0, 0))  # Transparente

# Tasa de limpieza (1000 cm²/s)
tasa_limpeza = 1000  # cm²/s

# Función para calcular el área
def calcular_area(largo, ancho):
    return largo * ancho

# Calcular áreas de las zonas
areas = {}
with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_zona = {executor.submit(calcular_area, w, h): zona for zona, (x, y, w, h) in zonas.items()}
    for future in concurrent.futures.as_completed(future_to_zona):
        zona = future_to_zona[future]
        areas[zona] = future.result()

# Superficie total y tiempo estimado
superficie_total = sum(areas.values())
tiempo_limpeza = superficie_total / tasa_limpeza

time_limit = 30  # Tiempo límite antes de que llegue la madre
time_remaining = time_limit

# Clase Roomba
class Roomba:
    def __init__(self, x, y, color, leave_trail=False):
        self.x = x
        self.y = y
        self.radius = 15
        self.speed = 3
        self.color = color
        self.leave_trail = leave_trail
        self.direction = [random.choice([-self.speed, self.speed]), random.choice([-self.speed, self.speed])]
        self.change_direction_timer = 0
    
    def move(self):
        self.x += self.direction[0]
        self.y += self.direction[1]
        
        # Rebote en los bordes de la pantalla
        if self.x - self.radius < 0 or self.x + self.radius > WIDTH:
            self.direction[0] = -self.direction[0]
        if self.y - self.radius < 0 or self.y + self.radius > HEIGHT:
            self.direction[1] = -self.direction[1]
        
        # Cambio de dirección aleatorio cada cierto tiempo
        self.change_direction_timer += 1
        if self.change_direction_timer > 100:
            self.direction = [random.choice([-self.speed, 0, self.speed]), random.choice([-self.speed, 0, self.speed])]
            self.change_direction_timer = 0
        
        # Dejar huellas si es el bebé
        if self.leave_trail:
            pygame.draw.circle(huellas_superficie, (200, 100, 0, 150), (self.x, self.y), self.radius // 2)
        
        # Limpiar huellas si es el padre
        if not self.leave_trail:
            pygame.draw.circle(zona_superficie, (0, 0, 0, 0), (self.x, self.y), self.radius // 2)
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)

# Crear Roombas
bebe_roomba = Roomba(WIDTH // 4, HEIGHT // 4, (255, 100, 100), leave_trail=True)
padre_roomba = Roomba(WIDTH // 2, HEIGHT // 2, (100, 100, 255), leave_trail=False)

# Bucle principal
running = True
clock = pygame.time.Clock()
while running:
    screen.fill((200, 200, 200))  # Fondo gris
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Dibujar zonas
    for zona, (x, y, w, h) in zonas.items():
        pygame.draw.rect(screen, (0, 100, 255, 150), (x, y, w, h))  # Semitransparente
    
    # Dibujar huellas del bebé
    screen.blit(huellas_superficie, (0, 0))
    
    # Mover y dibujar las Roombas
    bebe_roomba.move()
    bebe_roomba.draw(screen)
    
    padre_roomba.move()
    padre_roomba.draw(screen)
    
    # Limpiar huellas al pasar el padre
    screen.blit(zona_superficie, (0, 0))
    
    # Actualizar el tiempo restante
    time_remaining -= 1 / 60
    font = pygame.font.Font(None, 36)
    timer_text = font.render(f"Tiempo: {max(0, int(time_remaining))}s", True, (0, 0, 0))
    screen.blit(timer_text, (10, 10))
    
    # Condición de fin de juego
    if time_remaining <= 0:
        running = False
    
    # Actualizar pantalla
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
