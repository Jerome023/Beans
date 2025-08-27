import sqlite3
import hashlib

# ------------------ Database Setup ------------------ #
def setup_database():
    conn = sqlite3.connect("userdata.db")
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS userdata (
        id INTEGER PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password CHAR(64) NOT NULL
    )
    """)

    # Friends table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS friends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        friend_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','accepted')),
        FOREIGN KEY(user_id) REFERENCES userdata(id),
        FOREIGN KEY(friend_id) REFERENCES userdata(id)
    )
    """)

    conn.commit()
    conn.close()

# ------------------ Utility ------------------ #
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_id(username):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM userdata WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# ------------------ Authentication ------------------ #
def register():
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    while True:
        username = input("Choose a username: ").strip()
        password = input("Choose a password: ").strip()
        confirm_password = input("Confirm your password: ").strip()

        if password != confirm_password:
            print("Passwords do not match. Try again.")
            continue

        try:
            cursor.execute(
                "INSERT INTO userdata (username, password) VALUES (?, ?)",
                (username, hash_password(password))
            )
            conn.commit()
            print(f"Registered successfully! Welcome, {username}!")
            conn.close()
            return username  # Auto-login after registration
        except sqlite3.IntegrityError:
            print("Username already exists. Try a different one.")

def login():
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    cursor.execute("SELECT password FROM userdata WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] == hash_password(password):
        print(f"Login successful! Welcome, {username}!")
        return username
    else:
        print("Invalid username or password.")
        return None
    
# ------------------ Main Menu ------------------ #
def main_menu(username):
    while True:
        print("\n--- Main Menu ---")
        print("1. Friends System")
        print("q. Logout")

        choice = input("Choose an option: ").strip().lower()

        if choice == "1":
            friends_menu(username)
        elif choice == "q":
            print("Logging out...\n")
            break
        else:
            print("Invalid option.")

# ------------------ Friends System ------------------ #
def count_requests(user_id):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM friends WHERE friend_id = ? AND status = 'pending'", (user_id,))
    incoming = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM friends WHERE user_id = ? AND status = 'pending'", (user_id,))
    outgoing = cursor.fetchone()[0]

    conn.close()
    return incoming, outgoing


def friends_menu(username):
    user_id = get_user_id(username)

    while True:
        print("\n--- Friends Menu ---")
        view_friends(user_id)

        incoming_count, outgoing_count = count_requests(user_id)
        print(f"1. View Friend Requests ({incoming_count})")
        print(f"2. View Outgoing Requests ({outgoing_count})")
        print("3. Add Friend")
        print("4. Remove Friend")
        print("q. Main Menu")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            view_requests(user_id)
        elif choice == "2":
            view_outgoing(user_id)
        elif choice == "3":
            add_friend(user_id)
        elif choice == "4":
            remove_friend(user_id)
        elif choice.lower() == "q":
            break
        else:
            print("Invalid option.")


def view_friends(user_id):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT u.username
    FROM friends f
    JOIN userdata u ON (u.id = f.user_id OR u.id = f.friend_id)
    WHERE (f.user_id = ? OR f.friend_id = ?)
      AND f.status = 'accepted'
      AND u.id != ?
    """, (user_id, user_id, user_id))

    friends = cursor.fetchall()
    conn.close()

    if friends:
        print("Your friends:")
        for friend in friends:
            print(f" - {friend[0]}")
    else:
        print("No friends yet.")


def view_requests(user_id):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.username 
        FROM friends f
        JOIN userdata u ON f.user_id = u.id
        WHERE f.friend_id = ? AND f.status = 'pending'
    """, (user_id,))
    requests = cursor.fetchall()
    conn.close()

    if not requests:
        print("\nNo incoming friend requests.")
        return

    print("\n--- Incoming Friend Requests ---")
    for i, (username,) in enumerate(requests, start=1):
        print(f"{i}. {username}")

    while True:
        choice = input("\nType a username to Accept/Decline, or 'b' to go back: ").strip()
        
        if choice.lower() == "b":
            break

        # check if username is in requests
        valid_usernames = [u[0] for u in requests]
        if choice not in valid_usernames:
            print("Invalid username. Please type exactly as shown.")
            continue

        action = input(f"Do you want to (a)ccept or (d)ecline {choice}? ").strip().lower()
        if action not in ["a", "d"]:
            print("Invalid option. Type 'a' for accept or 'd' for decline.")
            continue

        confirm = input(f"Are you sure you want to {'ACCEPT' if action == 'a' else 'DECLINE'} {choice}? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            continue

        conn = sqlite3.connect("userdata.db")
        cursor = conn.cursor()

        if action == "a":
            cursor.execute("""
                UPDATE friends 
                SET status = 'accepted'
                WHERE user_id = (SELECT id FROM userdata WHERE username = ?)
                AND friend_id = ?
                AND status = 'pending'
            """, (choice, user_id))
            print(f"You are now friends with {choice}!")

        elif action == "d":
            cursor.execute("""
                DELETE FROM friends 
                WHERE user_id = (SELECT id FROM userdata WHERE username = ?)
                AND friend_id = ?
                AND status = 'pending'
            """, (choice, user_id))
            print(f"You declined the request from {choice}.")

        conn.commit()
        conn.close()

        # refresh the list after action
        return view_requests(user_id)



def view_outgoing(user_id):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT u.username 
    FROM friends f
    JOIN userdata u ON f.friend_id = u.id
    WHERE f.user_id = ? AND f.status = 'pending'
    """, (user_id,))

    outgoing = cursor.fetchall()
    conn.close()

    if outgoing:
        print("Outgoing friend requests:")
        for uname in outgoing:
            uname = uname[0]
            confirm = input(f"Cancel friend request to {uname}? (y/n/skip): ").strip().lower()
            if confirm == "y":
                cancel_request(user_id, uname)
    else:
        print("No outgoing requests.")


def add_friend(user_id):
    target = input("Enter username to add: ").strip()
    target_id = get_user_id(target)

    if not target_id:
        print("User not found.")
        return
    if target_id == user_id:
        print("You cannot add yourself.")
        return

    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT status FROM friends 
    WHERE (user_id = ? AND friend_id = ?) 
       OR (user_id = ? AND friend_id = ?)
    """, (user_id, target_id, target_id, user_id))

    relation = cursor.fetchone()

    if relation:
        print("You are already connected or request pending.")
    else:
        cursor.execute("""
        INSERT INTO friends (user_id, friend_id, status)
        VALUES (?, ?, 'pending')
        """, (user_id, target_id))
        conn.commit()
        print(f"Friend request sent to {target}!")

    conn.close()


