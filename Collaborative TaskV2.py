import pygame
import requests
import threading
import json
import os
import tkinter as tk
from tkinter import filedialog

# Ollama setup
MODEL_NAME = "llama3"  # Model

def query_ollama(prompt: str, model: str = MODEL_NAME) -> str:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt},
            timeout=60,
            stream=True
        )
        if response.status_code != 200:
            return f"Error {response.status_code}: {response.text[:200]}"
        output = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = line.decode("utf-8")
                    if '"response":' in data:
                        part = data.split('"response":"')[1].split('"')[0]
                        output += part
                except Exception:
                    pass
        return output.strip() if output else "No response."
    except Exception as e:
        return f"Ollama error: {e}"

# Persistence 
PLANTS_FILE = "plants.json"
plants = []


def load_plants():
    global plants
    if os.path.exists(PLANTS_FILE):
        with open(PLANTS_FILE, "r") as f:
            plants = json.load(f)
    else:
        plants = []

    # Ensure all plants have an "archived" field
    for p in plants:
        if "archived" not in p:
            p["archived"] = False


def save_plants():
    with open(PLANTS_FILE, "w") as f:
        json.dump(plants, f, indent=2)

# Pygame Setup
pygame.init()
screen_width, screen_height = 360, 650
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Plant Lists")
colour = (250, 250, 250)
font = pygame.font.SysFont(None, 20)

ai_response = "I'm Derek the Dandelion, I am here to help in all your gardening needs."
user_input = ""
input_active = False
scroll_y = 0
viewing_archives = False  # Toggle between active and archived plants

