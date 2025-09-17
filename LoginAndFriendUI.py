import sqlite3
import hashlib
import pygame
import sys

# ------------------ Database ------------------ #
DB_FILE = "appdata.db"

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
    # always store as (smaller, larger) to avoid duplicates
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

# ------------------ Pygame UI ------------------ #
pygame.init()
WIDTH, HEIGHT = 360, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
FONT = pygame.font.SysFont(None, 28)

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

# ------------------ Global State ------------------ #
setup_database()
current_screen="home"; current_user=None; message=""; login_warning=None; warning_timer=0
friend_page=0; pending_remove=None

# ------------------ Navigation ------------------ #
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

# ------------------ Actions ------------------ #
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
    # Check if user exists
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

# ------------------ UI Helpers ------------------ #
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

# ------------------ Input Boxes ------------------ #
login_user=InputBox(45,200,240,40); login_pass=InputBox(45,260,240,40,password=True)
reg_user=InputBox(45,180,240,40); reg_pass=InputBox(45,240,240,40,password=True); reg_conf=InputBox(45,300,240,40,password=True)
add_box=InputBox(45,180,240,40); rem_box=InputBox(45,180,240,40)

# ------------------ Main Loop ------------------ #
running=True
while running:
    screen.fill((255,255,255)); buttons=[]
    # --- Title ---
    if current_screen=="home": draw_title("Home")
    elif current_screen=="login": draw_title("Login")
    elif current_screen=="register": draw_title("Register")
    elif current_screen=="account": draw_title("Account")
    elif current_screen.startswith("friends"): draw_title("Friends")
    # --- Screens ---
    incoming_count = len(get_incoming_requests(current_user))
    outgoing_count = len(get_outgoing_requests(current_user))
    
    if current_screen=="home":
        if current_user: buttons=[Button(f"{current_user}'s Account",65,200,230,50,go_account)]
        else: buttons=[Button("Login",65,200,230,50,go_login)]
        # Nav bar
        buttons+=[Button("Home",30,HEIGHT-50,120,40,go_home),
                  Button("Friends",200,HEIGHT-50,120,40,lambda: go_friends() if current_user else None)]
        
        if not current_user and pygame.mouse.get_pressed()[0] and buttons[-1].rect.collidepoint(pygame.mouse.get_pos()):
            login_warning="Please login first"; warning_timer=pygame.time.get_ticks()
    elif current_screen=="login":
        login_user.draw(screen); login_pass.draw(screen)
        buttons=[Button("Log in",65,340,230,50,do_login),Button("Register",65,410,230,50,go_register),Button("Back",65,480,230,50,go_home)]
    elif current_screen=="register":
        reg_user.draw(screen); reg_pass.draw(screen); reg_conf.draw(screen)
        buttons=[Button("Register",65,370,230,50,do_register),Button("Back",65,440,230,50,go_login)]
    elif current_screen=="account":
        screen.blit(FONT.render(f"Logged in as {current_user}",True,(0,0,0)),(50,150))
        buttons=[Button("Logout",65,250,230,50,do_logout),Button("Back",65,320,230,50,go_home)]
    elif current_screen=="friends":
        total_pages=render_friend_list(friend_page)
        buttons=[Button("Add Friend",65,370,230,40,go_add_friend),Button("Remove Friend",65,420,230,40,go_remove_friend),
                 Button(f"Incoming ({incoming_count})",65,470,230,40,go_incoming),Button(f"Outgoing ({outgoing_count})",65,520,230,40,go_outgoing),
                 Button("Home",30,HEIGHT-50,120,40,go_home),Button("Friends",200,HEIGHT-50,120,40,go_friends)]
        if friend_page>0: buttons.append(Button("<",30,HEIGHT-90,40,30,lambda: globals().update(friend_page=friend_page-1)))
        if friend_page<total_pages-1: buttons.append(Button(">",WIDTH-70,HEIGHT-90,40,30,lambda: globals().update(friend_page=friend_page+1)))
    elif current_screen=="friends_add":
        add_box.draw(screen); buttons=[Button("Add",65,240,230,40,do_add_friend),Button("Back",65,300,230,40,go_friends)]
    elif current_screen=="friends_remove":
        rem_box.draw(screen); buttons=[Button("Remove",65,240,230,40,do_remove_friend),Button("Back",65,300,230,40,go_friends)]
    elif current_screen=="friends_confirm_remove":
        screen.blit(FONT.render(f"Remove {pending_remove}?",True,(0,0,0)),(60,200))
        buttons=[Button("Yes",65,260,100,40,confirm_remove_friend),Button("No",200,260,100,40,go_friends)]
    elif current_screen=="friends_incoming":
        y=60
        for s in get_incoming_requests(current_user):
            r=pygame.Rect(40,y,WIDTH-80,50); pygame.draw.rect(screen,(255,255,255),r); pygame.draw.rect(screen,(0,0,0),r,2)
            screen.blit(FONT.render(s,True,(0,0,0)),(r.x+10,r.y+15))
            buttons+=[Button("/",r.right-60,r.y+10,20,20,lambda sender=s: accept_request(sender,current_user)),
                      Button("X",r.right-30,r.y+10,20,20,lambda sender=s: decline_request(sender,current_user))]
            y+=60
        buttons.append(Button("Back",65,HEIGHT-60,230,40,go_friends))
    elif current_screen=="friends_outgoing":
        y=60
        for rcv in get_outgoing_requests(current_user):
            r=pygame.Rect(40,y,WIDTH-80,50); pygame.draw.rect(screen,(255,255,255),r); pygame.draw.rect(screen,(0,0,0),r,2)
            screen.blit(FONT.render(rcv,True,(0,0,0)),(r.x+10,r.y+15))
            buttons.append(Button("X",r.right-30,r.y+10,20,20,lambda rec=rcv: cancel_request(current_user,rec)))
            y+=60
        buttons.append(Button("Back",65,HEIGHT-60,230,40,go_friends))
    # --- Events ---
    for e in pygame.event.get():
        if e.type==pygame.QUIT: running=False
        if current_screen=="login": login_user.handle_event(e); login_pass.handle_event(e)
        elif current_screen=="register":
            reg_user.handle_event(e); reg_pass.handle_event(e); reg_conf.handle_event(e)
        elif current_screen=="friends_add": add_box.handle_event(e)
        elif current_screen=="friends_remove": rem_box.handle_event(e)
        for b in buttons: b.handle_event(e)
    # --- Draw Buttons ---
    for b in buttons: b.draw(screen)
    # --- Message ---
    if message: screen.blit(FONT.render(message,True,(200,0,0)),(20,HEIGHT-30))
    if login_warning:
        screen.blit(FONT.render(login_warning,True,(200,0,0)),(65,260))
        if pygame.time.get_ticks()-warning_timer>3000: login_warning=None
    pygame.display.flip()

pygame.quit()
sys.exit()
