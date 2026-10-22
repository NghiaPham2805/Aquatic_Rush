import traceback
import asyncio
import pygame

async def main():
    # Initialize Pygame and display early
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Bounce Game")
    
    try:
        # Move the import INSIDE the try block so traceback shows on screen
        from bounce_climber.game import Game
        
        game = Game()
        await game.run()
        
    except Exception:
        # This will catch missing modules or path errors and paint them red on canvas
        err_msg = traceback.format_exc()
        screen.fill((50, 0, 0))
        
        # Use Font instead of SysFont (SysFont is unreliable in the browser)
        font = pygame.font.Font(None, 24)
        lines = err_msg.split("\n")
        y = 20
        for line in lines:
            txt = font.render(line, True, (255, 200, 200))
            screen.blit(txt, (20, y))
            y += 25
            
        pygame.display.flip()
        
        # Keep the error on screen asynchronously
        while True:
            await asyncio.sleep(0.1)

asyncio.run(main())