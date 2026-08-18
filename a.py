import sys
import pygame

# Initialize Pygame
pygame.init()

# Set up the display window
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Draw Green Rectangle")

# Define colors
BACKGROUND_COLOR = (30, 30, 30)  # Dark gray
GREEN = (0, 255, 0)  # Pure Green

# Game Loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Fill background first so shapes are drawn on top
    screen.fill(BACKGROUND_COLOR)

    # Draw a filled green rectangle
    # Starts at X=100, Y=80, with Width=200 and Height=100
    pygame.draw.rect(screen, GREEN, (100, 80, 200, 100))

    # Update the display
    pygame.display.flip()

# Quit Pygame cleanly
pygame.quit()
sys.exit()
