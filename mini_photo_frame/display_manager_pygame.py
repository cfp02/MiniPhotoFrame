import pygame
import os
from display_manager import get_caption  # reuse your caption logic
from PIL import Image
import time

def show_photo(image_path, display_interval, rotation=0):
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    screen_width, screen_height = screen.get_size()

    # Load and optionally rotate image
    img = Image.open(image_path)
    if rotation:
        img = img.rotate(-rotation, expand=True)
    img_width, img_height = img.size

    # Scale image to fit screen
    img_ratio = img_width / img_height
    screen_ratio = screen_width / screen_height
    if img_ratio > screen_ratio:
        new_width = screen_width
        new_height = int(screen_width / img_ratio)
    else:
        new_height = screen_height
        new_width = int(screen_height * img_ratio)

    img = img.resize((new_width, new_height))
    img = pygame.image.fromstring(img.tobytes(), img.size, img.mode)

    # Fill screen and blit image centered
    screen.fill((0, 0, 0))
    x_offset = (screen_width - new_width) // 2
    y_offset = (screen_height - new_height) // 2
    screen.blit(img, (x_offset, y_offset))

    # Draw caption
    caption = get_caption(image_path)
    font = pygame.font.SysFont('Arial', 28)
    text = font.render(caption, True, (255, 255, 255))
    text_rect = text.get_rect(center=(screen_width // 2, screen_height - 30))
    outline = font.render(caption, True, (0, 0, 0))
    outline_rect = outline.get_rect(center=(screen_width // 2, screen_height - 30))
    screen.blit(outline, outline_rect.move(2, 2))
    screen.blit(text, text_rect)

    pygame.display.flip()

    # Timer and key loop
    start_time = time.time()
    while time.time() - start_time < display_interval:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return "exit"
                elif event.key == pygame.K_r:
                    pygame.quit()
                    return "reshuffle"
                elif event.key == pygame.K_n:
                    pygame.quit()
                    return "new"
                elif event.key == pygame.K_b:
                    pygame.quit()
                    return "back"
                else:
                    pygame.quit()
                    return "next"
        time.sleep(0.1)

    pygame.quit()
    return "next"