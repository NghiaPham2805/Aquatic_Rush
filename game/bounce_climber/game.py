import asyncio
import random
import sys
from pathlib import Path

import pygame

from .config import (
    BASE_SCROLL_SPEED,
    BUBBLE_COLOR,
    BUBBLE_COUNT,
    COIN_COLOR,
    FPS,
    HEIGHT,
    LAVA_COLOR,
    OBSTACLE_CREATURES,
    OCEAN_BOTTOM_COLOR,
    SAFE_START_GAP,
    SHAKE_DURATION_FRAMES,
    SHAKE_MAGNITUDE,
    STARTING_LIVES,
    TEXT_COLOR,
    WIDTH,
)
from .entities.coin import Coin
from .entities.obstacle import Obstacle
from .entities.player import Player
from .entities.particle import Particle
from .entities.eel import Eel
#from app.bounce_climber.leaderboard import submit_score_async, get_top_scores
#import threading

DIRECTION_KEYS = (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d, pygame.K_SPACE)
HEART_SIZE = 28
GAME_TITLE = "Aquatic Rush"
MODE_CLASSIC = "classic"
MODE_INFINITE = "infinite"

# --- UPDATED ASSET PATH LOGIC ---
if getattr(sys, 'frozen', False):
    # If built as a PyInstaller .exe
    ASSETS_DIR = Path(sys.executable).parent / "assets"
else:
    # If running normally in VS Code or Browser
    ASSETS_DIR = Path(__file__).parent / "assets"
# --------------------------------


