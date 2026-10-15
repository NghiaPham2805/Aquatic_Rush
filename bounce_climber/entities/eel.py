# bounce_climber/entities/eel.py
import random
import pygame
from bounce_climber.config import WIDTH
from bounce_climber.entities.obstacle import Obstacle

class Eel(Obstacle):
    def __init__(self, y, difficulty):
        w, h = 100, 24 
        self.direction = random.choice([1, -1])
        x = -w if self.direction == 1 else WIDTH
        super().__init__(x, y, w, h, "eel.png", difficulty=difficulty)
        
        self.is_eel = True
        self.state = "WAITING"   # --- NEW: Start idle ---
        self.is_dead = False     # --- NEW: Track when it flies off ---
        self.warning_frames = 90 
        self.move_speed = (6 + difficulty * 2) * self.direction

        if self.direction == 1:
            self.image = pygame.transform.flip(self.image, True, False)

    # --- NEW: Accept camera_y to know when we are on screen ---
    def update(self, camera_y):
        if self.state == "WAITING":
            # camera_y is the very top of the screen. 
            # Trigger the warning when the eel is 250 pixels DOWN from the top,
            # putting it perfectly in the player's jump path.
            if self.rect.y > camera_y + 250: 
                self.state = "WARNING"
                
        elif self.state == "WARNING":
            self.warning_frames -= 1
            if self.warning_frames <= 0:
                self.state = "ATTACK"
                
        elif self.state == "ATTACK":
            self.rect.x += self.move_speed
            
            # If it flies completely off the left or right side, mark it for deletion
            if self.rect.left > WIDTH + 100 or self.rect.right < -100:
                self.is_dead = True

    def draw(self, surface, camera_y):
        draw_y = self.rect.y - camera_y
        
        if self.state == "WARNING":
            # Draw a flashing red laser warning line across the whole screen
            if (self.warning_frames // 4) % 2 == 0:
                center_y = int(draw_y + self.rect.height / 2)
                pygame.draw.line(surface, (255, 50, 50), (0, center_y), (WIDTH, center_y), 2)
        else:
            # Draw the actual sprite once the warning finishes
            super().draw(surface, camera_y)