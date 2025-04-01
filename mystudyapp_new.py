import sys
import json
import bcrypt
import sqlite3
import hashlib
import datetime
import subprocess
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QFrame, QPushButton, QVBoxLayout, QHBoxLayout,
                             QListWidget, QLineEdit, QMessageBox, QDialog, QGridLayout, QTableWidget, QDateTimeEdit, 
                             QComboBox, QStackedWidget, QInputDialog)

# Database setup
conn = sqlite3.connect("tasks.db")
cursor = conn.cursor()

# Create the tasks table first
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    task_name TEXT,
    task_time TEXT,
    status TEXT,
    notes TEXT DEFAULT '',
    recurrence TEXT DEFAULT 'None',
    xp INTEGER DEFAULT 10,
    time_limit TEXT DEFAULT '00:30',
    difficulty INTEGER DEFAULT 1
);
""")
conn.commit()


cursor.execute("""
CREATE TABLE IF NOT EXISTS xp_tracking (
    id INTEGER PRIMARY KEY,
    task_id INTEGER,
    xp_gained INTEGER DEFAULT 0,
    xp_lost INTEGER DEFAULT 0,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()


# Ensure required columns exist
cursor.execute("PRAGMA table_info(tasks)")
columns = [col[1] for col in cursor.fetchall()]
if "recurrence" not in columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT 'None'")
if "xp" not in columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN xp INTEGER DEFAULT 10")
if "time_limit" not in columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN time_limit TEXT DEFAULT '00:30'")
conn.commit()

# Ensure required columns exist
cursor.execute("PRAGMA table_info(tasks)")
columns = [col[1] for col in cursor.fetchall()]
if "recurrence" not in columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT 'None'")
if "xp" not in columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN xp INTEGER DEFAULT 10")
if "time_limit" not in columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN time_limit TEXT DEFAULT '00:30'")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    task_name TEXT,
    task_time TEXT,
    status TEXT,
    notes TEXT,
    recurrence TEXT,
    xp INTEGER,
    time_limit TEXT
)
""")
conn.commit()

# Player stats table
cursor.execute("""
CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY,
    player_name TEXT UNIQUE,
    password_hash TEXT,
    intelligence INTEGER DEFAULT 0,
    dexterity INTEGER DEFAULT 0,
    flexibility INTEGER DEFAULT 0,
    strength INTEGER DEFAULT 0,
    combat_power INTEGER DEFAULT 0,
    popularity INTEGER DEFAULT 0,
    ranking INTEGER DEFAULT 1000
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    stat_name TEXT PRIMARY KEY,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1
);
""")
conn.commit()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS exercise_logs (
        id INTEGER PRIMARY KEY,
        task_name TEXT,
        date TEXT,
        completed INTEGER DEFAULT 0
    )
""")
conn.commit()


def setup_database():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

# Check if columns exist and add them if missing
cursor.execute("PRAGMA table_info(tasks)")
columns = [col[1] for col in cursor.fetchall()]

if "category" not in columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'general'")
if "current_step" not in columns:
    cursor.execute("ALTER TABLE tasks ADD COLUMN current_step INTEGER DEFAULT 0")

conn.commit()

setup_database()  # Run this when the app starts


# Load chat history for Ollama
chat_history_file = "chat_history.json"
try:
    with open(chat_history_file, "r") as f:
        content = f.read().strip()
        chat_history = json.loads(content) if content else []
except (FileNotFoundError, json.JSONDecodeError):
    chat_history = []

def save_chat_history():
    with open(chat_history_file, "w") as f:
        json.dump(chat_history, f, indent=4)

# Custom theme settings
def set_dark_theme(widget):
    palette = widget.palette()
    palette.setColor(QPalette.Window, QColor(20, 20, 20))
    palette.setColor(QPalette.WindowText, QColor(0, 255, 255))
    widget.setPalette(palette)
    widget.setStyleSheet("color: cyan; background-color: #121212; font-size: 16px;")

# File path for saving skill data
SKILL_FILE = "skills.json"

# Skill XP structure
default_skills = {
    "Python": {"level": "Beginner", "xp": 0},
    "Strength": {"level": "Novice", "xp": 0},
    "Communication": {"level": "Basic", "xp": 0},
}

