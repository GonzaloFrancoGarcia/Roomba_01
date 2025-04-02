import concurrent.futures
import threading
import time
import random
import math
import pygame

# ---------------------------
# Función auxiliar
# ---------------------------

def calcular_area(largo, ancho):
    """Calcula el área de una zona (cm²)."""
    return largo * ancho

# ==============================================================
# CLASE ROOMBAWORLD (LÓGICA DEL MUNDO)
# ==============================================================

class RoombaWorld:
    def __init__(self, window_size=(600, 600), tasa_limpeza=1000, velocidad_base=10):
        self.window_width, self.window_height = window_size
        self.tasa_limpeza = tasa_limpeza
        self.velocidad_base = velocidad_base

        # Definición de zonas: (largo, alto) en centímetros
        self.zonas = {
            'Zona 1': (500, 150),
            'Zona 2': (101, 220),
            'Zona 3': (309, 220),
            'Zona 4': (500, 150)
        }
        # Posiciones en la "habitación" (para conversión a píxeles)
        self.zone_positions = {
            'Zona 1': (50, 41),
            'Zona 2': (50, 190),
            'Zona 3': (241, 190),
            'Zona 4': (50, 408)
        }
        # Suponemos que la habitación es de 600 x 600 cm
        ROOM_WIDTH_CM = 600
        ROOM_HEIGHT_CM = 600
        self.SCALE = min(self.window_width / ROOM_WIDTH_CM, self.window_height / ROOM_HEIGHT_CM)
        
        # Calcular rectángulos (en píxeles) para cada zona:
        self.zone_rects = {}
        for zona, (largo, alto) in self.zonas.items():
            pos = self.zone_positions[zona]
            self.zone_rects[zona] = (
                int(pos[0] * self.SCALE),
                int(pos[1] * self.SCALE),
                int(largo * self.SCALE),
                int(alto * self.SCALE)
            )
        
        # Estado de "gente durmiendo" (partículas) por zona
        self.dust_particles = {zona: [] for zona in self.zonas}
        self.lock = threading.Lock()
        
        # Estado del "mosquito" (simula el Roomba)
        self.mosquito_pos = [self.window_width // 2, self.window_height // 2]
        self.mosquito_vel = [
            random.choice([-1, 1]) * self.velocidad_base * (self.tasa_limpeza / 1000),
            random.choice([-1, 1]) * self.velocidad_base * (self.tasa_limpeza / 1000)
        ]
        
        # Nivel inicial y cálculo de la superficie total
        self.level = 1
        self.superficie_total = sum(calcular_area(largo, alto) for largo, alto in self.zonas.values())
        
        # Evento para detener la simulación
        self.mosquito_stop_event = threading.Event()

    def generar_dust(self, zona, stop_event, nivel):
        """
        Genera "gente durmiendo" en la zona usando el sprite "sleeping.png".
        Se utiliza un retraso proporcional al nivel para controlar la aparición.
        Este método se ejecuta en un hilo.
        """
        x0, y0, width, height = self.zone_rects[zona]
        while not stop_event.is_set():
            delay = random.uniform(6.0, 8.0) / nivel
            time.sleep(delay)
            x = random.randint(x0, x0 + width)
            y = random.randint(y0, y0 + height)
            with self.lock:
                self.dust_particles[zona].append((x, y))
            print(f"{zona}: Gente durmiendo generada en ({x}, {y}). Total: {len(self.dust_particles[zona])}")

    def mover_mosquito(self, bite_sound):
        """
        Actualiza el movimiento del mosquito y elimina las partículas (simula "picaduras")
        utilizando modos (modo SEEK y movimiento aleatorio).
        Este método se ejecuta en un hilo.
        """
        cleaning_radius = 10
        dt = 0.05
        last_print = time.time()
        last_collection_time = time.time()
        in_seek_mode = False
        seek_start_time = None

        def allowed_position(x, y):
            for rect in self.zone_rects.values():
                rx, ry, rw, rh = rect
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    return True
            return False

        while not self.mosquito_stop_event.is_set():
            time.sleep(dt)
            with self.lock:
                current_time = time.time()
                if not in_seek_mode and (current_time - last_collection_time > 5):
                    in_seek_mode = True
                    seek_start_time = current_time
                    print("Modo SEEK activado: 5 s sin picar gente.")
                if in_seek_mode and (current_time - seek_start_time > 5):
                    in_seek_mode = False
                    self.mosquito_vel[0] = random.choice([-1, 1]) * self.velocidad_base * (self.tasa_limpeza / 1000)
                    self.mosquito_vel[1] = random.choice([-1, 1]) * self.velocidad_base * (self.tasa_limpeza / 1000)
                    last_collection_time = current_time
                    print("Modo SEEK cancelado: 5 s sin picar, volviendo a aleatorio.")
                
                if in_seek_mode:
                    candidate = None
                    best_dist = float('inf')
                    for zona in self.dust_particles:
                        for (x, y) in self.dust_particles[zona]:
                            dist = (x - self.mosquito_pos[0])**2 + (y - self.mosquito_pos[1])**2
                            if dist < best_dist:
                                best_dist = dist
                                candidate = (x, y)
                    if candidate is not None:
                        dx = candidate[0] - self.mosquito_pos[0]
                        dy = candidate[1] - self.mosquito_pos[1]
                        norm = math.sqrt(dx * dx + dy * dy)
                        if norm > 0:
                            speed = math.sqrt(self.mosquito_vel[0]**2 + self.mosquito_vel[1]**2)
                            self.mosquito_vel[0] = speed * dx / norm
                            self.mosquito_vel[1] = speed * dy / norm
                        print("Modo SEEK: ajustando dirección hacia la gente durmiendo.")
                
                if not in_seek_mode:
                    near_threshold = 30
                    candidate_near = None
                    best_dist_near = float('inf')
                    for zona in self.dust_particles:
                        for (x, y) in self.dust_particles[zona]:
                            dx = x - self.mosquito_pos[0]
                            dy = y - self.mosquito_pos[1]
                            dist = math.sqrt(dx * dx + dy * dy)
                            if dist < near_threshold and dist < best_dist_near:
                                best_dist_near = dist
                                candidate_near = (x, y)
                    if candidate_near is not None:
                        dx = candidate_near[0] - self.mosquito_pos[0]
                        dy = candidate_near[1] - self.mosquito_pos[1]
                        norm = math.sqrt(dx * dx + dy * dy)
                        if norm > 0:
                            speed = math.sqrt(self.mosquito_vel[0]**2 + self.mosquito_vel[1]**2)
                            self.mosquito_vel[0] = speed * dx / norm
                            self.mosquito_vel[1] = speed * dy / norm
                        print("Modo aleatorio: acercándose a gente durmiendo.")
                
                new_x = self.mosquito_pos[0] + self.mosquito_vel[0]
                new_y = self.mosquito_pos[1] + self.mosquito_vel[1]
                if allowed_position(new_x, new_y):
                    self.mosquito_pos[0] = new_x
                    self.mosquito_pos[1] = new_y
                else:
                    if allowed_position(self.mosquito_pos[0] + self.mosquito_vel[0], self.mosquito_pos[1]):
                        self.mosquito_pos[0] += self.mosquito_vel[0]
                        self.mosquito_vel[1] = -self.mosquito_vel[1]
                    elif allowed_position(self.mosquito_pos[0], self.mosquito_pos[1] + self.mosquito_vel[1]):
                        self.mosquito_pos[1] += self.mosquito_vel[1]
                        self.mosquito_vel[0] = -self.mosquito_vel[0]
                    else:
                        self.mosquito_vel[0] = -self.mosquito_vel[0]
                        self.mosquito_vel[1] = -self.mosquito_vel[1]
                
                cleaned = False
                for zona in self.dust_particles:
                    new_list = []
                    for (x, y) in self.dust_particles[zona]:
                        if (x - self.mosquito_pos[0])**2 + (y - self.mosquito_pos[1])**2 >= cleaning_radius**2:
                            new_list.append((x, y))
                        else:
                            cleaned = True
                            print(f"Mosquito picó gente en {zona} en ({x}, {y})")
                            bite_sound.play()
                    self.dust_particles[zona] = new_list
                if cleaned:
                    last_collection_time = current_time
                    if in_seek_mode:
                        in_seek_mode = False
                        print("Gente picada en modo SEEK; volviendo a aleatorio.")
                if time.time() - last_print >= 1:
                    total = sum(len(lst) for lst in self.dust_particles.values())
                    print(f"Mosquito en {self.mosquito_pos}; Gente durmiendo restante: {total}")
                    last_print = time.time()

    @staticmethod
    def allowed_position_general(x, y, zone_rects):
        """Método estático para verificar si (x, y) está dentro de alguna zona."""
        for rect in zone_rects.values():
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return True
        return False

# ==============================================================
# CLASE ROOMBARENDERER (PARTE VISUAL)
# ==============================================================

class RoombaRenderer:
    def __init__(self, world: RoombaWorld):
        self.world = world
        self.window_width, self.window_height = world.window_width, world.window_height
        self.SCALE = world.SCALE
        pygame.init()
        self.screen = pygame.display.set_mode((self.window_width, self.window_height))
        pygame.display.set_caption("Simulación Mosquito - Jugador vs Mosquito")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 16)
        
        # Cargar sprites – asegúrate de que los archivos existan en el directorio actual
        self.mosquito_sprite = pygame.image.load("mosquito.png").convert_alpha()
        self.player_sprite = pygame.image.load("slipper.png").convert_alpha()
        self.sleeping_sprite = pygame.image.load("sleeping.png").convert_alpha()
        self.mosquito_size = (10, 10)
        self.player_size = (20, 20)
        self.sleeping_size = (30, 30)
        self.mosquito_sprite = pygame.transform.scale(self.mosquito_sprite, self.mosquito_size)
        self.player_sprite = pygame.transform.scale(self.player_sprite, self.player_size)
        self.sleeping_sprite = pygame.transform.scale(self.sleeping_sprite, self.sleeping_size)
        
        pygame.mixer.init()
        pygame.mixer.music.load("background_music.mp3")
        pygame.mixer.music.set_volume(0.1)
        pygame.mixer.music.play(-1)
        self.squash_sound = pygame.mixer.Sound("squash.mp3")
        self.squash_sound.set_volume(1.0)
    
    def render(self):
        running = True
        player_speed = 5
        player_pos = [int(100 * self.SCALE), int(100 * self.SCALE)]
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            keys = pygame.key.get_pressed()
            dx, dy = 0, 0
            if keys[pygame.K_LEFT]:
                dx = -player_speed
            if keys[pygame.K_RIGHT]:
                dx = player_speed
            if keys[pygame.K_UP]:
                dy = -player_speed
            if keys[pygame.K_DOWN]:
                dy = player_speed
            candidate_x = player_pos[0] + dx
            candidate_y = player_pos[1] + dy
            if RoombaWorld.allowed_position_general(candidate_x, candidate_y, self.world.zone_rects):
                player_pos[0] = candidate_x
                player_pos[1] = candidate_y
            
            self.screen.fill((30, 30, 30))
            # Dibujar zonas y mostrar cuenta de "gente"
            for zona, rect in self.world.zone_rects.items():
                pygame.draw.rect(self.screen, (70, 70, 200), rect, 2)
                text_zone = self.font.render(zona, True, (200, 200, 200))
                self.screen.blit(text_zone, (rect[0] + 5, rect[1] + 5))
                with self.world.lock:
                    count = len(self.world.dust_particles[zona])
                count_text = self.font.render(f"Gente: {count}", True, (200, 200, 200))
                self.screen.blit(count_text, (rect[0] + 5, rect[1] + 30))
                with self.world.lock:
                    dust_list = list(self.world.dust_particles[zona])
                for (x, y) in dust_list:
                    self.screen.blit(self.sleeping_sprite, 
                                     (x - self.sleeping_size[0]//2, y - self.sleeping_size[1]//2))
            
            with self.world.lock:
                current_mosquito_pos = self.world.mosquito_pos[:]
            self.screen.blit(self.mosquito_sprite, (
                int(current_mosquito_pos[0]) - self.mosquito_size[0]//2,
                int(current_mosquito_pos[1]) - self.mosquito_size[1]//2
            ))
            mosquito_text = self.font.render(
                f"Mosquito: ({int(current_mosquito_pos[0])}, {int(current_mosquito_pos[1])})",
                True, (0, 255, 0)
            )
            self.screen.blit(mosquito_text, (self.window_width - 220, self.window_height - 30))
            
            self.screen.blit(self.player_sprite, (
                int(player_pos[0]) - self.player_size[0]//2,
                int(player_pos[1]) - self.player_size[1]//2
            ))
            player_text = self.font.render(
                f"Jugador: ({int(player_pos[0])}, {int(player_pos[1])})",
                True, (255, 0, 0)
            )
            self.screen.blit(player_text, (20, self.window_height - 30))
            
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

# ==============================================================
# FUNCION MAIN (DEMOSTRACIÓN LOCAL)
# ==============================================================

def main():
    # Inicializar pygame y el mixer desde aquí
    pygame.init()
    pygame.mixer.init()
    
    # Crear la instancia del mundo de simulación
    world = RoombaWorld(window_size=(600,600), tasa_limpeza=1000, velocidad_base=10)
    
    # Cargar el sonido para "mosquito_bite" (ahora el mixer ya está inicializado)
    bite_sound = pygame.mixer.Sound("mosquito_bite.mp3")
    bite_sound.set_volume(1.0)
    
    # Iniciar el hilo para mover el mosquito
    mosquito_thread = threading.Thread(target=world.mover_mosquito, args=(bite_sound,), daemon=True)
    mosquito_thread.start()
    
    # Iniciar hilos para generar partículas ("dust") en cada zona
    dust_stop_events = {}
    dust_threads = []
    for zona in world.zonas:
        stop_event = threading.Event()
        dust_stop_events[zona] = stop_event
        t = threading.Thread(target=world.generar_dust, args=(zona, stop_event, world.level), daemon=True)
        t.start()
        dust_threads.append(t)
    
    # Iniciar la parte visual (renderizado)
    renderer = RoombaRenderer(world)
    renderer.render()
    
    # Al salir, detener la simulación y los hilos
    world.mosquito_stop_event.set()
    for e in dust_stop_events.values():
        e.set()
    mosquito_thread.join()
    for t in dust_threads:
        t.join()

if __name__ == '__main__':
    main()
