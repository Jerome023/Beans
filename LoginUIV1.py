import sqlite3
import hashlib
import pygame
import sys

# ------------------ Database Setup ------------------ #
DB_FILE = "appdata.db"

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS userdata (
        id INTEGER PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password CHAR(64) NOT NULL
    )
    """)
    conn.commit()
    conn.close()

# ------------------ Utility ------------------ #
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_login(username, password):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT password FROM userdata WHERE username = ?", (username,))
    result = cur.fetchone()
    conn.close()
    return result and result[0] == hash_password(password)

def try_register(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO userdata (username, password) VALUES (?, ?)", 
                    (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# ------------------ Pygame UI ------------------ #
pygame.init()
WIDTH, HEIGHT = 330, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Account System")
FONT = pygame.font.SysFont(None, 28)

# --- Components --- #
class InputBox:
    def __init__(self, x, y, w, h, password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = pygame.Color("gray")
        self.text = ""
        self.txt_surface = FONT.render(self.text, True, self.color)
        self.active = False
        self.password = password

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
            self.txt_surface = FONT.render(
                "*" * len(self.text) if self.password else self.text, True, pygame.Color("black")
            )

    def draw(self, screen):
        pygame.draw.rect(screen, pygame.Color("black"), self.rect, 2)
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+8))

class Button:
    def __init__(self, text, x, y, w, h, action=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.color = pygame.Color("green")

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=8)
        label = FONT.render(self.text, True, pygame.Color("white"))
        screen.blit(label, (self.rect.x + (self.rect.w-label.get_width())//2,
                            self.rect.y + (self.rect.h-label.get_height())//2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            if self.action:
                self.action()

# ------------------ Screens ------------------ #
current_user = None
current_screen = "home"
message = ""

def go_home():
    global current_screen, message
    current_screen = "home"
    message = ""

def go_login():
    global current_screen, login_user, login_pass
    current_screen = "login"
    login_user.text, login_pass.text = "", ""
    login_user.txt_surface = FONT.render("", True, pygame.Color("black"))
    login_pass.txt_surface = FONT.render("", True, pygame.Color("black"))

def go_register():
    global current_screen, reg_user, reg_pass, reg_conf
    current_screen = "register"
    for box in [reg_user, reg_pass, reg_conf]:
        box.text = ""
        box.txt_surface = FONT.render("", True, pygame.Color("black"))

def go_account():
    global current_screen
    current_screen = "account"

def do_login():
    global current_user, message
    if validate_login(login_user.text, login_pass.text):
        current_user = login_user.text
        go_home()
    else:
        message = "Invalid login"

def do_register():
    global current_user, message
    if reg_pass.text != reg_conf.text:
        message = "Passwords do not match"
        return
    if try_register(reg_user.text, reg_pass.text):
        current_user = reg_user.text
        go_home()
    else:
        message = "Username already exists"

def do_logout():
    global current_user
    current_user = None
    go_home()

# Input Boxes
login_user = InputBox(45, 200, 240, 40)
login_pass = InputBox(45, 260, 240, 40, password=True)
reg_user = InputBox(45, 180, 240, 40)
reg_pass = InputBox(45, 240, 240, 40, password=True)
reg_conf = InputBox(45, 300, 240, 40, password=True)

# ------------------ Main Loop ------------------ #
setup_database()
running = True
while running:
    screen.fill(pygame.Color("white"))

    # Build buttons first
    if current_screen == "home":
        if current_user:
            buttons = [Button(f"{current_user}'s Account", 65, 200, 200, 50, go_account)]
        else:
            buttons = [Button("Login", 65, 200, 200, 50, go_login)]

    elif current_screen == "login":
        buttons = [
            Button("Log in", 65, 340, 200, 50, do_login),
            Button("Register", 65, 410, 200, 50, go_register),
            Button("Back", 65, 480, 200, 50, go_home)
        ]

    elif current_screen == "register":
        buttons = [
            Button("Register", 65, 370, 200, 50, do_register),
            Button("Back", 65, 440, 200, 50, go_login)
        ]

    elif current_screen == "account":
        buttons = [
            Button("Logout", 65, 250, 200, 50, do_logout),
            Button("Back", 65, 320, 200, 50, go_home)
        ]

    # Handle events (buttons now exist!)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if current_screen == "login":
            login_user.handle_event(event)
            login_pass.handle_event(event)
        elif current_screen == "register":
            reg_user.handle_event(event)
            reg_pass.handle_event(event)
            reg_conf.handle_event(event)

        for btn in buttons:
            btn.handle_event(event)

    # --- Draw Screens --- #
    if current_screen == "home":
        label = FONT.render("Home Screen", True, pygame.Color("black"))
        screen.blit(label, (WIDTH//2 - label.get_width()//2, 80))

    elif current_screen == "login":
        label = FONT.render("Login", True, pygame.Color("black"))
        screen.blit(label, (WIDTH//2 - label.get_width()//2, 100))
        login_user.draw(screen)
        login_pass.draw(screen)

    elif current_screen == "register":
        label = FONT.render("Register", True, pygame.Color("black"))
        screen.blit(label, (WIDTH//2 - label.get_width()//2, 100))
        reg_user.draw(screen)
        reg_pass.draw(screen)
        reg_conf.draw(screen)

    elif current_screen == "account":
        label = FONT.render(f"Account: {current_user}", True, pygame.Color("black"))
        screen.blit(label, (WIDTH//2 - label.get_width()//2, 150))

    # Draw buttons (after UI)
    for btn in buttons:
        btn.draw(screen)

    # Draw message if any
    if message:
        msg_label = FONT.render(message, True, pygame.Color("red"))
        screen.blit(msg_label, (WIDTH//2 - msg_label.get_width()//2, HEIGHT-60))

    pygame.display.flip()

pygame.quit()
sys.exit()