def load_skills():
    """Loads skill XP from the JSON file or initializes default skills."""
    try:
        with open(SKILL_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_skills

def save_skills(skills):
    """Saves the updated skill XP to the JSON file."""
    with open(SKILL_FILE, "w") as f:
        json.dump(skills, f, indent=4)

# Load skills at the start of the program
skills = load_skills()


class PlayerStatsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_stats_ui()

    def init_stats_ui(self):
        # Set a dark background and white text to mimic a manga-style design
        self.setStyleSheet("background-color: black; color: white; font-family: Arial;")
        self.main_layout = QVBoxLayout()

        # Title Label: Displays a clear header
        title = QLabel("PLAYER STATS")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title)

        # Stats Info Label: Will be updated by refresh_stats() with dynamic data
        self.stats_info_label = QLabel("Loading...")
        self.stats_info_label.setFont(QFont("Arial", 12))
        self.stats_info_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.stats_info_label)

        # Optional: Skills Section
        skills_label = QLabel("SKILLS")
        skills_label.setFont(QFont("Arial", 16, QFont.Bold))
        skills_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(skills_label)

        # Example Skills List (can be made dynamic later)
        skills = ["Sword Mastery LV3", "Endurance LV2", "Stealth LV4"]
        for skill in skills:
            skill_label = QLabel(f"• {skill}")
            skill_label.setFont(QFont("Arial", 12))
            skill_label.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(skill_label)

        # Navigation Button: To navigate to the Tasks page
        self.goto_tasks_btn = QPushButton("Go to Tasks")
        self.main_layout.addWidget(self.goto_tasks_btn)

        self.setLayout(self.main_layout)

    def refresh_stats(self, stats_data):
        """
        Update the stats display based on data from the player_stats table.
        Expected stats_data tuple format:
        (id, player_name, intelligence, dexterity, flexibility, strength, combat_power, popularity, ranking)
        """
        if stats_data:
            stats_text = (
                f"Intelligence: {stats_data[2]} | Dexterity: {stats_data[3]} | Flexibility: {stats_data[4]} | "
                f"Strength: {stats_data[5]} | Combat Power: {stats_data[6]} | Popularity: {stats_data[7]}"
            )
            self.stats_info_label.setText(stats_text)

class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ollama Chat")
        self.setGeometry(200, 200, 500, 600)

        layout = QVBoxLayout()

        # Chat history display
        self.chat_display = QListWidget()
        layout.addWidget(self.chat_display)

        # User input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Ollama...")
        layout.addWidget(self.input_field)

        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)

        self.setLayout(layout)

        # Load existing chat history
        self.load_chat_history()

    def load_chat_history(self):
        try:
            with open("C:/codes/chat_history.json", "r") as f:
                content = f.read().strip()
                chat_history = json.loads(content) if content else []
        except (FileNotFoundError, json.JSONDecodeError):
            chat_history = []

        # Populate chat window
        for chat in chat_history:
            for sender, message in chat.items():
                self.chat_display.addItem(f"{sender.capitalize()}: {message}")

    def send_message(self):
        question = self.input_field.text().strip()
        if not question:
            return

        self.chat_display.addItem(f"User: {question}")
        self.input_field.clear()

        # Call Ollama in WSL
        try:
            process = subprocess.run(
            ["wsl", "ollama", "run", "local_model"],
            input=question,
            text=True,
            capture_output=True,
            timeout=90,
            check=True
            )

            output = process.stdout.strip()
            self.chat_display.addItem(f"Ollama: {output}")

            # Save new chat to history
            self.save_chat_history(question, output)

        except subprocess.TimeoutExpired:
            self.chat_display.addItem("Ollama: Timeout! Try again later.")

        except subprocess.CalledProcessError as e:
            self.chat_display.addItem(f"Ollama: Error: {e}")

    def save_chat_history(self, question, response):
        try:
            with open("C:/codes/chat_history.json", "r") as f:
                content = f.read().strip()
                chat_history = json.loads(content) if content else []
        except (FileNotFoundError, json.JSONDecodeError):
            chat_history = []

        chat_history.append({"user": question, "ollama": response})

        with open("C:/codes/chat_history.json", "w") as f:
            json.dump(chat_history, f, indent=4)


