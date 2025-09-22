import sqlite3
import hashlib
import pygame
import sys
import requests
import threading
import json
import os
import tkinter as tk
from tkinter import filedialog

# Database
DB_FILE = "appdata.db"
PLANTS_JSON = "plants.json"

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS userdata(
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS friends(
        user1 TEXT NOT NULL, user2 TEXT NOT NULL,
        UNIQUE(user1, user2)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS requests(
        sender TEXT, receiver TEXT,
        UNIQUE(sender, receiver)
    )""")
    # Plants table
    cur.execute("""CREATE TABLE IF NOT EXISTS plants(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age TEXT,
        shade INTEGER,
        notes TEXT,
        photo TEXT,
        archived INTEGER DEFAULT 0,
        source_json INTEGER DEFAULT 0,
        UNIQUE(name, notes) -- naive uniqueness to avoid duplicates from import
    )""")
    conn.commit()
    conn.close()

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def validate_login(u, p):
    c=sqlite3.connect(DB_FILE); cur=c.cursor()
    cur.execute("SELECT password FROM userdata WHERE username=?",(u,))
    r=cur.fetchone(); c.close()
    return r and r[0]==hash_pw(p)

def try_register(u, p):
    try:
        c=sqlite3.connect(DB_FILE); cur=c.cursor()
        cur.execute("INSERT INTO userdata(username,password) VALUES(?,?)",(u,hash_pw(p)))
        c.commit(); c.close(); return True
    except: return False

def get_friends(user):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT user2 FROM friends WHERE user1=? 
        UNION 
        SELECT user1 FROM friends WHERE user2=?
    """, (user, user))
    rows = [row[0] for row in cur.fetchall()]
    conn.close()
    return rows

def add_friend(user1, user2):
    if user1 == user2:
        return False
    a, b = sorted([user1, user2])
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO friends (user1, user2) VALUES (?, ?)", (a, b))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def send_request(sender, receiver):
    if sender==receiver: return False
    c=sqlite3.connect(DB_FILE); cur=c.cursor()
    try:
        cur.execute("INSERT INTO requests VALUES(?,?)",(sender,receiver))
        c.commit(); c.close(); return True
    except: c.close(); return False

def accept_request(sender, receiver):
    c = sqlite3.connect(DB_FILE); cur = c.cursor()
    cur.execute("DELETE FROM requests WHERE sender=? AND receiver=?", (sender, receiver))
    a, b = sorted([sender, receiver])
    cur.execute("INSERT OR IGNORE INTO friends VALUES(?,?)", (a, b))
    c.commit(); c.close()


def decline_request(sender, receiver):
    c=sqlite3.connect(DB_FILE); cur=c.cursor()
    cur.execute("DELETE FROM requests WHERE sender=? AND receiver=?",(sender,receiver))
    c.commit(); c.close()

def cancel_request(sender, receiver):
    c=sqlite3.connect(DB_FILE); cur=c.cursor()
    cur.execute("DELETE FROM requests WHERE sender=? AND receiver=?",(sender,receiver))
    c.commit(); c.close()

def get_incoming_requests(user):
    c=sqlite3.connect(DB_FILE); cur=c.cursor()
    cur.execute("SELECT sender FROM requests WHERE receiver=?",(user,))
    rows=[r[0] for r in cur.fetchall()]
    c.close(); return rows

def get_outgoing_requests(user):
    c=sqlite3.connect(DB_FILE); cur=c.cursor()
    cur.execute("SELECT receiver FROM requests WHERE sender=?",(user,))
    rows=[r[0] for r in cur.fetchall()]
    c.close(); return rows

def remove_friend(u1,u2):
    c=sqlite3.connect(DB_FILE); cur=c.cursor()
    cur.execute("DELETE FROM friends WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)",(u1,u2,u2,u1))
    c.commit(); c.close()

# Ollama (AI)
MODEL_NAME = "llama3"

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

# Plants persistence

# Plants in-memory list
plants = []

def load_plants_from_json():
    global plants
    if os.path.exists(PLANTS_JSON):
        with open(PLANTS_JSON, "r") as f:
            try:
                plants = json.load(f)
            except Exception:
                plants = []
    else:
        plants = []
    # ensure fields
    for p in plants:
        if "archived" not in p: p["archived"] = False
        if "photo" not in p: p["photo"] = None

def save_plants_to_json():
    with open(PLANTS_JSON, "w") as f:
        json.dump(plants, f, indent=2)

def import_json_plants_to_db():
    # Insert plants from JSON into DB if not already present
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    for p in plants:
        try:
            cur.execute("INSERT OR IGNORE INTO plants(name,age,shade,notes,photo,archived,source_json) VALUES(?,?,?,?,?,?,1)",
                        (p.get('name'), p.get('age'), 1 if p.get('shade') else 0, p.get('notes'), p.get('photo'), 1 if p.get('archived') else 0))
        except Exception:
            pass
    conn.commit(); conn.close()

def refresh_plants_from_db():
    global plants
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id,name,age,shade,notes,photo,archived FROM plants ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    # convert to dict list for UI convenience
    plants = []
    for r in rows:
        plants.append({
            'id': r[0], 'name': r[1] or "", 'age': r[2] or "", 'shade': bool(r[3]), 'notes': r[4] or "", 'photo': r[5], 'archived': bool(r[6])
        })

def save_plant_to_db(plant, plant_id=None):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if plant_id is None:
        cur.execute("INSERT INTO plants(name,age,shade,notes,photo,archived,source_json) VALUES(?,?,?,?,?,?,0)",
                    (plant.get('name'), plant.get('age'), 1 if plant.get('shade') else 0, plant.get('notes'), plant.get('photo'), 1 if plant.get('archived') else 0))
    else:
        cur.execute("UPDATE plants SET name=?,age=?,shade=?,notes=?,photo=?,archived=?,source_json=0 WHERE id=?",
                    (plant.get('name'), plant.get('age'), 1 if plant.get('shade') else 0, plant.get('notes'), plant.get('photo'), 1 if plant.get('archived') else 0, plant_id))
    conn.commit(); conn.close()

def delete_plant_from_db(plant_id):
    conn = sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute("DELETE FROM plants WHERE id=?",(plant_id,))
    conn.commit(); conn.close()

# Pygame UI
pygame.init()
WIDTH, HEIGHT = 360, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
FONT = pygame.font.SysFont(None, 20)
SMLFONT = pygame.font.SysFont(None, 16)
checklist_area = pygame.Rect(20, 100, 320, 400)

class InputBox:
    def __init__(self,x,y,w,h,password=False):
        self.rect=pygame.Rect(x,y,w,h); self.text=""; self.active=False; self.password=password
        self.txt_surface=FONT.render("",True,pygame.Color("black"))
    def handle_event(self,e):
        if e.type==pygame.MOUSEBUTTONDOWN: self.active=self.rect.collidepoint(e.pos)
        if e.type==pygame.KEYDOWN and self.active:
            if e.key==pygame.K_BACKSPACE: self.text=self.text[:-1]
            elif e.key!=pygame.K_RETURN: self.text+=e.unicode
            self.txt_surface=FONT.render("*"*len(self.text) if self.password else self.text,True,pygame.Color("black"))
    def draw(self,sc): 
        pygame.draw.rect(sc,pygame.Color("black"),self.rect,2)
        sc.blit(self.txt_surface,(self.rect.x+5,self.rect.y+8))

class Button:
    def __init__(self,text,x,y,w,h,action=None,color=(0,128,0)):
        self.rect=pygame.Rect(x,y,w,h); self.text=text; self.action=action; self.color=color
    def draw(self,sc):
        pygame.draw.rect(sc,self.color,self.rect,border_radius=6)
        lab=FONT.render(self.text,True,pygame.Color("white"))
        sc.blit(lab,(self.rect.x+(self.rect.w-lab.get_width())//2,self.rect.y+(self.rect.h-lab.get_height())//2))
    def handle_event(self,e):
        if e.type==pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(e.pos):
            if self.action:self.action()

# Global State
setup_database()
current_screen="home"; current_user=None; message=""; login_warning=None; warning_timer=0
friend_page=0; pending_remove=None

# Checklist items
checklist_items = [
    {"text": "Water plants", "checked": False},
    {"text": "Fertilize soil", "checked": False},
    {"text": "Prune dead leaves", "checked": False},
]

checkbox_size = 22
item_height = 45
editing_index = None  # which item is being edited
text_input = ""

# Navigation
def go_home(): 
    global current_screen,message
    current_screen="home"; message=""
def go_login():
    global current_screen; current_screen="login"; login_user.text=login_pass.text=""; 
    login_user.txt_surface=login_pass.txt_surface=FONT.render("",True,pygame.Color("black"))
def go_register():
    global current_screen; current_screen="register"
    for b in [reg_user,reg_pass,reg_conf]: b.text=""; b.txt_surface=FONT.render("",True,pygame.Color("black"))
def go_account(): 
    global current_screen; current_screen="account"
def go_friends():
    global current_screen; current_screen="friends"
def go_add_friend(): 
    global current_screen; current_screen="friends_add"; add_box.text=""; add_box.txt_surface=FONT.render("",True,pygame.Color("black"))
def go_remove_friend(): 
    global current_screen; current_screen="friends_remove"; rem_box.text=""; rem_box.txt_surface=FONT.render("",True,pygame.Color("black"))
def go_incoming(): 
    global current_screen; current_screen="friends_incoming"
def go_outgoing(): 
    global current_screen; current_screen="friends_outgoing"

def go_plants():
    global current_screen
    refresh_plants_from_db()
    current_screen = "plants"

# Actions
def do_login():
    global current_user,message
    if validate_login(login_user.text,login_pass.text): current_user=login_user.text; go_home()
    else: message="Invalid login"

def do_register():
    global current_user,message
    if reg_pass.text!=reg_conf.text: message="Passwords do not match"; return
    if try_register(reg_user.text,reg_pass.text): current_user=reg_user.text; go_home()
    else: message="Username exists"

def do_logout(): 
    global current_user; current_user=None; go_home()
def do_add_friend():
    global message
    target = add_box.text.strip()
    if not target:
        message = "Enter a username"
        return
    c = sqlite3.connect(DB_FILE)
    cur = c.cursor()
    cur.execute("SELECT 1 FROM userdata WHERE username=?", (target,))
    exists = cur.fetchone()
    c.close()
    if not exists:
        message = "User does not exist"
        return

    if send_request(current_user, target):
        message = "Request sent"
    else:
        message = "Failed (maybe already sent?)"
    go_friends()

def do_remove_friend():
    global pending_remove,current_screen
    pending_remove=rem_box.text; current_screen="friends_confirm_remove"

def confirm_remove_friend():
    global pending_remove
    if pending_remove: remove_friend(current_user,pending_remove)
    pending_remove=None; go_friends()

# UI Helpers
def draw_title(text):
    pygame.draw.rect(screen,(46,204,113),(0,0,WIDTH,40))
    lab=FONT.render(text,True,pygame.Color("white"))
    screen.blit(lab,(WIDTH//2-lab.get_width()//2,10))

def render_friend_list(page):
    friends=get_friends(current_user); start=page*5; pagefriends=friends[start:start+5]
    y=60
    for f in pagefriends:
        r=pygame.Rect(40,y,WIDTH-80,50); pygame.draw.rect(screen,pygame.Color("white"),r); pygame.draw.rect(screen,pygame.Color("black"),r,2)
        screen.blit(FONT.render(f,True,pygame.Color("black")),(r.x+10,r.y+15)); y+=60
    total_pages=max((len(friends)+4)//5,1)
    lab=FONT.render(f"Page {page+1}/{total_pages}",True,pygame.Color("black"))
    screen.blit(lab,(WIDTH//2-lab.get_width()//2,HEIGHT-90))
    return total_pages

# Input Boxes
login_user=InputBox(45,200,240,40); login_pass=InputBox(45,260,240,40,password=True)
reg_user=InputBox(45,180,240,40); reg_pass=InputBox(45,240,240,40,password=True); reg_conf=InputBox(45,300,240,40,password=True)
add_box=InputBox(45,180,240,40); rem_box=InputBox(45,180,240,40) 

# load images
plant_img = pygame.image.load("Plant.png")
plant_img = pygame.transform.scale(plant_img, (100, 100)).convert_alpha()

speechbubble_img = pygame.image.load("SpeechBubble.png")
speechbubble_img = pygame.transform.scale(speechbubble_img, (75, 75)).convert_alpha()

ai_response = "I'm Derek the Dandelion, I am here to help in all your gardening needs."
user_input = ""
input_active = False
scroll_y = 0
viewing_archives = False
plant_button_start_y = 110

# Reuse the Button class above for main UI buttons

# Functions to open modal add/edit window

def open_add_plant_window(prefill=None, index=None, plant_db_id=None):
    global viewing_archives
    # modal loop
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
        root = tk.Tk(); root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if file_path:
            photo_path = file_path

    def save_or_add():
        nonlocal running
        plant_data = {"name": name, "age": age, "shade": shade, "notes": notes, "photo": photo_path, "archived": archived}
        # Save to DB
        if prefill and 'id' in prefill:
            save_plant_to_db(plant_data, plant_id=prefill['id'])
        else:
            save_plant_to_db(plant_data, plant_id=None)
        # also save to json
        refresh_plants_from_db()
        save_plants_to_json()
        running = False

    def delete_plant():
        nonlocal running
        if prefill and 'id' in prefill:
            delete_plant_from_db(prefill['id'])
            refresh_plants_from_db()
            save_plants_to_json()
        running = False

    def archive_plant():
        nonlocal running
        if prefill and 'id' in prefill:
            save_plant_to_db({"name":name,"age":age,"shade":shade,"notes":notes,"photo":photo_path,"archived":True}, plant_id=prefill['id'])
            refresh_plants_from_db(); save_plants_to_json()
        running = False

    def unarchive_plant():
        nonlocal running
        if prefill and 'id' in prefill:
            save_plant_to_db({"name":name,"age":age,"shade":shade,"notes":notes,"photo":photo_path,"archived":False}, plant_id=prefill['id'])
            refresh_plants_from_db(); save_plants_to_json()
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
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if rects["name"].collidepoint(mx, my): input_field = "name"
                elif rects["age"].collidepoint(mx, my): input_field = "age"
                elif rects["notes"].collidepoint(mx, my): input_field = "notes"
                else: input_field = None
                if rects["shade"].collidepoint(mx, my): shade = not shade
                if rects["photo"].collidepoint(mx, my): pick_photo()
                if rects["save"].collidepoint(mx, my): save_or_add()
                if prefill and rects["delete"].collidepoint(mx, my): delete_plant()
                if prefill and rects["archive"].collidepoint(mx, my): archive_plant()
                if prefill and rects["unarchive"].collidepoint(mx, my): unarchive_plant()
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

        # Draw modal
        screen.fill((240,240,240))
        screen.blit(FONT.render("Name:", True, (0,0,0)), (30,30))
        screen.blit(FONT.render("Age:", True, (0,0,0)), (30,90))
        screen.blit(FONT.render("Shade:", True, (0,0,0)), (30,150))
        screen.blit(FONT.render("Notes:", True, (0,0,0)), (30,280))

        pygame.draw.rect(screen, (255,255,255), rects["name"])
        screen.blit(FONT.render(name, True, (0,0,0)), (rects["name"].x + 5, rects["name"].y + 5))
        pygame.draw.rect(screen, (255,255,255), rects["age"])
        screen.blit(FONT.render(age, True, (0,0,0)), (rects["age"].x + 5, rects["age"].y + 5))
        pygame.draw.rect(screen, (200,200,200) if not shade else (60,217,28), rects["shade"])
        screen.blit(FONT.render("Shade" if shade else "Sun", True, (0,0,0)), (rects["shade"].x + 5, rects["shade"].y + 5))
        pygame.draw.rect(screen, (255,255,255), rects["notes"])
        screen.blit(FONT.render(notes, True, (0,0,0)), (rects["notes"].x + 5, rects["notes"].y + 5))
        pygame.draw.rect(screen, (180,180,255), rects["photo"])
        screen.blit(FONT.render("Add Photo", True, (0,0,0)), (rects["photo"].x + 10, rects["photo"].y + 5))
        if photo_path:
            screen.blit(FONT.render(os.path.basename(photo_path), True, (0,0,0)), (rects["photo"].x + 130, rects["photo"].y + 5))
        pygame.draw.rect(screen, (100,255,100), rects["save"])
        screen.blit(FONT.render("Save Changes" if prefill else "Add to List", True, (0,0,0)), (rects["save"].x + 5, rects["save"].y + 10))
        if prefill:
            pygame.draw.rect(screen, (255,100,100), rects["delete"])
            screen.blit(FONT.render("Delete Plant", True, (0,0,0)), (rects["delete"].x + 5, rects["delete"].y + 10))
            pygame.draw.rect(screen, (255,200,100), rects["archive"])
            screen.blit(FONT.render("Archive", True, (0,0,0)), (rects["archive"].x + 5, rects["archive"].y + 10))
            pygame.draw.rect(screen, (200,255,100), rects["unarchive"])
            screen.blit(FONT.render("Unarchive", True, (0,0,0)), (rects["unarchive"].x + 5, rects["unarchive"].y + 10))

        pygame.display.flip()

# AI Action for gardening tips

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

# Initial sync
load_plants_from_json()
import_json_plants_to_db()
refresh_plants_from_db()
save_plants_to_json()

# Main Loop
running = True
while running:
    screen.fill((255, 255, 255))
    buttons = []

    # Title
    if current_screen == "home": draw_title("Home")
    elif current_screen == "login": draw_title("Login")
    elif current_screen == "register": draw_title("Register")
    elif current_screen == "account": draw_title("Account")
    elif current_screen.startswith("friends"): draw_title("Friends")
    elif current_screen == "plants": draw_title("Plants")

    # Screens
    incoming_count = len(get_incoming_requests(current_user)) if current_user else 0
    outgoing_count = len(get_outgoing_requests(current_user)) if current_user else 0

    if current_screen == "home":
        # Checklist Area
        pygame.draw.rect(screen, (255, 255, 255), checklist_area, border_radius=8)
        pygame.draw.rect(screen, (0, 0, 0), checklist_area, 2, border_radius=8)
        screen.blit(FONT.render("Checklist", True, (0, 0, 0)), (checklist_area.x + 5, checklist_area.y - 25))

        # Render tasks
        for i, item in enumerate(checklist_items):
            y = checklist_area.y + 10 + i * item_height
            box_rect = pygame.Rect(checklist_area.x + 10, y, checkbox_size, checkbox_size)
            text_rect = pygame.Rect(box_rect.right + 10, y, 200, checkbox_size)
            delete_rect = pygame.Rect(checklist_area.right - 35, y, 25, 25)

            if i == editing_index:
                pygame.draw.rect(screen, (220, 240, 255), (box_rect.right + 8, y, 220, checkbox_size))

            pygame.draw.rect(screen, (255, 255, 255), box_rect, border_radius=4)
            pygame.draw.rect(screen, (0, 0, 0), box_rect, 2, border_radius=4)
            if item["checked"]:
                pygame.draw.line(screen, (0, 150, 0), (box_rect.x + 4, box_rect.y + 12),
                                 (box_rect.x + 9, box_rect.y + 18), 2)
                pygame.draw.line(screen, (0, 150, 0), (box_rect.x + 9, box_rect.y + 18),
                                 (box_rect.x + 18, box_rect.y + 4), 2)

            text_surface = FONT.render(text_input if i == editing_index else item["text"], True, (0, 0, 0))
            screen.blit(text_surface, (box_rect.right + 12, y))

            pygame.draw.rect(screen, (255, 100, 100), delete_rect, border_radius=6)
            pygame.draw.rect(screen, (0, 0, 0), delete_rect, 2, border_radius=6)
            screen.blit(SMLFONT.render("X", True, (0, 0, 0)), (delete_rect.x + 7, delete_rect.y + 4))

        # Add new task button
        add_button_rect = pygame.Rect(checklist_area.x + 10,
                                      checklist_area.y + 10 + len(checklist_items) * item_height,
                                      120, 30)
        pygame.draw.rect(screen, (100, 220, 100), add_button_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), add_button_rect, 2, border_radius=6)
        screen.blit(FONT.render("+ Add Task", True, (0, 0, 0)),
                    (add_button_rect.x + 10, add_button_rect.y + 5))

        # Home page account/login button
        if current_user:
            buttons = [Button(f"{current_user}'s Account", 120, 60, 120, 40, go_account)]
        else:
            buttons = [Button("Login", 120, 60, 120, 40, go_login)]

        # Nav bar (Plants button now opens plants screen)
        buttons += [
            Button("Plants", 30, HEIGHT-50, 120, 40, go_plants),   # Left button
            Button("Home", WIDTH//2 - 60, HEIGHT-50, 120, 40, go_home),  # Center button
            Button("Friends", WIDTH-150, HEIGHT-50, 120, 40, lambda: go_friends() if current_user else None)  # Right button
        ]

        # Show warning if not logged in and clicks Friends
        if not current_user and pygame.mouse.get_pressed()[0] and buttons[-1].rect.collidepoint(pygame.mouse.get_pos()):
            login_warning = "Please login first"
            warning_timer = pygame.time.get_ticks()

    elif current_screen == "plants":
        # Left column: plant list
        screen.blit(FONT.render("Your Plants", True, (0,0,0)), (30,60))
        y_off = 90
        for i, plant in enumerate(plants):
            if viewing_archives and not plant.get('archived'):
                continue
            if not viewing_archives and plant.get('archived'):
                continue
            r = pygame.Rect(30, y_off + i*50, 200, 40)
            pygame.draw.rect(screen, (180, 220, 180), r, border_radius=6)
            pygame.draw.rect(screen, (0,0,0), r, 2, border_radius=6)
            screen.blit(FONT.render(plant.get('name', '') + (" (A)" if plant.get('archived') else ""), True, (0,0,0)), (r.x+10, r.y+10))

        # Draw images
        screen.blit(plant_img, (220, 250))
        screen.blit(speechbubble_img, (150, 225))
        
        # Buttons for plants
        buttons = [
            Button("Add Plant", 120, 10, 120, 40, lambda: open_add_plant_window()),
            Button("Ask Derek the Dandelion", 30, 400, 300, 50, gardening_tip_action),
            Button("Toggle Archives", 120, 60, 120, 30, lambda: globals().update(viewing_archives=not viewing_archives)),
            Button("Back", 120, HEIGHT-50, 120, 40, go_home)
        ]

        # AI input box
        input_box = pygame.Rect(20, 360, 320, 30)
        pygame.draw.rect(screen, (255, 255, 255), input_box, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), input_box, 2, border_radius=6)
        screen.blit(FONT.render(user_input, True, (0, 0, 0)), (input_box.x + 5, input_box.y + 5))

        # AI response box
        if ai_response:
            box_rect = pygame.Rect(20, 470, 320, 100)
            pygame.draw.rect(screen, (230, 230, 230), box_rect, border_radius=8)
            pygame.draw.rect(screen, (0, 0, 0), box_rect, 2, border_radius=8)
            clip_rect = box_rect.inflate(-10, -10)
            screen.set_clip(clip_rect)
            words, line, lines = ai_response.split(), "", []
            for word in words:
                test_line = line + word + " "
                if FONT.render(test_line, True, (0, 0, 0)).get_width() > clip_rect.width:
                    lines.append(line)
                    line = word + " "
                else:
                    line = test_line
            if line: lines.append(line)
            y = clip_rect.y + scroll_y
            for line in lines:
                screen.blit(FONT.render(line, True, (0, 0, 0)), (clip_rect.x, y))
                y += 20
            screen.set_clip(None)

    elif current_screen == "login":
        login_user.draw(screen); login_pass.draw(screen)
        buttons = [Button("Log in", 65, 340, 230, 50, do_login),
                   Button("Register", 65, 410, 230, 50, go_register),
                   Button("Back", 65, 480, 230, 50, go_home)]
    elif current_screen == "register":
        reg_user.draw(screen); reg_pass.draw(screen); reg_conf.draw(screen)
        buttons = [Button("Register", 65, 370, 230, 50, do_register),
                   Button("Back", 65, 440, 230, 50, go_login)]
    elif current_screen == "account":
        screen.blit(FONT.render(f"Logged in as {current_user}", True, (0, 0, 0)), (50, 150))
        buttons = [Button("Logout", 65, 250, 230, 50, do_logout),
                   Button("Back", 65, 320, 230, 50, go_home)]
    elif current_screen == "friends":
        total_pages = render_friend_list(friend_page)
        buttons = [Button("Add Friend", 65, 370, 230, 40, go_add_friend),
                   Button("Remove Friend", 65, 420, 230, 40, go_remove_friend),
                   Button(f"Incoming ({incoming_count})", 65, 470, 230, 40, go_incoming),
                   Button(f"Outgoing ({outgoing_count})", 65, 520, 230, 40, go_outgoing),
                   Button("Plants", 30, HEIGHT-50, 120, 40, go_plants),
                   Button("Home", WIDTH//2 - 60, HEIGHT-50, 120, 40, go_home),  
                   Button("Friends", WIDTH-150, HEIGHT-50, 120, 40, lambda: go_friends() if current_user else None)]
        if friend_page > 0:
            buttons.append(Button("<", 30, HEIGHT-90, 40, 30, lambda: globals().update(friend_page=friend_page-1)))
        if friend_page < total_pages-1:
            buttons.append(Button(">", WIDTH-70, HEIGHT-90, 40, 30, lambda: globals().update(friend_page=friend_page+1)))
    elif current_screen == "friends_add":
        add_box.draw(screen)
        buttons = [Button("Add", 65, 240, 230, 40, do_add_friend),
                   Button("Back", 65, 300, 230, 40, go_friends)]
    elif current_screen == "friends_remove":
        rem_box.draw(screen)
        buttons = [Button("Remove", 65, 240, 230, 40, do_remove_friend),
                   Button("Back", 65, 300, 230, 40, go_friends)]
    elif current_screen == "friends_confirm_remove":
        screen.blit(FONT.render(f"Remove {pending_remove}?", True, (0, 0, 0)), (60, 200))
        buttons = [Button("Yes", 65, 260, 100, 40, confirm_remove_friend),
                   Button("No", 200, 260, 100, 40, go_friends)]
    elif current_screen == "friends_incoming":
        y = 60
        for s in get_incoming_requests(current_user):
            r = pygame.Rect(40, y, WIDTH-80, 50)
            pygame.draw.rect(screen, (255, 255, 255), r)
            pygame.draw.rect(screen, (0, 0, 0), r, 2)
            screen.blit(FONT.render(s, True, (0, 0, 0)), (r.x + 10, r.y + 15))
            buttons += [Button("/", r.right-60, r.y+10, 20, 20, lambda sender=s: accept_request(sender, current_user)),
                        Button("X", r.right-30, r.y+10, 20, 20, lambda sender=s: decline_request(sender, current_user))]
            y += 60
        buttons.append(Button("Back", 65, HEIGHT-60, 230, 40, go_friends))
    elif current_screen == "friends_outgoing":
        y = 60
        for rcv in get_outgoing_requests(current_user):
            r = pygame.Rect(40, y, WIDTH-80, 50)
            pygame.draw.rect(screen, (255, 255, 255), r)
            pygame.draw.rect(screen, (0, 0, 0), r, 2)
            screen.blit(FONT.render(rcv, True, (0, 0, 0)), (r.x + 10, r.y + 15))
            buttons.append(Button("X", r.right-30, r.y+10, 20, 20, lambda rec=rcv: cancel_request(current_user, rec)))
            y += 60
        buttons.append(Button("Back", 65, HEIGHT-60, 230, 40, go_friends))

    # Events
    for e in pygame.event.get():
        if e.type == pygame.QUIT: 
            running = False

        if current_screen == "login": login_user.handle_event(e); login_pass.handle_event(e)
        elif current_screen == "register": reg_user.handle_event(e); reg_pass.handle_event(e); reg_conf.handle_event(e)
        elif current_screen == "friends_add": add_box.handle_event(e)
        elif current_screen == "friends_remove": rem_box.handle_event(e)

        for b in buttons: b.handle_event(e)

        # Checklist events
        if current_screen == "home":
            if e.type == pygame.MOUSEBUTTONDOWN:
                if add_button_rect.collidepoint(e.pos):
                    checklist_items.append({"text": "New Task", "checked": False})
                for i, item in enumerate(checklist_items):
                    y = checklist_area.y + 10 + i * item_height
                    box_rect = pygame.Rect(checklist_area.x + 10, y, checkbox_size, checkbox_size)
                    text_rect = pygame.Rect(box_rect.right + 10, y, 200, checkbox_size)
                    delete_rect = pygame.Rect(checklist_area.right - 35, y, 25, 25)

                    if box_rect.collidepoint(e.pos):
                        item["checked"] = not item["checked"]
                    elif text_rect.collidepoint(e.pos):
                        editing_index = i
                        text_input = item["text"]
                    elif delete_rect.collidepoint(e.pos):
                        checklist_items.pop(i)
                        if editing_index == i:
                            editing_index = None
                        break

            elif e.type == pygame.KEYDOWN and editing_index is not None:
                if e.key == pygame.K_RETURN:
                    checklist_items[editing_index]["text"] = text_input.strip() or "Untitled Task"
                    editing_index = None
                elif e.key == pygame.K_BACKSPACE:
                    text_input = text_input[:-1]
                else:
                    text_input += e.unicode

        # Plants screen events: click plant to edit, input box for AI
        if current_screen == "plants":
            if e.type == pygame.MOUSEBUTTONDOWN:
                mx,my = e.pos
                # detect clicks on plant entries
                y_base = 90
                clicked_index = None
                visible_index = 0
                for i, plant in enumerate(plants):
                    if viewing_archives and not plant.get('archived'):
                        continue
                    if not viewing_archives and plant.get('archived'):
                        continue
                    r = pygame.Rect(30, y_base + visible_index*50, 200, 40)
                    if r.collidepoint(mx,my):
                        clicked_index = i
                        break
                    visible_index += 1
                if clicked_index is not None:
                    open_add_plant_window(prefill=plants[clicked_index])
                # input box activation
                input_box_rect = pygame.Rect(20, 360, 320, 30)
                if input_box_rect.collidepoint(mx,my):
                    input_active = True
                else:
                    input_active = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    gardening_tip_action()
                elif e.key == pygame.K_BACKSPACE:
                    user_input = user_input[:-1]
                else:
                    user_input += e.unicode

    # Draw Buttons
    for b in buttons: b.draw(screen)

    # Messages
    if message: screen.blit(FONT.render(message, True, (200, 0, 0)), (20, HEIGHT-30))
    if login_warning:
        screen.blit(FONT.render(login_warning, True, (200, 0, 0)), (65, 260))
        if pygame.time.get_ticks() - warning_timer > 3000: login_warning = None

    pygame.display.flip()

# On exit, persist plants snapshot to JSON
save_plants_to_json()
pygame.quit()
sys.exit()
