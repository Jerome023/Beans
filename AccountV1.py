import sqlite3
import hashlib

def setup_database():
    conn = sqlite3.connect("userdata.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS userdata (
        id INTEGER PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        password CHAR(64) NOT NULL
    )
    """)
    conn.commit()
    conn.close()
    
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register ():
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()
    
    while True:
        username= input("Choose a username: ")
        password = input ("Choose a password: ")
        confirm_password = input("Confirm your password: ")
        
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

# Login
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

#Main Menu
def main():
    setup_database()
    print("Gardening Tracker\n")
    
    while True:
        choice = input("Do you want to Login or Register? (q to quit): ").strip()
        
        if choice.lower() == "login":
            user = login()
            if user:
                break  # Exit after successful login
        
        elif choice.lower() == "register":
            user = register()
            if user:
                break  # Auto-login after successful registration
        
        elif choice.lower() == "q":
            print("Exiting...")
            break
        else:
            print("Invalid option, try again.")

if __name__ == "__main__":
    main()



