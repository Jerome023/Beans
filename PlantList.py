import pygame

# Initialize Pygame
pygame.init()

# Window size
screen_width = 360
screen_height = 650
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Plant Lists")
colour = (250, 250, 250)

# Main loop
run = True
while run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

screen.fill(colour)

# Quit Pygame
pygame.quit()