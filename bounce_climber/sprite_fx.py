import pygame


def add_outline(image, thickness=2, color=(12, 14, 25, 255)):
    """Draw the sprite's silhouette offset in a ring around it for a crisp, readable outline."""
    mask = pygame.mask.from_surface(image)
    silhouette = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))

    w, h = image.get_size()
    outlined = pygame.Surface((w + thickness * 2, h + thickness * 2), pygame.SRCALPHA)
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx * dx + dy * dy <= thickness * thickness + 1 and (dx, dy) != (0, 0):
                outlined.blit(silhouette, (thickness + dx, thickness + dy))
    outlined.blit(image, (thickness, thickness))
    return outlined
