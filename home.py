import pygame
import sys

# Initialize pygame
pygame.init()

# Screen setup
WIDTH, HEIGHT = 400, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gardening Assistant - Home")

# Fonts
font = pygame.font.SysFont("arial", 24)
small_font = pygame.font.SysFont("arial", 18)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (50, 200, 50)
LIGHT_GRAY = (230, 230, 230)
BLUE = (100, 150, 250)

# Example streak counter
streak_count = 15

# Input box for AI Mascot
input_box = pygame.Rect(50, 350, 300, 40)
input_active = False
user_text = ""

# Main loop
clock = pygame.time.Clock()
running = True

while running:
    screen.fill(WHITE)

    # --- Top streak bar ---
    streak_text = font.render(f"Streak: {streak_count} 🔥", True, BLACK)
    screen.blit(streak_text, (20, 20))

    # --- Plant buttons ---
    plant1 = pygame.Rect(50, 80, 300, 50)
    plant2 = pygame.Rect(50, 150, 300, 50)
    pygame.draw.rect(screen, GREEN, plant1, border_radius=10)
    pygame.draw.rect(screen, GREEN, plant2, border_radius=10)

    plant1_text = small_font.render("Plant 1: [Species Name]", True, WHITE)
    plant2_text = small_font.render("Plant 2: [Species Name]", True, WHITE)
    screen.blit(plant1_text, (plant1.x + 20, plant1.y + 15))
    screen.blit(plant2_text, (plant2.x + 20, plant2.y + 15))

    # --- AI Mascot area ---
    mascot_text = small_font.render("AI Mascot Assistant", True, BLACK)
    screen.blit(mascot_text, (120, 280))

    pygame.draw.circle(screen, (255, 200, 0), (200, 250), 40)  # mascot face placeholder
    pygame.draw.rect(screen, BLACK, input_box, 2)
    input_text = small_font.render(user_text if user_text else "Ask me Anything...", True, BLACK)
    screen.blit(input_text, (input_box.x + 10, input_box.y + 10))

    # --- Bottom navigation bar ---
    nav_height = 60
    pygame.draw.rect(screen, LIGHT_GRAY, (0, HEIGHT - nav_height, WIDTH, nav_height))

    # Three nav buttons (placeholders: Profile, Home, Friends)
    pygame.draw.circle(screen, BLUE, (70, HEIGHT - 30), 20)   # Profile
    pygame.draw.circle(screen, BLUE, (200, HEIGHT - 30), 20)  # Home
    pygame.draw.circle(screen, BLUE, (330, HEIGHT - 30), 20)  # Friends

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if input_box.collidepoint(event.pos):
                input_active = True
            else:
                input_active = False

        if event.type == pygame.KEYDOWN and input_active:
            if event.key == pygame.K_BACKSPACE:
                user_text = user_text[:-1]
            elif event.key == pygame.K_RETURN:
                print("User asked mascot:", user_text)  # Placeholder for AI response
                user_text = ""
            else:
                user_text += event.unicode

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