class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_player_stats()
        self.load_tasks()
    
    def init_ui(self):
        print("Initializing UI...")
        self.setWindowTitle("My App")
        self.setGeometry(100, 100, 700, 500)
        set_dark_theme(self)

        # Create the stacked widget first
        self.stack = QStackedWidget(self)

        # --- Login Page ---
        self.login_page = QWidget()
        login_layout = QVBoxLayout()
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Enter Player ID")
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Enter Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.login_btn = QPushButton("Login", self)
        self.login_btn.clicked.connect(self.login_user)
        self.login_btn.setEnabled(True)
        self.register_btn = QPushButton("Register", self)
        self.register_btn.clicked.connect(self.open_register_page)
        login_layout.addWidget(self.username_input)
        login_layout.addWidget(self.password_input)
        login_layout.addWidget(self.login_btn)
        login_layout.addWidget(self.register_btn)
        self.login_page.setLayout(login_layout)
        self.stack.addWidget(self.login_page)

        # --- Registration Page ---
        self.register_page = QWidget()
        register_layout = QVBoxLayout()
        self.reg_username_input = QLineEdit(self)
        self.reg_username_input.setPlaceholderText("Enter New Player ID")
        self.reg_password_input = QLineEdit(self)
        self.reg_password_input.setPlaceholderText("Enter Password")
        self.reg_password_input.setEchoMode(QLineEdit.Password)
        self.reg_confirm_password_input = QLineEdit(self)
        self.reg_confirm_password_input.setPlaceholderText("Confirm Password")
        self.reg_confirm_password_input.setEchoMode(QLineEdit.Password)
        self.submit_register_btn = QPushButton("Register", self)
        self.submit_register_btn.clicked.connect(self.register_user)
        self.back_to_login_btn = QPushButton("Back to Login", self)
        self.back_to_login_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.login_page))
        register_layout.addWidget(self.reg_username_input)
        register_layout.addWidget(self.reg_password_input)
        register_layout.addWidget(self.reg_confirm_password_input)
        register_layout.addWidget(self.submit_register_btn)
        register_layout.addWidget(self.back_to_login_btn)
        self.register_page.setLayout(register_layout)
        self.stack.addWidget(self.register_page)

        # --- Player Stats Page using the new class ---
        self.stats_page = PlayerStatsPage()
        # Ensure the "Go to Tasks" button on the stats page navigates correctly:
        self.stats_page.goto_tasks_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.tasks_page))
        self.stack.addWidget(self.stats_page)

        # --- Side Page (For Extra Features) ---
        self.side_page = QWidget()
        side_layout = QVBoxLayout()
        self.ollama_chat_btn = QPushButton("Chat with Ollama", self)
        self.ollama_chat_btn.clicked.connect(self.open_chat_window)
        self.goto_stats_btn = QPushButton("View Player Stats", self)
        self.goto_stats_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.stats_page))
        side_layout.addWidget(self.ollama_chat_btn)
        side_layout.addWidget(self.goto_stats_btn)
        # "Check Failures" Button is only added in the side page
        self.check_failures_btn = QPushButton("Check Failures", self)
        self.check_failures_btn.clicked.connect(self.check_failures_with_progress)
        side_layout.addWidget(self.check_failures_btn)
        self.side_page.setLayout(side_layout)
        self.stack.addWidget(self.side_page)

        # --- Task Page ---
        self.tasks_page = QWidget()
        tasks_layout = QVBoxLayout()
        self.goto_side_page_btn = QPushButton("More Options", self)
        self.goto_side_page_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.side_page))
        tasks_layout.addWidget(self.goto_side_page_btn)
        self.task_list = QListWidget(self)
        self.task_input = QLineEdit(self)
        self.task_input.setPlaceholderText("Enter task name")
        self.time_input = QDateTimeEdit(self)
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setTime(QDateTime.currentDateTime().time())
        self.time_limit_input = QLineEdit(self)
        self.time_limit_input.setPlaceholderText("Time Limit (HH:MM)")
        self.recurrence_input = QComboBox(self)
        self.recurrence_input.addItems(["None", "Daily", "Weekly", "Monthly", "Yearly"])
        self.category_input = QComboBox(self)
        self.category_input.setEditable(True)
        self.category_input.addItems(["general", "exercise"])
        tasks_layout.addWidget(self.task_list)
        tasks_layout.addWidget(self.task_input)
        tasks_layout.addWidget(self.category_input)
        tasks_layout.addWidget(self.time_input)
        tasks_layout.addWidget(self.time_limit_input)
        tasks_layout.addWidget(self.recurrence_input)

        # Buttons for tasks in a horizontal layout
        task_buttons_layout = QHBoxLayout()
        self.add_task_btn = QPushButton("Add Task", self)
        self.delete_task_btn = QPushButton("Delete Task", self)
        self.complete_task_btn = QPushButton("Mark as Done", self)
        self.add_task_btn.clicked.connect(self.add_task)
        self.delete_task_btn.clicked.connect(self.delete_task)
        self.complete_task_btn.clicked.connect(self.mark_done)
        task_buttons_layout.addWidget(self.add_task_btn)
        task_buttons_layout.addWidget(self.delete_task_btn)
        task_buttons_layout.addWidget(self.complete_task_btn)
        tasks_layout.addLayout(task_buttons_layout)

        self.tasks_page.setLayout(tasks_layout)
        self.stack.addWidget(self.tasks_page)

        # --- Set Initial Page ---
        print("Switching to login page...")
        self.stack.setCurrentWidget(self.login_page)
        self.username_input.setFocus()

        # --- Main Layout ---
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)



    def open_register_page(self):
        print("Switching to Register Page...")
        self.stack.setCurrentWidget(self.register_page)




    def open_chat_window(self):
        self.chat_window = ChatWindow()
        self.chat_window.setWindowModality(True)
        self.chat_window.show()


    def login_user(self):
        print("Login button clicked")
        username = self.username_input.text()
        password = self.password_input.text()

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        
        conn.close()

        if user:
            print("Login Successful!")
            self.stack.setCurrentWidget(self.stats_page)  # Redirect to main app
        else:
            QMessageBox.warning(self, "Error", "Invalid Player ID or Password")

    def register_user(self):
        username = self.reg_username_input.text()
        password = self.reg_password_input.text()
        confirm_password = self.reg_confirm_password_input.text()

        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords do not match!")
            return

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        # Check if username exists
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            QMessageBox.warning(self, "Error", "Username already exists!")
            conn.close()
            return

        # Insert new user
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        QMessageBox.information(self, "Success", "Account Created! Please log in.")
        self.stack.setCurrentWidget(self.login_page)  # Redirect to login page


    def add_task(self):
        task_name = self.task_input.text().strip()
        task_time = self.time_input.time().toString("HH:mm")
        time_limit = self.time_limit_input.text().strip() or "00:30"
        recurrence = self.recurrence_input.currentText()
        category = self.category_input.currentText()  # Fetch category selection

        if not task_name:
            QMessageBox.warning(self, "Error", "Task name cannot be empty.")
            return

        try:
            cursor.execute("""
                INSERT INTO tasks (task_name, task_time, status, recurrence, time_limit, category, current_step)
                VALUES (?, ?, 'Pending', ?, ?, ?, ?)
            """, (task_name, task_time, recurrence, time_limit, category, 0))
            
            conn.commit()
            self.load_tasks()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Database Error: {e}")


    def delete_task(self):
        selected_task = self.task_list.currentItem()
        if not selected_task:
            QMessageBox.warning(self, "Error", "No task selected for deletion.")
            return

        task_name = selected_task.text().split(" - ")[0]  # Extract Task Name

        # Confirm Deletion
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete '{task_name}'?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                cursor.execute("DELETE FROM tasks WHERE task_name=?", (task_name,))
                conn.commit()
                self.load_tasks()  # Refresh Task List
                QMessageBox.information(self, "Success", f"Task '{task_name}' deleted successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete task: {e}")


    def mark_done(self):
        selected_task = self.task_list.currentItem()
        
        if selected_task:
            task_name = selected_task.text().split(" - ")[0]
            cursor.execute("SELECT id, category, difficulty, xp FROM tasks WHERE task_name=?", (task_name,))
            task_data = cursor.fetchone()

            if task_data:
                task_id, category, difficulty, base_xp = task_data

                # Define XP multipliers for different difficulties
                xp_multipliers = {"Easy": 1.0, "Medium": 1.5, "Hard": 2.0}
                xp_gain = int(base_xp * xp_multipliers.get(difficulty, 1.5))  # Default: Medium

                # Map task category to skills
                category_to_skill = {
                    "Coding": "Python",
                    "Workout": "Strength",
                    "Social": "Communication",
                }

                if category in category_to_skill:
                    skill = category_to_skill[category]
                    skills[skill]["xp"] += xp_gain  # Add XP

                    # Check for level-up
                    self.check_skill_upgrade(skill)

                    # Save new XP data
                    save_skills(skills)

                # Mark task as completed in DB
                cursor.execute("UPDATE tasks SET status='Completed' WHERE id=?", (task_id,))
                conn.commit()
                self.load_tasks()  # Refresh task list
                print(f"✅ Task '{task_name}' completed! Earned {xp_gain} XP in {skill}.")

    def save_incomplete_progress(self):
        """
        Save the current progress for tasks that are still pending but have passed their time limit.
        This function logs the current step so that if the same task appears later, you can resume from where you left off.
        """
        cursor.execute("""
            SELECT id, task_name, current_step 
            FROM tasks
            WHERE status='Pending' AND datetime(task_time) < datetime('now', '-' || time_limit || ' minutes')
        """)
        tasks_to_update = cursor.fetchall()

        for task in tasks_to_update:
            task_id, task_name, current_step = task
            # Here, you could update the current_step as needed. For now, we just keep the value.
            new_step = current_step  # This could be modified if you have logic to increment the step.
            cursor.execute("UPDATE tasks SET current_step=? WHERE id=?", (new_step, task_id))
        
        conn.commit()


    def check_failures_with_progress(self):
        # First, save incomplete progress for tasks that have timed out
        self.save_incomplete_progress()
        
        # Fetch Completed Tasks
        cursor.execute("""
            SELECT task_time, task_name, notes, recurrence 
            FROM tasks WHERE status='Completed' 
            ORDER BY 
                CASE WHEN recurrence='Daily' THEN 1
                    WHEN recurrence='Weekly' THEN 2
                    WHEN recurrence='Monthly' THEN 3
                    WHEN recurrence='Yearly' THEN 4
                END, task_time ASC
        """)
        completed_tasks = cursor.fetchall()

        # Fetch Failed (Incomplete) Tasks
        cursor.execute("""
            SELECT task_time, task_name, notes, recurrence 
            FROM tasks WHERE status='Pending' 
            AND datetime(task_time) < datetime('now', '-' || time_limit || ' minutes')
            ORDER BY 
                CASE WHEN recurrence='Daily' THEN 1
                    WHEN recurrence='Weekly' THEN 2
                    WHEN recurrence='Monthly' THEN 3
                    WHEN recurrence='Yearly' THEN 4
                END, task_time ASC
        """)
        failed_tasks = cursor.fetchall()

        # Create a QDialog to display the tables
        failure_dialog = QDialog(self)
        failure_dialog.setWindowTitle("Task Status")
        failure_dialog.setGeometry(300, 300, 800, 600)
        layout = QVBoxLayout()

        # Create and set up table for Completed Tasks
        completed_label = QLabel("COMPLETED TASKS:")
        layout.addWidget(completed_label)
        completed_table = QTableWidget()
        completed_table.setColumnCount(4)
        completed_table.setHorizontalHeaderLabels(["Task Time", "Task Name", "Notes", "Recurrence"])
        completed_table.setRowCount(len(completed_tasks))
        for i, task in enumerate(completed_tasks):
            for j, value in enumerate(task):
                completed_table.setItem(i, j, QTableWidgetItem(str(value)))
        layout.addWidget(completed_table)

        # Create and set up table for Failed Tasks
        failed_label = QLabel("FAILED TASKS:")
        layout.addWidget(failed_label)
        failed_table = QTableWidget()
        failed_table.setColumnCount(4)
        failed_table.setHorizontalHeaderLabels(["Task Time", "Task Name", "Notes", "Recurrence"])
        failed_table.setRowCount(len(failed_tasks))
        for i, task in enumerate(failed_tasks):
            for j, value in enumerate(task):
                failed_table.setItem(i, j, QTableWidgetItem(str(value)))
        layout.addWidget(failed_table)

        failure_dialog.setLayout(layout)
        failure_dialog.exec_()
    def load_tasks(self):
        self.task_list.clear()
        cursor.execute("SELECT task_name, task_time, status, xp, current_step, category FROM tasks")
        for task in cursor.fetchall():
            task_name, task_time, status, xp, current_step, category = task
            step_info = f" (Step {current_step})" if current_step > 0 else ""
            xp_info = f" [XP: {xp}]"
            self.task_list.addItem(f"{task_name} - {task_time} - {status}{step_info}{xp_info} - {category}")

    def load_player_stats(self):
        cursor.execute("SELECT * FROM player_stats LIMIT 1")
        data = cursor.fetchone()
        if not data:
            cursor.execute("INSERT INTO player_stats (player_name) VALUES ('Player1')")
            conn.commit()
            cursor.execute("SELECT * FROM player_stats LIMIT 1")
            data = cursor.fetchone()
        self.stats_page.refresh_stats(data)

