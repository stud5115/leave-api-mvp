import sqlite3

# --- BACKEND SETUP ---

def init_db():
    """Create database and employees table if it doesn't exist."""
    conn = sqlite3.connect("leave_system.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            leave_balance INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_employee(name, leave_balance):
    """Add a new employee to the database."""
    conn = sqlite3.connect("leave_system.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO employees (name, leave_balance) VALUES (?, ?)", (name, leave_balance))
    conn.commit()
    conn.close()

def get_leave_balance(name):
    """Return the leave balance for an employee."""
    conn = sqlite3.connect("leave_system.db")
    cursor = conn.cursor()
    cursor.execute("SELECT leave_balance FROM employees WHERE name = ?", (name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def apply_for_leave(name, days):
    """Reduce leave balance if enough days remain."""
    conn = sqlite3.connect("leave_system.db")
    cursor = conn.cursor()
    cursor.execute("SELECT leave_balance FROM employees WHERE name = ?", (name,))
    result = cursor.fetchone()
    if result:
        current_balance = result[0]
        if days <= current_balance:
            new_balance = current_balance - days
            cursor.execute("UPDATE employees SET leave_balance = ? WHERE name = ?", (new_balance, name))
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    conn.close()
    return None

# --- CLIENT MENU ---

def main_menu():
    while True:
        print("\n==== Leave Management System ====")
        print("1. Add Employee")
        print("2. Check Leave Balance")
        print("3. Apply for Leave")
        print("4. Exit")
        
        choice = input("Choose an option: ")

        if choice == "1":
            name = input("Enter employee name: ")
            balance = int(input("Enter starting leave balance: "))
            add_employee(name, balance)
            print(f"Employee {name} added with {balance} days leave.")

        elif choice == "2":
            name = input("Enter your name: ")
            balance = get_leave_balance(name)
            if balance is not None:
                print(f"{name} has {balance} leave days remaining.")
            else:
                print("Employee not found.")

        elif choice == "3":
            name = input("Enter your name: ")
            days = int(input("Enter number of leave days to apply for: "))
            result = apply_for_leave(name, days)
            if result is True:
                print(f"Leave approved for {days} days.")
            elif result is False:
                print("Not enough leave days available.")
            else:
                print("Employee not found.")

        if balance < 0:
    print("Leave balance cannot be negative.")
    continue

if days <= 0:
    print("Number of leave days must be positive.")
    continue

        elif choice == "4":
            print("Exiting system.")
            break

        else:
            print("Invalid choice. Please try again.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    init_db()
    main_menu()
