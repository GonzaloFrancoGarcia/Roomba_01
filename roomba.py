import pygame
import concurrent.futures
import random

# Inicializar pygame
pygame.init()

# Dimensiones de la pantalla
WIDTH, HEIGHT = 600, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulación de Roomba")

# Colores
WHITE = (255, 255, 255)
BLUE = (0, 100, 255)
GREEN = (0, 255, 100)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

# Definición de zonas de limpieza
zonas = {
    'Zona 1': (50, 50, 200, 100),  # (x, y, ancho, alto)
    'Zona 2': (300, 50, 180, 100),
    'Zona 3': (100, 200, 250, 150),
    'Zona 4': (400, 300, 90, 220)
}

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

# Clase Roomba
class Roomba:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 15
        self.color = RED
        self.speed = 2
        self.direction = random.choice([(self.speed, 0), (-self.speed, 0), (0, self.speed), (0, -self.speed)])

    def move(self):
        self.x += self.direction[0]
        self.y += self.direction[1]
        
        if self.x < 0 or self.x > WIDTH:
            self.direction = (-self.direction[0], self.direction[1])
        if self.y < 0 or self.y > HEIGHT:
            self.direction = (self.direction[0], -self.direction[1])
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)

# Crear Roomba
roomba = Roomba(WIDTH // 2, HEIGHT // 2)

# Bucle principal
running = True
clock = pygame.time.Clock()
while running:
    screen.fill(WHITE)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Dibujar zonas
    for zona, (x, y, w, h) in zonas.items():
        pygame.draw.rect(screen, BLUE, (x, y, w, h))
    
    # Mover y dibujar la Roomba
    roomba.move()
    roomba.draw(screen)
    
    # Actualizar pantalla
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