class Game:
    """Owns all game state and runs the main loop for Vertical Bounce Climber."""

    def __init__(self):
        print("DEBUG A: Starting pygame.init()")
        pygame.init()

        # 1. ALWAYS initialize the display FIRST in WebAssembly!
        print("DEBUG B: Setting display mode")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.render_surface = pygame.Surface((WIDTH, HEIGHT))

        # 2. Prepare audio placeholders (we will unlock audio on first key press)
        self.audio_initialized = False
        self.crash_sound = None
        self.lose_sound = None
        self.coin_sound = None
        self.menu_click = None
        self.pending_music = "lobby_bgm.mp3"

        # 3. Load Fonts & Images (Always wrap Path in str() for WASM compatibility)
        print("DEBUG C: Loading fonts and heart image")
        self.font = pygame.font.Font(str(ASSETS_DIR / "PressStart2P.ttf"), 12)
        self.title_font = pygame.font.Font(str(ASSETS_DIR / "PressStart2P.ttf"), 30)
        self.heart_image = self._load_heart_image()
        
        self.bubbles = self._make_bubbles()
        self.shake_timer = 0
        self.particles = []
        self.waiting_for_initials = False
        self.player_initials = ""

        # 4. Load and scale our 3 background variants
        print("DEBUG D: Loading backgrounds")
        bg_files = ["background.png", "background2.png", "background3.png"]
        self.bg_images = []
        for file in bg_files:
            raw = pygame.image.load(str(ASSETS_DIR / file)).convert()
            w, h = raw.get_size()
            scale_ratio = WIDTH / w
            bg_h = int(h * scale_ratio)
            self.bg_images.append(pygame.transform.scale(raw, (WIDTH, bg_h)))
        
        self.bg_height = bg_h 
        
        self.assigned_bg_chunks = {
            -1: random.choice(self.bg_images),
             0: random.choice(self.bg_images),
             1: random.choice(self.bg_images)
        }

        # Menu and Difficulty States
        self.in_menu = True
        self.menu_stage = "MODE"
        self.difficulty_levels = ["Easy", "Normal", "Hard", "Impossible"]
        self.diff_idx = 1
        self.difficulty_name = "Normal"
        self.mode = MODE_CLASSIC

        # Heart Tracking
        self.hearts = []
        self.highest_heart_y = -random.randint(3000, 5000)
        
        print("DEBUG E: Running initial reset()")
        self.reset()
        print("DEBUG F: Game.__init__() complete!")

    def _load_heart_image(self):
        raw = pygame.image.load(str(ASSETS_DIR / "heart.png")).convert_alpha()
        # Scale the 16x16 sprite to 36x36 for a chunkier, 8-bit look that's easy to see
        # We use nearest-neighbor scaling (pygame.transform.scale) to keep it pixelated!
        return pygame.transform.scale(raw, (36, 36))


    def _make_bubbles(self):
        bubbles = []
        for _ in range(BUBBLE_COUNT):
            bubbles.append(
                {
                    "x": random.uniform(0, WIDTH),
                    "y": random.uniform(0, HEIGHT),
                    "radius": random.uniform(2, 6),
                    "speed": random.uniform(0.4, 1.6),
                    "drift": random.uniform(-0.3, 0.3),
                }
            )
        return bubbles

    def _update_bubbles(self):
        for bubble in self.bubbles:
            bubble["y"] -= bubble["speed"]
            bubble["x"] += bubble["drift"]
            if bubble["y"] + bubble["radius"] < 0:
                bubble["y"] = HEIGHT + bubble["radius"]
                bubble["x"] = random.uniform(0, WIDTH)
            elif bubble["x"] < 0 or bubble["x"] > WIDTH:
                bubble["x"] = bubble["x"] % WIDTH

    def _draw_bubbles(self, surface):
        for bubble in self.bubbles:
            # Draw squares instead of circles for a pixelated look
            size = int(bubble["radius"] * 2)
            rect = (int(bubble["x"]), int(bubble["y"]), size, size)
            pygame.draw.rect(surface, BUBBLE_COLOR, rect, 1)

    def reset(self):
        # --- NEW: Set up dynamic difficulty variables ---
        self.difficulty_name = getattr(self, 'difficulty_name', "Normal")
        
        # base = starting speed bonus, max = cap for that difficulty
        diff_settings = {
            "Easy": {"base": -0.5, "max": 2.0},
            "Normal": {"base": 0.0, "max": 3.0},
            "Hard": {"base": 1.0, "max": 4.0},
            "Impossible": {"base": 2.5, "max": 5.0}
        }
        
        setting = diff_settings[self.difficulty_name]
        self.base_speed_bonus = setting["base"]
        self.max_speed_bonus = setting["max"]
        self.speed_bonus = max(0.0, self.base_speed_bonus) # Prevents negative starting speed
        # ------------------------------------------------

        self.player = Player(WIDTH // 2, HEIGHT - 150)
        self.camera_y = 0
        self.death_zone_y = HEIGHT  
        self.obstacles = []
        # --- NEW: Spawn Static Tutorial Obstacles ---
        if self.mode == "TUTORIAL":
            # --- NEW: Wipe out any default obstacles that spawned earlier ---
            self.obstacles.clear() 
            
            # 1. Small Obstacle (Bottom Left)
            self.obstacles.append(Obstacle(WIDTH // 4 - 20, self.camera_y + HEIGHT - 150, 40, 30, "crab.png", difficulty=0))
            
            # 2. Medium Obstacle (Middle Right)
            self.obstacles.append(Obstacle(3 * WIDTH // 4 - 30, self.camera_y + HEIGHT - 350, 60, 50, "shark.png", difficulty=0))
            
            # 3. Big Obstacle / Whale (Top Left/Center)
            whale = Obstacle(WIDTH // 2 - 60, self.camera_y + HEIGHT - 600, 120, 100, "whale.png", difficulty=0)
            whale.is_whale = True
            self.obstacles.append(whale)
        # --------------------------------------------
        self.highest_obstacle_y = self.player.y - SAFE_START_GAP
        self.coins = []
        self.highest_coin_y = self.player.y - SAFE_START_GAP
        self.coins_collected = 0
        self.score = 0
        self.lives = STARTING_LIVES
        self.game_over = False
        self.game_started = False
        self.shake_timer = 0

        self._generate_obstacles()
        self._generate_coins()

        
        # --- UPDATED: Restart game BGM if restarting from a Game Over ---
        if not self.in_menu and self.audio_initialized and not pygame.mixer.music.get_busy():
            self._play_music("bgm.mp3")

    def _generate_obstacles(self):
        # Generate obstacles ahead of the camera, each a randomly picked ocean creature
        while self.highest_obstacle_y > self.camera_y - 800:
            
            # --- NEW: Explicit Level Design Spacing ---
            if getattr(self, 'difficulty_name', 'Normal') == "Easy":
                base_min, base_max = 220, 370  # Increased from 200, 350
            elif self.difficulty_name == "Normal":
                base_min, base_max = 170, 300  # Increased from 150, 280
            elif self.difficulty_name == "Hard":
                base_min, base_max = 125, 210  # Increased from 105, 190
            elif self.difficulty_name == "Impossible":
                base_min, base_max = 110, 180  # Increased from 90, 160
            else:
                base_min, base_max = 170, 300

            # Calculate how much the speed has naturally increased from climbing
            progression = max(0.0, self.speed_bonus - self.base_speed_bonus)
            
            # Slowly shrink the gap as they climb higher, but don't let it become physically impossible
            shrinkage_min = int(progression * 10)
            shrinkage_max = int(progression * 20)
            
            min_gap = max(80, base_min - shrinkage_min)  # 80 is the absolute minimum passable vertical space
            max_gap = max(130, base_max - shrinkage_max)
            
            self.highest_obstacle_y -= random.randint(min_gap, max_gap)
            # ------------------------------------------

            # --- NEW: Eel Spawning Logic ---
            # Check how many eels currently exist
            active_eels = sum(1 for ob in self.obstacles if getattr(ob, 'is_eel', False))
            
            # 15% chance to spawn an Eel, but NEVER spawn more than 1 at a time!
            if random.random() < 0.40 and active_eels < 2:
                new_eel = Eel(self.highest_obstacle_y, difficulty=self.speed_bonus)
                self.obstacles.append(new_eel)
                continue  # Skip the normal creature spawn for this height step
            # -------------------------------

            
            creature = random.choice(OBSTACLE_CREATURES)
            
            # --- NEW: Whale Limiter ---
            if "whale" in creature["image"].lower():
                active_whales = sum(1 for ob in self.obstacles if getattr(ob, 'is_whale', False))
                while "whale" in creature["image"].lower() and active_whales >= 2:
                    creature = random.choice(OBSTACLE_CREATURES)
            # --------------------------

            # --- NEW: Whale Speed Cap ---
            obstacle_speed = self.speed_bonus
            if "whale" in creature["image"].lower():
                # Cap the whale's speed multiplier at a very low number (e.g., 0.2)
                # so it stays slow and heavy even on Impossible difficulty.
                obstacle_speed = min(self.speed_bonus, 0.2)
            # ----------------------------

            # --- NEW: Locked Aspect Ratio Scaling ---
            # Pick a single random percentage (0.0 to 1.0) so the sprite scales uniformly
            scale_percent = random.random() 
            
            min_w, max_w = creature["width"]
            min_h, max_h = creature["height"]
            
            w = int(min_w + (max_w - min_w) * scale_percent)
            h = int(min_h + (max_h - min_h) * scale_percent)
            # ----------------------------------------
            
            x = random.randint(0, WIDTH - w)
            
            # Create the obstacle using the capped obstacle_speed, NOT self.speed_bonus!
            new_ob = Obstacle(x, self.highest_obstacle_y, w, h, creature["image"], difficulty=obstacle_speed)
            
            # --- NEW: Tag the obstacle so we can count it later ---
            if "whale" in creature["image"].lower():
                new_ob.is_whale = True
                
            self.obstacles.append(new_ob)

            # --- NEW: Generate Hearts ---
        while self.highest_heart_y > self.camera_y - 800:
            x = random.randint(30, WIDTH - 30)
            
            # Store hearts as simple Pygame Rects (30x30 pixels)
            self.hearts.append(pygame.Rect(x, self.highest_heart_y, 36, 36))
            
            # Schedule the next heart spawn 150-200 "meters" higher up
            self.highest_heart_y -= random.randint(3000, 5000)
        # ----------------------------

    def _generate_coins(self):
        # --- NEW: Scale coin rarity based on difficulty ---
        if getattr(self, 'difficulty_name', 'Normal') == "Easy":
            coin_min_gap, coin_max_gap = 150, 250
        elif self.difficulty_name == "Normal":
            coin_min_gap, coin_max_gap = 200, 350
        elif self.difficulty_name == "Hard":
            # Coins are rare, making the few you see a dangerous temptation
            coin_min_gap, coin_max_gap = 350, 550
        elif self.difficulty_name == "Impossible":
            # Extremely rare. You will only see one every 500-800 pixels.
            coin_min_gap, coin_max_gap = 500, 800
        else:
            coin_min_gap, coin_max_gap = 200, 350
        # --------------------------------------------------

        while True:
            # Preview the next coin's Y position before committing
            next_y = self.highest_coin_y - random.randint(coin_min_gap, coin_max_gap)
            
            # If this coin would spawn higher than the highest generated obstacle,
            # we STOP generating coins until the camera moves and more obstacles spawn.
            if next_y < self.highest_obstacle_y:
                break
                
            self.highest_coin_y = next_y
            
            # Try to place the coin. If it gets blocked by a moving obstacle's lane,
            # nudge it up safely by 80 pixels and try one more time!
            placed = self._try_place_coin(self.highest_coin_y)
            if not placed:
                self.highest_coin_y -= 80
                self._try_place_coin(self.highest_coin_y)

    def _try_place_coin(self, y, attempts=20):
        nearby_obstacles = [ob for ob in self.obstacles if abs(ob.rect.centery - y) < 250]
        
        for _ in range(attempts):
            if nearby_obstacles:
                ref_ob = min(nearby_obstacles, key=lambda ob: abs(ob.rect.centery - y))
                
                if ref_ob.rect.centerx < WIDTH // 2:
                    x = random.randint(WIDTH // 2, WIDTH - 30)
                else:
                    x = random.randint(30, WIDTH // 2)
            else:
                x = random.randint(30, WIDTH - 30)

            coin = Coin(x, y)
            
            if self._coin_clear_of_obstacles(coin, margin=25):
                self.coins.append(coin)
                return True # Successfully placed
                
        return False # Failed to place (likely due to a moving obstacle lane)

    def _coin_clear_of_obstacles(self, coin, margin=25):
        pad = coin.radius + margin
        
        for ob in self.obstacles:
            if getattr(ob, 'is_dynamic', False):
                # Extra strict vertical clearance for moving hazards (added +15 buffer)
                vertical_clearance = (ob.rect.height // 2) + pad + 15
                if abs(ob.rect.centery - coin.y) < vertical_clearance:
                    return False  # Block spawning anywhere on this horizontal line
            else:
                padded = ob.rect.inflate(pad * 2, pad * 2)
                if padded.collidepoint(coin.x, coin.y):
                    return False
                    
        return True

    def _held_directions(self):
        keys_now = pygame.key.get_pressed()
        left_down = keys_now[pygame.K_LEFT] or keys_now[pygame.K_a]
        right_down = keys_now[pygame.K_RIGHT] or keys_now[pygame.K_d]
        return left_down, right_down

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return  # Avoids sys.exit() crashing the browser tab

            if event.type == pygame.KEYDOWN:
                self._unlock_audio()  # Unlocks audio on the first key press

            if self.waiting_for_initials:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and len(self.player_initials) == 3:
                        # Submit the score and exit the input phase
                        #submit_score_async(self.player_initials.upper(), self.score)
                        self.waiting_for_initials = False 
                        
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_initials = self.player_initials[:-1]
                        
                    elif event.unicode.isalpha() and len(self.player_initials) < 3:
                        self.player_initials += event.unicode.upper()

            # Return to the main menu from the game-over screen
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.game_over or getattr(self, 'mode', None) == "TUTORIAL":
                    self.in_menu = True
                    self.menu_stage = "MODE"
                    self._play_music("lobby_bgm.mp3")
                    continue

            # Explicitly allow the Escape key to bypass this filter
            is_valid_key = event.type == pygame.KEYDOWN and (event.key in DIRECTION_KEYS or event.key == pygame.K_ESCAPE)

            if not is_valid_key:
                continue
            

            left_down, right_down = self._held_directions()

            # Catch A+D overlap OR Spacebar
            is_space = event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
            up_pressed = (left_down and right_down) or is_space

            if self.in_menu:
                if event.type == pygame.KEYDOWN:
                    
                    # --- NEW: Unified Mode Selection ---
                    if self.menu_stage == "MODE":
                        # Initialize options if they don't exist yet
                        if not hasattr(self, 'mode_options'):
                            self.mode_options = ["Tutorial", "Classic", "Infinite", "Leaderboard"]
                            self.mode_idx = 1 # Start on Classic
                            
                        if up_pressed:
                            if self.menu_click: self.menu_click.play()
                            
                            selected = self.mode_options[self.mode_idx]
                            if selected == "Tutorial":
                                self.mode = "TUTORIAL"
                                # Start tutorial immediately, bypassing difficulty
                                self._start_run("TUTORIAL", "Easy", "UP")
                            elif selected == "Classic":
                                self.mode = MODE_CLASSIC
                                self.menu_stage = "DIFFICULTY"
                            elif selected == "Infinite":
                                self.mode = MODE_INFINITE
                                self.menu_stage = "DIFFICULTY"
                            elif selected == "Leaderboard":
                                self.menu_stage = "LEADERBOARD"
                                self._fetch_leaderboard_async()
                                
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            if self.menu_click: self.menu_click.play()
                            self.mode_idx = max(0, self.mode_idx - 1)
                            
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            if self.menu_click: self.menu_click.play()
                            self.mode_idx = min(len(self.mode_options) - 1, self.mode_idx + 1)
                    # -----------------------------------

                    elif self.menu_stage == "DIFFICULTY":
                        if event.key == pygame.K_ESCAPE:
                            self.menu_stage = "MODE"
                            if self.menu_click: self.menu_click.play()
                        elif up_pressed:
                            if self.menu_click: self.menu_click.play()
                            self._start_run(self.mode, self.difficulty_levels[self.diff_idx], "UP")
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            if self.menu_click: self.menu_click.play()
                            self.diff_idx = max(0, self.diff_idx - 1)
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            if self.menu_click: self.menu_click.play()
                            self.diff_idx = min(len(self.difficulty_levels) - 1, self.diff_idx + 1)
                            
                    elif self.menu_stage == "LEADERBOARD":
                        if event.key == pygame.K_ESCAPE:
                            self.menu_stage = "MODE"
                            if self.menu_click: self.menu_click.play()

            if self.game_over:
                # Use the new up_pressed check
                if up_pressed:
                    self.reset()
                continue

            if not self.game_started:
                self.game_started = True

            # Use the new up_pressed check for gameplay
            if up_pressed:
                self.player.jump("UP")
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_a):
                self.player.jump("LEFT")
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RIGHT, pygame.K_d):
                self.player.jump("RIGHT")

    # --- UPDATED: Accepts difficulty_name ---
    def _start_run(self, mode, difficulty_name, direction):
        self.mode = mode
        self.difficulty_name = difficulty_name
        self.in_menu = False
        
        # --- NEW: Switch to gameplay music ---
        self._play_music("bgm.mp3")
        # -------------------------------------
        
        self.reset()
        self.game_started = True
        self.player.jump(direction)

    def _fetch_leaderboard_async(self):
        self.fetching_scores = True
        self.top_scores = []
        
        #def fetch():
        #    self.top_scores = get_top_scores()
        #    self.fetching_scores = False
            
        #threading.Thread(target=fetch, daemon=True).start()
        self.fetching_scores = False

    def update(self):
        # Decrement regardless of game state so shake doesn't get stuck once game_over is set
        if self.shake_timer > 0:
            self.shake_timer -= 1

        self._update_bubbles()

        if self.in_menu:
            return

        if not self.game_started or self.game_over:
            return

        self.player.update()

        # --- NEW: Jump Particles ---
        if getattr(self.player, 'jump_triggered', False):
            # Spawn 6 cyan particles at the bottom of the player to look like a splash/boost
            for _ in range(6):
                self.particles.append(Particle(self.player.x, self.player.y + self.player.radius, (0, 255, 255)))
            self.player.jump_triggered = False
        # ---------------------------

        # --- NEW: Tutorial Freeze Check ---
        # Only run camera, lava, and score logic if we are NOT in the tutorial
        if self.mode != "TUTORIAL":
            
            # Convert pixels to meters (30 pixels = 1 meter)
            start_y = HEIGHT - 150  
            pixels_climbed = max(0, start_y - self.player.y)  
            current_height_score = int(pixels_climbed / 30)

            if current_height_score > self.score:
                self.score = current_height_score

            # New Scroll logic (camera follows player)
            progression_bonus = (self.score // 250) * 0.1  
            
            # Add the base difficulty bonus and cap it according to the selected difficulty
            self.speed_bonus = self.base_speed_bonus + progression_bonus
            self.speed_bonus = max(0.0, min(self.speed_bonus, self.max_speed_bonus))
            
            scroll_speed = BASE_SCROLL_SPEED + self.speed_bonus

            # Pass the current difficulty back to the player to buff their stats
            self.player.difficulty_bonus = self.speed_bonus

            # Auto-scroll camera and death zone
            self.camera_y -= scroll_speed
            self.death_zone_y -= scroll_speed

            # If player is moving faster than camera towards the top of the screen, snap camera to player
            if self.player.y < self.camera_y + HEIGHT * 0.55:  
                diff = (self.camera_y + HEIGHT * 0.55) - self.player.y  
                self.camera_y -= diff
                self.death_zone_y -= diff  # Keep the distance between camera and death zone consistent

            # Cleanup old obstacles & generate new ones
            self.obstacles = [ob for ob in self.obstacles if ob.rect.y < self.camera_y + HEIGHT + 100 and not getattr(ob, 'is_dead', False)]
            self._generate_obstacles()

            # Cleanup old coins & generate new ones
            self.coins = [c for c in self.coins if c.y < self.camera_y + HEIGHT + 100]
            self._generate_coins()

            # Update dynamic obstacles
            for ob in self.obstacles:
                if getattr(ob, 'is_eel', False):
                    ob.update(self.camera_y)
                else:
                    ob.update()

            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.life > 0]
                
        # --- NEW: Tutorial Bounds ---
        elif self.mode == "TUTORIAL":
            # 1. The Floor (Stop falling forever)
            # Locks them about 50 pixels above the bottom of the screen
            floor_y = self.camera_y + HEIGHT - 50 
            if self.player.y + self.player.radius > floor_y:
                self.player.y = floor_y - self.player.radius
                self.player.vy = 0 # Stop falling momentum
                
            # 2. The Ceiling (Stop flying into space)
            # Locks them about 50 pixels below the top of the screen
            ceiling_y = self.camera_y + 50
            if self.player.y - self.player.radius < ceiling_y:
                self.player.y = ceiling_y + self.player.radius
                self.player.vy = max(0, self.player.vy) # Kill upward momentum (bonk their head)
        # ----------------------------------

       # Update Eels and pass the camera position
        for ob in self.obstacles:
            if getattr(ob, 'is_eel', False):
                ob.update(self.camera_y)

       # Collision Logic 
        if not self.player.is_invincible():
            # Ghost Hitbox Math
            hitboxes = [self.player.rect]
            
            # If wrapping off the left edge, create a ghost on the right
            if self.player.rect.left < 0:
                ghost = self.player.rect.copy()
                ghost.x += WIDTH
                hitboxes.append(ghost)
                
            # If wrapping off the right edge, create a ghost on the left
            elif self.player.rect.right > WIDTH:
                ghost = self.player.rect.copy()
                ghost.x -= WIDTH
                hitboxes.append(ghost)

            for ob in self.obstacles:
                # Check if ANY of the player's active hitboxes touch the obstacle
                if any(box.colliderect(ob.rect) for box in hitboxes):
                    if self.crash_sound:
                        self.crash_sound.play()
                        
                    # --- NEW: Spawn Damage Particles ---
                    for _ in range(20):
                        self.particles.append(Particle(self.player.x, self.player.y, (255, 69, 0)))
                    # -----------------------------------
                        
                    self.player.start_invincibility()
                    self.shake_timer = SHAKE_DURATION_FRAMES
                    if self.mode == MODE_CLASSIC:
                        self.lives -= 1
                        if self.lives <= 0:
                            self._trigger_game_over()
                    break

        # Coin collection
        for c in self.coins[:]:
            # Ghost Coin Math (Fixed minus signs)
            dist_real = ((self.player.x - c.x) ** 2 + (self.player.y - c.y) ** 2) ** 0.5
            dist_left = ((self.player.x + WIDTH - c.x) ** 2 + (self.player.y - c.y) ** 2) ** 0.5
            dist_right = ((self.player.x - WIDTH - c.x) ** 2 + (self.player.y - c.y) ** 2) ** 0.5
            
            # If ANY of the distances are close enough, collect the coin
            if min(dist_real, dist_left, dist_right) < self.player.radius + c.radius:
                self.coins.remove(c)
                self.coins_collected += 1
                
                # --- NEW: Spawn Gold Particles ---
                for _ in range(10):
                    self.particles.append(Particle(c.x, c.y, (255, 215, 0)))
                # ---------------------------------
                
                if self.coin_sound:
                    self.coin_sound.play()
                    
        # Death Zone logic (Fell off bottom)
        if self.mode != "TUTORIAL" and self.player.y > self.death_zone_y:
            self._trigger_game_over()

        # Heart Collection
        for h in self.hearts[:]:
            hx = h.centerx
            hy = h.centery
            
            # Ghost Heart Math (Fixed minus signs)
            dist_real = ((self.player.x - hx) ** 2 + (self.player.y - hy) ** 2) ** 0.5
            dist_left = ((self.player.x + WIDTH - hx) ** 2 + (self.player.y - hy) ** 2) ** 0.5
            dist_right = ((self.player.x - WIDTH - hx) ** 2 + (self.player.y - hy) ** 2) ** 0.5
            
            # UPDATED: Use 23 (half of the 46px hitbox) for generous collision
            if min(dist_real, dist_left, dist_right) < self.player.radius + 23:
                self.hearts.remove(h)
                self.lives += 1
                
                # --- NEW: Spawn Heart Particles ---
                for _ in range(12):
                    self.particles.append(Particle(hx, hy, (255, 50, 100)))
                # ----------------------------------
                
                if self.coin_sound:
                    self.coin_sound.play()
                    
        # Clean up hearts that scroll completely off the bottom of the screen
        self.hearts = [h for h in self.hearts if h.y < self.camera_y + HEIGHT + 100]

        

    def draw(self):
        surface = self.render_surface
        
        # Determine the base chunk index based on absolute camera position
        current_chunk = int(self.camera_y // self.bg_height)
        
        # Draw the current chunk, plus one above and one below
        for chunk_offset in [-1, 0, 1]:
            chunk_index = current_chunk + chunk_offset
            
            # Generate the background variation if it doesn't exist yet
            if chunk_index not in self.assigned_bg_chunks:
                self.assigned_bg_chunks[chunk_index] = random.choice(self.bg_images)
                
            # Calculate the true world Y position mapped to the screen
            screen_y = (chunk_index * self.bg_height) - self.camera_y
            
            # Blit perfectly locked to the world coordinates
            surface.blit(self.assigned_bg_chunks[chunk_index], (0, screen_y))
        
        # Clean up old chunks to prevent memory leaks (keep a safe buffer of 3)
        keys_to_remove = [k for k in self.assigned_bg_chunks if abs(k - current_chunk) > 3]
        for k in keys_to_remove:
            del self.assigned_bg_chunks[k]

        self._draw_bubbles(surface)

        if self.in_menu:
            self._draw_menu(surface)
            self.screen.blit(surface, (0, 0))
            pygame.display.flip()
            return

        for ob in self.obstacles:
            ob.draw(surface, self.camera_y)

        for c in self.coins:
            c.draw(surface, self.camera_y)
        # --- NEW: Draw Hearts ---
        for h in self.hearts:
            # h is a pygame.Rect(x, y, 30, 30)
            draw_y = h.y - self.camera_y
            
            # Use your existing heart asset and center it on the hitbox
            heart_rect = self.heart_image.get_rect(center=(h.centerx, int(draw_y + 15)))
            surface.blit(self.heart_image, heart_rect)
        # ------------------------
        for p in self.particles:
            p.draw(surface, self.camera_y)

        # --- NEW: Draw Tutorial Text HERE (Behind the Player) ---
        if getattr(self, 'mode', None) == "TUTORIAL":
            instructions = [
                "TUTORIAL (Esc to Exit)",
                "",
                "A / Left : Jump Left",
                "D / Right : Jump Right",
                "A + D : Vertical Dash",
                "",
                "ADVANCED TIP:",
                "Press A+D to instantly cancel",
                "a sideways jump and",
                "shoot straight up!"
            ]
            
            for i, line in enumerate(instructions):
                if not line: continue 
                color = (255, 215, 0) if i == 0 else (255, 255, 255)
                text_surf = self.font.render(line, True, color)
                surface.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, 300 + (i * 28)))
        # --------------------------------------------------------

        if not self.game_over:
            self.player.draw(surface, self.camera_y)

        self._draw_death_zone(surface)
        self._draw_ui(surface)

        offset = self._shake_offset()
        self.screen.fill(OCEAN_BOTTOM_COLOR)
        self.screen.blit(surface, offset)

        pygame.display.flip()

    def _shake_offset(self):
        if self.shake_timer <= 0:
            return (0, 0)
        return (
            random.randint(-SHAKE_MAGNITUDE, SHAKE_MAGNITUDE),
            random.randint(-SHAKE_MAGNITUDE, SHAKE_MAGNITUDE),
        )

    def _draw_death_zone(self, surface):
        draw_death_y = self.death_zone_y - self.camera_y
        if draw_death_y < HEIGHT:
            lava_rect = pygame.Rect(0, draw_death_y, WIDTH, HEIGHT - draw_death_y + 100)
            pygame.draw.rect(surface, LAVA_COLOR, lava_rect)

            # Add a glowing top line to the lava
            pygame.draw.line(surface, (255, 150, 0), (0, draw_death_y), (WIDTH, draw_death_y), 4)

    def _draw_ui(self, surface):

        # --- NEW: Tutorial On-Screen Text ---
        
        
        # Score is now accurately tracked in meters
        score_text = self.font.render(f"{max(0, self.score)}m", True, TEXT_COLOR)
        surface.blit(score_text, (10, 10))

        coin_text = self.font.render(f"Coins: {self.coins_collected}", True, COIN_COLOR)
        surface.blit(coin_text, (10, 45))

        # --- UPDATED: Speed Level Indicator ---
        # Level increases every 50 meters, capping at 31
        current_level = int(min(self.score // 250, 30)) + 1
        level_text = self.font.render(f"Speed Level {current_level}", True, (255, 215, 0))
        surface.blit(level_text, (WIDTH // 2 - level_text.get_width() // 2, 10))

        self._draw_lives(surface)

        if self.game_over:
            if self.waiting_for_initials:
                self._draw_game_over_input(surface)
            else:
                # Standard Game Over screen that appears AFTER initials are submitted
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(150)
                overlay.fill((0, 0, 0))
                surface.blit(overlay, (0, 0))

                go_text = self.font.render("GAME OVER", True, (255, 50, 50))
                surface.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 40))

                restart_text = self.font.render("Press A+D to Restart", True, TEXT_COLOR)
                surface.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 10))

                menu_text = self.font.render("Press Esc for Main Menu", True, TEXT_COLOR)
                surface.blit(menu_text, (WIDTH // 2 - menu_text.get_width() // 2, HEIGHT // 2 + 45))
            
        elif not self.game_started:
            hint_text = self.font.render("Press A/D or Arrow Keys", True, TEXT_COLOR)
            surface.blit(hint_text, (WIDTH // 2 - hint_text.get_width() // 2, HEIGHT // 2 - 40))

            hint_text2 = self.font.render("to Bounce and Start", True, TEXT_COLOR)
            surface.blit(hint_text2, (WIDTH // 2 - hint_text2.get_width() // 2, HEIGHT // 2))

    def _draw_lives(self, surface):
        if self.mode == MODE_INFINITE:
            infinite_text = self.font.render("Lives: \u221e", True, (255, 90, 90))
            surface.blit(infinite_text, (10, 80))
            return

        spacing = HEART_SIZE + 6
        for i in range(max(0, self.lives)):
            x = 10 + i * spacing
            surface.blit(self.heart_image, (x, 80))

    def _draw_menu(self, surface):
        title_text = self.title_font.render(GAME_TITLE, True, TEXT_COLOR)
        surface.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 3 - 60))

        if self.menu_stage == "MODE":
            mode_label = self.font.render("Select Mode:", True, TEXT_COLOR)
            surface.blit(mode_label, (WIDTH // 2 - mode_label.get_width() // 2, HEIGHT // 2 - 20))
            
            # Ensure the variables exist just in case draw triggers before events
            if not hasattr(self, 'mode_options'):
                self.mode_options = ["Tutorial", "Classic", "Infinite", "Leaderboard"]
                self.mode_idx = 1
                
            # Show arrows and the current mode choice
            current_mode = self.mode_options[self.mode_idx]
            mode_str = f"<  {current_mode}  >"
            mode_text = self.font.render(mode_str, True, (255, 215, 0))
            surface.blit(mode_text, (WIDTH // 2 - mode_text.get_width() // 2, HEIGHT // 2 + 20))
            
            # Mode Explanations
            if current_mode == "Tutorial":
                desc = "Learn the controls in a safe zone."
            elif current_mode == "Classic":
                desc = "Standard game with 3 lives."
            elif current_mode == "Infinite":
                desc = "One life. Climb forever."
            elif current_mode == "Leaderboard":
                desc = "View the global top 10 scores."
            else:
                desc = ""
                
            desc_text = self.font.render(desc, True, (200, 200, 220))
            surface.blit(desc_text, (WIDTH // 2 - desc_text.get_width() // 2, HEIGHT // 2 + 55))
            
            confirm_text = self.font.render("Press A+D to Confirm", True, (150, 150, 150))
            surface.blit(confirm_text, (WIDTH // 2 - confirm_text.get_width() // 2, HEIGHT // 2 + 95))
            
        elif self.menu_stage == "DIFFICULTY":
            diff_label = self.font.render("Select Difficulty:", True, TEXT_COLOR)
            surface.blit(diff_label, (WIDTH // 2 - diff_label.get_width() // 2, HEIGHT // 2 - 20))
            
            # Show arrows and the current difficulty choice
            current_diff = self.difficulty_levels[self.diff_idx]
            diff_str = f"<  {current_diff}  >"
            diff_text = self.font.render(diff_str, True, (255, 215, 0))
            surface.blit(diff_text, (WIDTH // 2 - diff_text.get_width() // 2, HEIGHT // 2 + 20))
            
            # --- NEW: Difficulty Explanations ---
            if current_diff == "Easy":
                desc = "Wide gaps and a forgiving pace."
            elif current_diff == "Normal":
                desc = "The standard arcade experience."
            elif current_diff == "Hard":
                desc = "Narrower paths and faster speed."
            elif current_diff == "Impossible":
                desc = "Brutally tight spacing. Good luck."
            else:
                desc = ""
                
            # Render the description in a slightly dimmer/different color (light blue/grey)
            desc_text = self.font.render(desc, True, (200, 200, 220))
            surface.blit(desc_text, (WIDTH // 2 - desc_text.get_width() // 2, HEIGHT // 2 + 55))
            # ------------------------------------
            
            # Shifted down from +70 to +95 to make room for the description
            confirm_text = self.font.render("Press A+D/Space to Confirm", True, (150, 150, 150))
            surface.blit(confirm_text, (WIDTH // 2 - confirm_text.get_width() // 2, HEIGHT // 2 + 95))
        
        elif self.menu_stage == "LEADERBOARD":
            title_text = self.font.render("GLOBAL TOP 10", True, (255, 215, 0))
            surface.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 3 - 20))
            
            if getattr(self, 'fetching_scores', False):
                load_text = self.font.render("Fetching scores...", True, (200, 200, 200))
                surface.blit(load_text, (WIDTH // 2 - load_text.get_width() // 2, HEIGHT // 2))
            elif not getattr(self, 'top_scores', []):
                err_text = self.font.render("No scores found.", True, (255, 50, 50))
                surface.blit(err_text, (WIDTH // 2 - err_text.get_width() // 2, HEIGHT // 2))
            else:
                for i, record in enumerate(self.top_scores[:10]):
                    name = record.get("player_name", "???")
                    score = record.get("score", 0)
                    row_text = self.font.render(f"{i+1}. {name} ... {score}m", True, (255, 255, 255))
                    surface.blit(row_text, (WIDTH // 2 - row_text.get_width() // 2, HEIGHT // 3 + 30 + (i * 25)))
                    
            esc_text = self.font.render("Press Esc to Return", True, (150, 150, 150))
            surface.blit(esc_text, (WIDTH // 2 - esc_text.get_width() // 2, HEIGHT - 50))

    def _draw_game_over_input(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        
        prompt_text = self.font.render("ENTER 3 INITIALS", True, (255, 255, 255))
        surface.blit(prompt_text, (WIDTH // 2 - prompt_text.get_width() // 2, 200))
        
        initials_text = self.font.render(self.player_initials + "_", True, (255, 255, 0))
        surface.blit(initials_text, (WIDTH // 2 - initials_text.get_width() // 2, 300))
        
        score_text = self.font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        surface.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 400))

    # Helper method to trigger game over
    def _trigger_game_over(self):
        if not self.game_over:
            if self.lose_sound:
                self.lose_sound.play()
            if self.audio_initialized:
                pygame.mixer.music.stop()
            pygame.mixer.music.stop()
            self.game_over = True
            
            # Trigger the text input phase
            self.waiting_for_initials = True
            self.player_initials = ""

    def _unlock_audio(self):
        """Initializes mixer only after the user interacts with the page."""
        if self.audio_initialized:
            return
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            self.audio_initialized = True  # only after init succeeded

            def load_sound(filename, vol=0.5):
                try:
                    s = pygame.mixer.Sound(str(ASSETS_DIR / filename))
                    s.set_volume(vol)
                    return s
                except Exception as e:
                    print(f"Audio load skipped ({filename}): {e}")
                    return None

            self.crash_sound = load_sound("crash.wav", 0.2)
            self.lose_sound = load_sound("lose.wav", 0.4)
            self.coin_sound = load_sound("coin.wav", 0.15)
            self.menu_click = load_sound("menu_click.wav", 0.5)

            if self.pending_music:
                self._play_music(self.pending_music)
        except Exception as e:
            print(f"Mixer init failed in browser: {e}")

    def _play_music(self, filename):
        self.pending_music = filename
        if not getattr(self, "audio_initialized", False):
            return
        try:
            pygame.mixer.music.load(str(ASSETS_DIR / filename))
            pygame.mixer.music.set_volume(0.05)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"Music playback skipped ({filename}): {e}")


    async def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
            await asyncio.sleep(0)  # CRITICAL: This prevents the browser tab from freezing!
