# --- Configuration & Constants ---
WIDTH, HEIGHT = 400, 750
FPS = 60

# Colors
BG_COLOR = (20, 24, 34)
BALL_COLOR = (0, 255, 200)
OBSTACLE_COLOR = (255, 80, 80)
LAVA_COLOR = (255, 50, 0)
TEXT_COLOR = (255, 255, 255)
COIN_COLOR = (255, 215, 0)

# Ocean Background Theme
OCEAN_TOP_COLOR = (90, 180, 220)  # Sunlit shallow water near the surface
OCEAN_BOTTOM_COLOR = (5, 20, 55)  # Dark deep water
BUBBLE_COLOR = (210, 240, 255)
BUBBLE_COUNT = 28

# Obstacle creatures: size ranges scaled to roughly match their real-world proportions
OBSTACLE_CREATURES = [
    {"name": "crab", "image": "crab.png", "width": (38, 54), "height": (28, 39)},
    {"name": "pufferfish", "image": "pufferfish.png", "width": (36, 50), "height": (32, 44)},
    {"name": "commonFish", "image": "commonFish.png", "width": (55, 85), "height": (22, 34)},
    {"name": "shark", "image": "shark.png", "width": (95, 140), "height": (34, 48)},
    {"name": "whale", "image": "whale.png", "width": (140, 195), "height": (50, 70)},
]

# Physics & Gameplay
GRAVITY = 0.4
JUMP_Y = -9.0
JUMP_X = 6.0
MAX_FALL_SPEED = 12.0
BASE_SCROLL_SPEED = 2.0
COOLDOWN_FRAMES = 12  # Prevent holding the button to fly
SAFE_START_GAP = 180  # Clear space above the player's spawn so the first obstacle is never on top of them

# Player spin (frantic tumble while moving left/right, straightened by the UP jump)
SPIN_SPEED_DEGREES = 12  # Degrees rotated per frame while spinning (12 * 60fps = 720deg/s = 2 rotations/sec)

# Lives & Invincibility
STARTING_LIVES = 3
INVINCIBILITY_FRAMES = 90  # 1.5 seconds at 60 FPS of iframes after getting hit
FLICKER_INTERVAL = 6  # Toggle visibility every N frames while invincible

# Screen Shake
SHAKE_DURATION_FRAMES = 15  # How long the shake lasts after losing a heart
SHAKE_MAGNITUDE = 6  # Max pixel offset in any direction while shaking
