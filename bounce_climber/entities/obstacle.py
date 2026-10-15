from pathlib import Path
import random
import sys
import pygame

from bounce_climber.config import WIDTH  # Make sure to import WIDTH
from bounce_climber.sprite_fx import add_outline

# --- UPDATED ASSET PATH LOGIC ---
if getattr(sys, 'frozen', False):
    # If built as a PyInstaller .exe, look for assets next to the executable
    ASSETS_DIR = Path(sys.executable).resolve().parent / "assets"
else:
    # If running normally in VS Code, go up two directories (entities -> bounce_climber)
    ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
# --------------------------------


class Obstacle:
    _raw_image_cache = {}

    # --- UPDATED: Added 'difficulty' parameter ---
    def __init__(self, x, y, w, h, image_name, difficulty=0.0):
        self.rect = pygame.Rect(x, y, w, h)
        image = self._get_scaled_image(image_name, w, h)
        
        # 1. Scale Dynamic Chance: Starts at 10%, goes up to 55% at max difficulty (3.0)
        dynamic_chance = 0.10 + (difficulty * 0.15)
        self.is_dynamic = random.random() < dynamic_chance
        
        if self.is_dynamic:
            # 2. Scale Speed: Starts at 1.0 - 2.5, scales up to 4.0 - 5.5 at max difficulty
            min_speed = 1.0 + difficulty
            max_speed = 2.5 + difficulty
            speed = random.uniform(min_speed, max_speed)
            self.vx = speed if random.choice([True, False]) else -speed
        else:
            self.vx = 0

        # Face the creature in the direction it's moving (or randomly if stationary)
        facing_left = (self.vx < 0) if self.is_dynamic else random.choice([True, False])
        if facing_left:
            image = pygame.transform.flip(image, True, False)
            
        self.image = add_outline(image)

    @classmethod
    def _get_raw_image(cls, image_name):
        if image_name not in cls._raw_image_cache:
            cls._raw_image_cache[image_name] = pygame.image.load(str(ASSETS_DIR / image_name)).convert_alpha()
        return cls._raw_image_cache[image_name]

    @classmethod
    def _get_scaled_image(cls, image_name, w, h):
        raw = cls._get_raw_image(image_name)
        return pygame.transform.smoothscale(raw, (w, h))

    def update(self):
        if not self.is_dynamic:
            return

        # Move the obstacle
        self.rect.x += self.vx

        # Bounce off screen edges and flip image to face the new direction
        if self.rect.left < 0:
            self.rect.left = 0
            self.vx = abs(self.vx)  # Force positive (move right)
            self.image = pygame.transform.flip(self.image, True, False)
        elif self.rect.right > WIDTH:
            self.rect.right = WIDTH
            self.vx = -abs(self.vx) # Force negative (move left)
            self.image = pygame.transform.flip(self.image, True, False)

    def draw(self, surface, camera_y):
        cx, cy = self.rect.center
        cy -= camera_y
        draw_rect = self.image.get_rect(center=(cx, cy))
        surface.blit(self.image, draw_rect)