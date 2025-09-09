import pygame

pygame.init()
screen_width, screen_height = 360, 650
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Editable Checklist Page")
font = pygame.font.SysFont("Arial", 20)
small_font = pygame.font.SysFont("Arial", 16)

# --- UI Rectangles ---
login_button = pygame.Rect(100, 40, 160, 40)
checklist_area = pygame.Rect(20, 100, 320, 400)
dock_height = 70
dock_area = pygame.Rect(0, screen_height - dock_height, screen_width, dock_height)

dock_buttons = [
    pygame.Rect(30, screen_height - dock_height + 15, 40, 40),   # Plant page
    pygame.Rect(160, screen_height - dock_height + 15, 40, 40),  # Checklist page (current)
    pygame.Rect(290, screen_height - dock_height + 15, 40, 40),  # Profile/settings page
]

# --- Checklist items ---
checklist_items = [
    {"text": "Water plants", "checked": False},
    {"text": "Fertilize soil", "checked": False},
    {"text": "Prune dead leaves", "checked": False},
]

checkbox_size = 22
item_height = 45
editing_index = None  # which item is being edited
text_input = ""

# --- Main Loop ---
run = True
while run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if login_button.collidepoint(event.pos):
                print("Login button pressed (hook up externally)")

            # Add new item if click below last task
            add_button_rect = pygame.Rect(checklist_area.x + 10,
                                          checklist_area.y + 10 + len(checklist_items) * item_height,
                                          120, 30)
            if add_button_rect.collidepoint(event.pos):
                checklist_items.append({"text": "New Task", "checked": False})
                continue

            # Detect clicks on tasks
            for i, item in enumerate(checklist_items):
                y = checklist_area.y + 10 + i * item_height
                box_rect = pygame.Rect(checklist_area.x + 10, y, checkbox_size, checkbox_size)
                text_rect = pygame.Rect(box_rect.right + 10, y, 200, checkbox_size)
                delete_rect = pygame.Rect(checklist_area.right - 35, y, 25, 25)

                if box_rect.collidepoint(event.pos):
                    item["checked"] = not item["checked"]

                elif text_rect.collidepoint(event.pos):
                    editing_index = i
                    text_input = item["text"]

                elif delete_rect.collidepoint(event.pos):
                    checklist_items.pop(i)
                    if editing_index == i:
                        editing_index = None
                    break

            # Dock clicks
            for i, btn in enumerate(dock_buttons):
                if btn.collidepoint(event.pos):
                    print(f"Switch to page {i}")  # Replace with real navigation

        elif event.type == pygame.KEYDOWN:
            if editing_index is not None:
                if event.key == pygame.K_RETURN:
                    checklist_items[editing_index]["text"] = text_input.strip() or "Untitled Task"
                    editing_index = None
                elif event.key == pygame.K_BACKSPACE:
                    text_input = text_input[:-1]
                else:
                    text_input += event.unicode

    # --- Draw ---
    screen.fill((245, 245, 245))

    # Login button
    pygame.draw.rect(screen, (150, 200, 255), login_button, border_radius=10)
    pygame.draw.rect(screen, (0, 0, 0), login_button, 2, border_radius=10)
    screen.blit(font.render("Login", True, (0, 0, 0)),
                (login_button.x + 45, login_button.y + 10))

    # Checklist area
    pygame.draw.rect(screen, (255, 255, 255), checklist_area, border_radius=8)
    pygame.draw.rect(screen, (0, 0, 0), checklist_area, 2, border_radius=8)
    screen.blit(font.render("Checklist", True, (0, 0, 0)),
                (checklist_area.x + 5, checklist_area.y - 25))

    # Render tasks
    for i, item in enumerate(checklist_items):
        y = checklist_area.y + 10 + i * item_height
        box_rect = pygame.Rect(checklist_area.x + 10, y, checkbox_size, checkbox_size)
        delete_rect = pygame.Rect(checklist_area.right - 35, y, 25, 25)

        # Background highlight if editing
        if i == editing_index:
            pygame.draw.rect(screen, (220, 240, 255),
                             (box_rect.right + 8, y, 220, checkbox_size))

        # Checkbox
        pygame.draw.rect(screen, (255, 255, 255), box_rect, border_radius=4)
        pygame.draw.rect(screen, (0, 0, 0), box_rect, 2, border_radius=4)
        if item["checked"]:
            pygame.draw.line(screen, (0, 150, 0), (box_rect.x + 4, box_rect.y + 12),
                             (box_rect.x + 9, box_rect.y + 18), 2)
            pygame.draw.line(screen, (0, 150, 0), (box_rect.x + 9, box_rect.y + 18),
                             (box_rect.x + 18, box_rect.y + 4), 2)

        # Task text
        text_surface = font.render(text_input if i == editing_index else item["text"], True, (0, 0, 0))
        screen.blit(text_surface, (box_rect.right + 12, y))

        # Delete button
        pygame.draw.rect(screen, (255, 100, 100), delete_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), delete_rect, 2, border_radius=6)
        screen.blit(small_font.render("X", True, (0, 0, 0)),
                    (delete_rect.x + 7, delete_rect.y + 4))

    # Add new task button
    add_button_rect = pygame.Rect(checklist_area.x + 10,
                                  checklist_area.y + 10 + len(checklist_items) * item_height,
                                  120, 30)
    pygame.draw.rect(screen, (100, 220, 100), add_button_rect, border_radius=6)
    pygame.draw.rect(screen, (0, 0, 0), add_button_rect, 2, border_radius=6)
    screen.blit(font.render("+ Add Task", True, (0, 0, 0)),
                (add_button_rect.x + 10, add_button_rect.y + 5))

    # Dock
    pygame.draw.rect(screen, (220, 220, 220), dock_area)
    pygame.draw.line(screen, (0, 0, 0),
                     (0, dock_area.y),
                     (screen_width, dock_area.y), 2)

    for i, btn in enumerate(dock_buttons):
        pygame.draw.rect(screen, (200, 200, 200), btn, border_radius=8)
        pygame.draw.rect(screen, (0, 0, 0), btn, 2, border_radius=8)
        screen.blit(font.render(str(i+1), True, (0, 0, 0)),
                    (btn.x + 10, btn.y + 10))

    pygame.display.flip()

pygame.quit()
