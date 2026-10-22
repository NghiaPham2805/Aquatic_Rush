import sys
from pathlib import Path

import pygame

# --- UPDATED ASSET PATH LOGIC ---
if getattr(sys, 'frozen', False):
    # If built as a PyInstaller .exe, look for assets next to the executable
    ASSETS_DIR = Path(sys.executable).resolve().parent / "assets"
else:
    # If running normally in VS Code, go up two directories (entities -> bounce_climber)
    ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
# --------------------------------


class Coin:
    _image = None

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 16

    @classmethod
    def _get_image(cls):
        if cls._image is None:
            raw = pygame.image.load(str(ASSETS_DIR / "coin.png")).convert_alpha()
            diameter = 16 * 2
            cls._image = pygame.transform.smoothscale(raw, (diameter, diameter))
        return cls._image

    def draw(self, surface, camera_y):
        draw_y = self.y - camera_y
        image = self._get_image()
        rect = image.get_rect(center=(int(self.x), int(draw_y)))
        surface.blit(image, rect)