# Button Class
class Button:
    def __init__(self, x, y, w, h, text, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.color = (60, 217, 28)
        self.hover_color = (39, 115, 24)
        self.text_color = (250, 250, 250)

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.rect(surface, self.hover_color if self.rect.collidepoint(mouse_pos) else self.color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, width=3, border_radius=8)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.callback()

# Add/Edit Plant
def open_add_plant_window(prefill=None, index=None):
    global viewing_archives
    new_screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Add Plant")

    # Field values
    name = prefill["name"] if prefill else ""
    age = prefill["age"] if prefill else ""
    shade = prefill["shade"] if prefill else False
    notes = prefill["notes"] if prefill else ""
    photo_path = prefill["photo"] if prefill else None
    archived = prefill["archived"] if prefill else False

    input_field = None
    running = True

    def pick_photo():
        nonlocal photo_path
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if file_path:
            photo_path = file_path

    def save_or_add():
        nonlocal running
        plant_data = {"name": name, "age": age, "shade": shade, "notes": notes, "photo": photo_path, "archived": archived}
        if index is None:
            plants.append(plant_data)
        else:
            plants[index] = plant_data
        save_plants()
        running = False

    def delete_plant():
        nonlocal running
        if index is not None:
            plants.pop(index)
            save_plants()
        running = False

    def archive_plant():
        nonlocal running, archived
        if index is not None:
            plants[index]["archived"] = True
            save_plants()
        running = False

    def unarchive_plant():
        nonlocal running, archived
        if index is not None:
            plants[index]["archived"] = False
            save_plants()
        running = False

    # Rects
    rects = {
        "name": pygame.Rect(100, 30, 200, 30),
        "age": pygame.Rect(100, 90, 200, 30),
        "notes": pygame.Rect(30, 310, 300, 150),
        "shade": pygame.Rect(100, 150, 80, 30),
        "photo": pygame.Rect(30, 220, 120, 30),
        "save": pygame.Rect(30, 500, 120, 40),
        "delete": pygame.Rect(180, 500, 120, 40),
        "archive": pygame.Rect(30, 560, 120, 40),
        "unarchive": pygame.Rect(180, 560, 120, 40)
    }

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if rects["name"].collidepoint(mx, my): input_field = "name"
                elif rects["age"].collidepoint(mx, my): input_field = "age"
                elif rects["notes"].collidepoint(mx, my): input_field = "notes"
                else: input_field = None
                if rects["shade"].collidepoint(mx, my): shade = not shade
                if rects["photo"].collidepoint(mx, my): pick_photo()
                if rects["save"].collidepoint(mx, my): save_or_add()
                if index is not None and rects["delete"].collidepoint(mx, my): delete_plant()
                if index is not None and rects["archive"].collidepoint(mx, my): archive_plant()
                if index is not None and rects["unarchive"].collidepoint(mx, my): unarchive_plant()
            elif event.type == pygame.KEYDOWN and input_field:
                if event.key == pygame.K_TAB:
                    input_field = {"name":"age","age":"notes","notes":"name"}[input_field]
                elif event.key == pygame.K_RETURN:
                    save_or_add()
                elif event.key == pygame.K_BACKSPACE:
                    if input_field == "name": name = name[:-1]
                    elif input_field == "age": age = age[:-1]
                    elif input_field == "notes": notes = notes[:-1]
                else:
                    if input_field == "name": name += event.unicode
                    elif input_field == "age": age += event.unicode
                    elif input_field == "notes": notes += event.unicode

        # Draw 
        new_screen.fill((240, 240, 240))
        new_screen.blit(font.render("Name:", True, (0,0,0)), (30,30))
        new_screen.blit(font.render("Age:", True, (0,0,0)), (30,90))
        new_screen.blit(font.render("Shade:", True, (0,0,0)), (30,150))
        new_screen.blit(font.render("Notes:", True, (0,0,0)), (30,280))

        pygame.draw.rect(new_screen, (255,255,255), rects["name"])
        new_screen.blit(font.render(name, True, (0,0,0)), (rects["name"].x + 5, rects["name"].y + 5))
        pygame.draw.rect(new_screen, (255,255,255), rects["age"])
        new_screen.blit(font.render(age, True, (0,0,0)), (rects["age"].x + 5, rects["age"].y + 5))
        pygame.draw.rect(new_screen, (200,200,200) if not shade else (60,217,28), rects["shade"])
        new_screen.blit(font.render("Shade" if shade else "Sun", True, (0,0,0)), (rects["shade"].x + 5, rects["shade"].y + 5))
        pygame.draw.rect(new_screen, (255,255,255), rects["notes"])
        new_screen.blit(font.render(notes, True, (0,0,0)), (rects["notes"].x + 5, rects["notes"].y + 5))
        pygame.draw.rect(new_screen, (180,180,255), rects["photo"])
        new_screen.blit(font.render("Add Photo", True, (0,0,0)), (rects["photo"].x + 10, rects["photo"].y + 5))
        if photo_path:
            new_screen.blit(font.render(os.path.basename(photo_path), True, (0,0,0)), (rects["photo"].x + 130, rects["photo"].y + 5))
        pygame.draw.rect(new_screen, (100,255,100), rects["save"])
        new_screen.blit(font.render("Save Changes" if index is not None else "Add to List", True, (0,0,0)), (rects["save"].x + 5, rects["save"].y + 10))
        if index is not None:
            pygame.draw.rect(new_screen, (255,100,100), rects["delete"])
            new_screen.blit(font.render("Delete Plant", True, (0,0,0)), (rects["delete"].x + 5, rects["delete"].y + 10))
            pygame.draw.rect(new_screen, (255,200,100), rects["archive"])
            new_screen.blit(font.render("Archive", True, (0,0,0)), (rects["archive"].x + 5, rects["archive"].y + 10))
            pygame.draw.rect(new_screen, (200,255,100), rects["unarchive"])
            new_screen.blit(font.render("Unarchive", True, (0,0,0)), (rects["unarchive"].x + 5, rects["unarchive"].y + 10))

        pygame.display.flip()

# AI Action
def gardening_tip_action():
    global ai_response, user_input
    if not user_input.strip():
        ai_response = "Please type a question first."
        return
    ai_response = "Thinking..."
    def fetch_response():
        global ai_response
        ai_response = query_ollama(user_input)
    threading.Thread(target=fetch_response, daemon=True).start()

# Load Images
plant_img = pygame.image.load("Plant.png")
plant_img = pygame.transform.scale(plant_img, (100, 100)).convert_alpha()

speechbubble_img = pygame.image.load("SpeechBubble.png")
speechbubble_img = pygame.transform.scale(speechbubble_img, (75, 75)).convert_alpha()

# Main Loop 
load_plants()

buttons = [
    Button(120, 10, 120, 40, "Add Plant", lambda: open_add_plant_window()),
    Button(30, 400, 300, 50, "Ask Derek the Dandelion", gardening_tip_action),
    Button(120, 60, 120, 30, "View Archives", lambda: toggle_archives())
]

def toggle_archives():
    global viewing_archives
    viewing_archives = not viewing_archives

plant_button_start_y = 110

run = True
while run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            # AI input box
            input_box_rect = pygame.Rect(20, 360, 320, 30)
            if input_box_rect.collidepoint(mx, my):
                input_active = True
            else:
                input_active = False
            # Plant list buttons
            for i, plant in enumerate(plants):
                if viewing_archives and not plant["archived"]:
                    continue
                if not viewing_archives and plant["archived"]:
                    continue
                btn_rect = pygame.Rect(30, plant_button_start_y + i * 50, 200, 40)
                if btn_rect.collidepoint(mx, my):
                    open_add_plant_window(prefill=plant, index=i)
        elif event.type == pygame.KEYDOWN and input_active:
            if event.key == pygame.K_RETURN:
                gardening_tip_action()
            elif event.key == pygame.K_BACKSPACE:
                user_input = user_input[:-1]
            else:
                user_input += event.unicode
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: scroll_y += 20
            elif event.key == pygame.K_DOWN: scroll_y -= 20
        for button in buttons:
            button.handle_event(event)

    # Draw Buttons
    screen.fill(colour)
    for button in buttons:
        button.draw(screen)

    # Draw Images 
    screen.blit(plant_img, (220, 250))
    screen.blit(speechbubble_img, (150, 225))

    # Plant list
    y_offset = 0
    for i, plant in enumerate(plants):
        if viewing_archives and not plant["archived"]:
            continue
        if not viewing_archives and plant["archived"]:
            continue
        rect = pygame.Rect(30, plant_button_start_y + y_offset * 50, 200, 40)
        pygame.draw.rect(screen, (180, 220, 180), rect, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), rect, 2, border_radius=6)
        screen.blit(font.render(plant["name"] + (" (A)" if plant["archived"] else ""), True, (0, 0, 0)), (rect.x + 10, rect.y + 10))
        y_offset += 1

    # AI input box (moved up)
    input_box = pygame.Rect(20, 360, 320, 30)
    pygame.draw.rect(screen, (255, 255, 255), input_box, border_radius=6)
    pygame.draw.rect(screen, (0, 0, 0), input_box, 2, border_radius=6)
    screen.blit(font.render(user_input, True, (0, 0, 0)), (input_box.x + 5, input_box.y + 5))

    # AI response box (moved up)
    if ai_response:
        box_rect = pygame.Rect(20, 470, 320, 100)
        pygame.draw.rect(screen, (230, 230, 230), box_rect, border_radius=8)
        pygame.draw.rect(screen, (0, 0, 0), box_rect, 2, border_radius=8)
        clip_rect = box_rect.inflate(-10, -10)
        screen.set_clip(clip_rect)
        words, line, lines = ai_response.split(), "", []
        for word in words:
            test_line = line + word + " "
            if font.render(test_line, True, (0, 0, 0)).get_width() > clip_rect.width:
                lines.append(line)
                line = word + " "
            else:
                line = test_line
        if line: lines.append(line)
        y = clip_rect.y + scroll_y
        for line in lines:
            screen.blit(font.render(line, True, (0, 0, 0)), (clip_rect.x, y))
            y += 20
        screen.set_clip(None)

    pygame.display.flip()

pygame.quit()