def remove_friend(user_id):
    target = input("Enter username to remove: ").strip()
    target_id = get_user_id(target)

    if not target_id:
        print("User not found.")
        return

    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM friends 
    WHERE ((user_id = ? AND friend_id = ?) 
        OR (user_id = ? AND friend_id = ?))
      AND status = 'accepted'
    """, (user_id, target_id, target_id, user_id))

    if cursor.rowcount > 0:
        print(f"Removed {target} from your friends.")
    else:
        print("You are not friends with this user.")

    conn.commit()
    conn.close()


def handle_request(user_id, from_username, accept):
    from_id = get_user_id(from_username)
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    if accept:
        cursor.execute("""
        UPDATE friends SET status = 'accepted' 
        WHERE user_id = ? AND friend_id = ? AND status = 'pending'
        """, (from_id, user_id))
        print(f"You are now friends with {from_username}!")
    else:
        cursor.execute("""
        DELETE FROM friends 
        WHERE user_id = ? AND friend_id = ? AND status = 'pending'
        """, (from_id, user_id))
        print(f"Declined friend request from {from_username}.")

    conn.commit()
    conn.close()


def cancel_request(user_id, to_username):
    to_id = get_user_id(to_username)
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM friends 
    WHERE user_id = ? AND friend_id = ? AND status = 'pending'
    """, (user_id, to_id))

    if cursor.rowcount > 0:
        print(f"Cancelled request to {to_username}.")
    else:
        print("No such request found.")

    conn.commit()
    conn.close()


# ------------------ Main ------------------ #
def main():
    setup_database()
    print("Gardening Tracker\n")
    
    while True:   # Keep looping until quit
        choice = input("Do you want to Login or Register? (q to quit): ").strip()
        
        if choice.lower() == "login":
            user = login()
            if user:
                main_menu(user)  # Once logout, return here
        
        elif choice.lower() == "register":
            user = register()
            if user:
                main_menu(user)  # After registering, go into friends menu
        
        elif choice.lower() == "q":
            print("Exiting...")
            break
        else:
            print("Invalid option, try again.")

if __name__ == "__main__":
    main()