def apply_xp_gain(self, xp, task_name):
    # Map tasks to relevant stats
    stat_mapping = {
        "Coding": "intelligence",
        "Workout": "strength",
        "Reading": "intelligence",
        "Networking": "popularity",
        "Yoga": "flexibility",
        "Sparring": "combat_power",
        "Community Work": "popularity"
    }
    
    cursor.execute("SELECT category FROM tasks WHERE task_name=?", (task_name,))
    category = cursor.fetchone()
    
    if category:
        stat_column = stat_mapping.get(category[0])
        if stat_column:
            cursor.execute(f"UPDATE player_stats SET {stat_column} = {stat_column} + ? WHERE id=1", (xp,))
            
            # Check for level up
            cursor.execute(f"SELECT {stat_column} FROM player_stats WHERE id=1")
            new_stat_value = cursor.fetchone()[0]
            if new_stat_value >= 100:  # Example threshold for leveling up
                cursor.execute(f"UPDATE player_stats SET {stat_column} = 0, ranking = ranking - 10 WHERE id=1")
                QMessageBox.information(self, "Level Up!", f"{stat_column.capitalize()} Leveled Up!")
            
            conn.commit()

    def apply_xp_loss(self, xp_loss, task_name):
        stat_mapping = {
            "Coding": "intelligence",
            "Workout": "strength",
            "Reading": "intelligence",
            "Networking": "popularity",
            "Yoga": "flexibility",
            "Sparring": "combat_power",
            "Community Work": "popularity"
        }

        cursor.execute("SELECT category FROM tasks WHERE task_name=?", (task_name,))
        category = cursor.fetchone()

        if category:
            stat_column = stat_mapping.get(category[0])
            if stat_column:
                cursor.execute(f"UPDATE player_stats SET {stat_column} = {stat_column} - ? WHERE id=1", (xp_loss,))
                conn.commit()


    def refresh_stats(self, stats_data):
        # Fetch player stats (should be only one row)
        cursor.execute("SELECT * FROM player_stats LIMIT 1")
        data = cursor.fetchone()
        if not data:
            cursor.execute("INSERT INTO player_stats (player_name) VALUES ('Player1')")
            conn.commit()
            cursor.execute("SELECT * FROM player_stats LIMIT 1")
            data = cursor.fetchone()
            
        # Fetch exercise log counts (workouts completed and skipped)
        cursor.execute("SELECT COUNT(*) FROM exercise_logs WHERE completed=1")
        completed = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM exercise_logs WHERE completed=0")
        skipped = cursor.fetchone()[0]
        
        if data:
            # data indices: 0:id, 1:player_name, 2:intelligence, 3:dexterity, 4:flexibility,
            # 5:strength, 6:combat_power, 7:popularity, 8:ranking
            stats_text = (
                f"Intelligence: {data[2]} | Dexterity: {data[3]} | Flexibility: {data[4]} | "
                f"Strength: {data[5]} | Combat Power: {data[6]} | Popularity: {data[7]} | "
                f"Workouts Completed: {completed} | Workouts Skipped: {skipped}"
            )
            self.stats_display.setText(stats_text)

# Run application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
