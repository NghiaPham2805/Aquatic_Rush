from pathlib import Path

import sys
import pygame

from ..config import (
    COOLDOWN_FRAMES,
    FLICKER_INTERVAL,
    GRAVITY,
    INVINCIBILITY_FRAMES,
    JUMP_X,
    JUMP_Y,
    MAX_FALL_SPEED,
    SPIN_SPEED_DEGREES,
    WIDTH,
)
from ..sprite_fx import add_outline

# --- UPDATED ASSET PATH LOGIC ---
if getattr(sys, 'frozen', False):
    # If built as a PyInstaller .exe, look for assets next to the executable
    ASSETS_DIR = Path(sys.executable).resolve().parent / "assets"
else:
    # If running normally in VS Code, go up two directories (entities -> bounce_climber)
    ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
# --------------------------------

# Assuming your game runs at 60 FPS:
# 60 frames = 1.0 seconds
# 90 frames = 1.5 seconds
# 120 frames = 2.0 seconds
UP_COOLDOWN_FRAMES = 45


class Player:
    _image = None

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.radius = 12
        self.jump_cooldown = 0
        self.up_jump_cooldown = 0
        self.current_max_up_cooldown = UP_COOLDOWN_FRAMES  
        self.difficulty_bonus = 0.0  
        self.invincible_timer = 0
        self.spin_angle = 0.0
        self.spin_speed = 0.0
        self.rect = pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)
        # --- NEW: Load Action/Jump Sound ---
        try:
            self.action_sound = pygame.mixer.Sound(str(ASSETS_DIR / "action.wav"))
            self.action_sound.set_volume(0.15)
        except FileNotFoundError:
            self.action_sound = None

    def jump(self, direction):
        # Grace frames increase as the game gets faster
        GRACE_FRAMES = 5 + int(self.difficulty_bonus)

        # 1. Block the UP jump if it is on cooldown
        if direction == "UP" and self.up_jump_cooldown > 0:
            return

        # Dynamically reduce the horizontal jump lockout 
        # (Restored the missing minus sign here)
        dynamic_jump_cooldown = max(4, int(COOLDOWN_FRAMES - self.difficulty_bonus))

        # --- NEW: Directional Reversal Leniency ---
        # Get the last direction the player successfully jumped
        last_dir = getattr(self, 'last_jump_direction', None)
        
        # Check if they are trying to sharply change directions
        is_reversing = (direction == "LEFT" and last_dir == "RIGHT") or (direction == "RIGHT" and last_dir == "LEFT")
        # ------------------------------------------

        # Reduce the cooldown by 1 frame specifically for A/D cancels
        if is_reversing:
            dynamic_jump_cooldown -= 1
        # ------------------------------------------


        # 2. Cooldown logic for jump spam
        if self.jump_cooldown > 0:
            
            # ONLY the A+D Vertical Dash is allowed to cancel a jump's startup frames
            if direction == "UP" and self.jump_cooldown >= (dynamic_jump_cooldown - GRACE_FRAMES):
                pass 
                
            else:
                # Lock out everything else. If they press A or D, they must wait 
                # for the full recovery cooldown to finish.
                return

        # Apply the dynamically calculated cooldown
        self.jump_cooldown = dynamic_jump_cooldown
        
        # --- NEW: Remember this jump direction for next time ---
        self.last_jump_direction = direction
        # -------------------------------------------------------
        
        # Play Action Sound
        if self.action_sound:
            self.action_sound.stop()
            self.action_sound.play()
            self.jump_triggered = True
        
        if direction == "LEFT":
            self.vx = -JUMP_X
            self.vy = JUMP_Y
            self.spin_speed = -SPIN_SPEED_DEGREES
            self.up_jump_cooldown = 0  
            
        elif direction == "RIGHT":
            self.vx = JUMP_X
            self.vy = JUMP_Y
            self.spin_speed = SPIN_SPEED_DEGREES
            self.up_jump_cooldown = 0  
            
        elif direction == "UP":
            self.vx = 0
            # Restored the missing multiplication sign here
            self.vy = JUMP_Y * 1.3  
            self.spin_speed = 0.0
            self.spin_angle = 0.0  

            # Reduce max UP cooldown based on game speed. 
            # Restored the missing minus and multiplication signs here
            dynamic_up_cooldown = int(UP_COOLDOWN_FRAMES - (self.difficulty_bonus * 40))
            
            self.current_max_up_cooldown = dynamic_up_cooldown
            self.up_jump_cooldown = dynamic_up_cooldown

    def update(self):
        # Apply Gravity
        self.vy += GRAVITY
        if self.vy > MAX_FALL_SPEED:
            self.vy = MAX_FALL_SPEED

        # Move
        self.x += self.vx
        self.y += self.vy

        # --- UPDATED: Smoothly wrap the exact float coordinate without gaps or popping ---
        self.x %= WIDTH
        # -------------------------------------------------------------------------------

        # Reduce cooldown
        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1
        
        if self.up_jump_cooldown > 0:
            self.up_jump_cooldown -= 1

        # Reduce invincibility (iframes) after getting hit
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

        # Keep frantically spinning until the next input straightens or redirects it
        self.spin_angle = (self.spin_angle + self.spin_speed) % 360

        # Update hitbox
        self.rect.topleft = (self.x - self.radius, self.y - self.radius)

    def is_invincible(self):
        return self.invincible_timer > 0

    def start_invincibility(self):
        self.invincible_timer = INVINCIBILITY_FRAMES

    @classmethod
    def _get_image(cls):
        if cls._image is None:
            raw = pygame.image.load(str(ASSETS_DIR / "Squid.png")).convert_alpha()
            sprite_diameter = int(12 * 2 * 2)  # Drawn larger than the hitbox for visual flair
            scaled = pygame.transform.smoothscale(raw, (sprite_diameter, sprite_diameter))
            cls._image = add_outline(scaled)
        return cls._image

    def draw(self, surface, camera_y):
        # --- REMOVED THE FLICKER RETURN STATEMENT HERE ---

        draw_y = self.y - camera_y
        image = self._get_image()

        if self.spin_angle:
            image = pygame.transform.rotate(image, self.spin_angle)

        # Draw the main player sprite
        rect = image.get_rect(center=(int(self.x), int(draw_y)))
        surface.blit(image, rect)

        # --- VISUAL GHOSTS ---
        if self.x - self.radius < 0:
            ghost_rect = image.get_rect(center=(int(self.x + WIDTH), int(draw_y)))
            surface.blit(image, ghost_rect)
            
        elif self.x + self.radius > WIDTH:
            ghost_rect = image.get_rect(center=(int(self.x - WIDTH), int(draw_y)))
            surface.blit(image, ghost_rect)
        # --------------------------

        # --- NEW: THE BUBBLE SHIELD ---
        if self.is_invincible():
            # Calculate how much time is left (1.0 is full, 0.0 is empty)
            time_left = self.invincible_timer / INVINCIBILITY_FRAMES
            
            # Determine if the shield should be visible this frame
            draw_shield = True
            
            # In the final 30% of the timer, blink the shield rapidly to warn the player
            if time_left < 0.3:
                # Blinks on and off every 4 frames
                if (self.invincible_timer // 4) % 2 == 0:
                    draw_shield = False
                    
            if draw_shield:
                # Create a transparent surface large enough to hold the bubble
                bubble_radius = self.radius + 12
                bubble_surf = pygame.Surface((bubble_radius * 2, bubble_radius * 2), pygame.SRCALPHA)
                
                # Draw the translucent blue fill (R, G, B, Alpha)
                pygame.draw.circle(bubble_surf, (0, 200, 255, 60), (bubble_radius, bubble_radius), bubble_radius)
                # Draw the solid glowing rim
                pygame.draw.circle(bubble_surf, (0, 255, 255, 200), (bubble_radius, bubble_radius), bubble_radius, 3)
                
                # Draw the bubble over the main player
                surface.blit(bubble_surf, (int(self.x) - bubble_radius, int(draw_y) - bubble_radius))
                
                # Draw the bubble over the screen-wrapping ghosts
                if self.x - self.radius < 0:
                    surface.blit(bubble_surf, (int(self.x + WIDTH) - bubble_radius, int(draw_y) - bubble_radius))
                elif self.x + self.radius > WIDTH:
                    surface.blit(bubble_surf, (int(self.x - WIDTH) - bubble_radius, int(draw_y) - bubble_radius))
        # ------------------------------

        # --- UP Jump Radial "Outline" Cooldown Indicator ---
        if self.up_jump_cooldown > 0:
            import math
            
            center = (int(self.x), int(draw_y))
            radius = self.radius + 8 
            thickness = 3  
            
            pygame.draw.circle(surface, (40, 50, 70), center, radius, thickness)
            
            fill_ratio = (UP_COOLDOWN_FRAMES - self.up_jump_cooldown) / UP_COOLDOWN_FRAMES
            num_segments = int(36 * fill_ratio)  
            if num_segments > 1:
                points = []
                start_angle = -math.pi / 2
                total_arc = 2 * math.pi * fill_ratio 
                
                for i in range(num_segments + 1):
                    t = i / num_segments
                    angle = start_angle + (t * total_arc)
                    px = center[0] + int(radius * math.cos(angle))
                    py = center[1] + int(radius * math.sin(angle))
                    points.append((px, py))
                
                color_val = int(100 + (155 * fill_ratio))
                color = (color_val, int(200 * fill_ratio) + 20, 50)  
                
                pygame.draw.lines(surface, color, False, points, thickness)

    
