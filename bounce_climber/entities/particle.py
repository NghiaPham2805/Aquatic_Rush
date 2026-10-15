# bounce_climber/entities/particle.py
import random
import pygame

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        # Burst outward in random directions
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-5, 1)
        self.color = color
        self.size = random.randint(4, 8)
        self.life = random.randint(20, 40)  # Frames before the particle disappears
        self.max_life = self.life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # Slight gravity pulling them down
        self.life -= 1

    def draw(self, surface, camera_y):
        if self.life > 0:
            # Shrink the particle as it gets closer to dying
            current_size = max(1, int((self.life / self.max_life) * self.size))
            draw_y = self.y - camera_y
            rect = pygame.Rect(int(self.x), int(draw_y), current_size, current_size)
            pygame.draw.rect(surface, self.color, rect)