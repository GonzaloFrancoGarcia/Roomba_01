import pygame
import random
import concurrent.futures

# Configuración de Pygame
pygame.init()

# Dimensiones de la pantalla
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Roomba Cat & Mouse")

# Colores
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Zonas de limpieza (x, y, ancho, alto)
zonas = {
    'Zona 1': (50, 50, 200, 150),
    'Zona 2': (300, 100, 180, 101),
    'Zona 3': (100, 300, 309, 200),
    'Zona 4': (400, 400, 90, 220)
}

# Cálculo de áreas para determinar el tiempo de limpieza
def calcular_area(largo, ancho):
    return largo * ancho

areas = {}
with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_zona = {executor.submit(calcular_area, w, h): zona for zona, (_, _, w, h) in zonas.items()}
    for future in concurrent.futures.as_completed(future_to_zona):
        zona = future_to_zona[future]
        areas[zona] = future.result()

superficie_total = sum(areas.values())
tasa_limpeza = 1000
limpieza_tiempo = superficie_total / tasa_limpeza

# Personajes
class Roomba:
    def __init__(self, x, y, color, speed):
        self.x = x
        self.y = y
        self.color = color
        self.speed = speed
        self.rect = pygame.Rect(self.x, self.y, 30, 30)
    
    def move_towards(self, target_x, target_y):
        if self.x < target_x:
            self.x += min(self.speed, target_x - self.x)
        elif self.x > target_x:
            self.x -= min(self.speed, self.x - target_x)
        if self.y < target_y:
            self.y += min(self.speed, target_y - self.y)
        elif self.y > target_y:
            self.y -= min(self.speed, self.y - target_y)
        self.rect.topleft = (self.x, self.y)
    
    def draw(self):
        pygame.draw.rect(screen, self.color, self.rect)

# Inicialización de Roombas
mouse_roomba = Roomba(100, 100, BLUE, 2)  # Roomba ratón
cat_roomba = Roomba(400, 300, RED, 4)  # Roomba gato (jugador)

# Quesos dentro de las zonas
quesos = []
for _ in range(5):
    zona = random.choice(list(zonas.values()))
    x = random.randint(zona[0], zona[0] + zona[2] - 10)
    y = random.randint(zona[1], zona[1] + zona[3] - 10)
    quesos.append(pygame.Rect(x, y, 10, 10))

# Bucle principal
def game_loop():
    running = True
    clock = pygame.time.Clock()
    cheese_index = 0
    
    while running:
        screen.fill(WHITE)
        for zona in zonas.values():
            pygame.draw.rect(screen, YELLOW, zona, 2)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            cat_roomba.x -= cat_roomba.speed
        if keys[pygame.K_RIGHT]:
            cat_roomba.x += cat_roomba.speed
        if keys[pygame.K_UP]:
            cat_roomba.y -= cat_roomba.speed
        if keys[pygame.K_DOWN]:
            cat_roomba.y += cat_roomba.speed
        cat_roomba.rect.topleft = (cat_roomba.x, cat_roomba.y)
        
        if cheese_index < len(quesos):
            target_cheese = quesos[cheese_index]
            mouse_roomba.move_towards(target_cheese.x, target_cheese.y)
            if mouse_roomba.rect.colliderect(target_cheese):
                quesos.pop(cheese_index)
        
        for cheese in quesos:
            pygame.draw.rect(screen, YELLOW, cheese)
        
        mouse_roomba.draw()
        cat_roomba.draw()
        
        if mouse_roomba.rect.colliderect(cat_roomba.rect):
            print("El gato atrapó al ratón. Fin del juego.")
            running = False
        elif len(quesos) == 0:
            print("El ratón recogió todos los quesos. Fin del juego.")
            running = False
        
        pygame.display.flip()
        clock.tick(30)
    
    pygame.quit()

game_loop()
