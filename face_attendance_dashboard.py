import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import cv2
import os
import numpy as np
from datetime import datetime
import pandas as pd
import smtplib
import threading
# Initialize DB for admin users
def init_db():
    conn = sqlite3.connect('admin_users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')
    conn.commit()
    conn.close()

marked_names = set()

def mark_attendance(name):
    if name in marked_names:
        return
    marked_names.add(name)
    now = datetime.now()
    df = pd.DataFrame({
        'Name': [name],
        'Time': [now.strftime('%H:%M:%S')],
        'Date': [now.strftime('%Y-%m-%d')]
    })
    if os.path.exists("attendance.xlsx"):
        existing = pd.read_excel("attendance.xlsx")
        df = pd.concat([existing, df], ignore_index=True)
    df.to_excel("attendance.xlsx", index=False)
   
def capture_and_save_face():
    def save_face_to_folder():
        name = name_entry.get()
        if not name:
            messagebox.showerror("Error", "Enter a name.")
            return

        cap = cv2.VideoCapture(0)
        detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

        saved = False
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.1, 4)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                face_crop = frame[y:y+h, x:x+w]
                face_crop = cv2.resize(face_crop, (100, 100))
                cv2.imshow("Saving Face", face_crop)
                cv2.imwrite(f"faces/{name}.jpg", face_crop)
                saved = True
                break

            cv2.imshow("Webcam - Press Q to Quit", frame)
            if saved or cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        if saved:
            messagebox.showinfo("Success", f"Face for '{name}' saved successfully!")
        else:
            messagebox.showwarning("Warning", "No face captured.")

    # Small popup window for name input
    win = tk.Toplevel()
    win.title("Add New Face")
    win.geometry("300x100")
    tk.Label(win, text="Enter Name:").pack(pady=5)
    name_entry = tk.Entry(win)
    name_entry.pack()
    tk.Button(win, text="Capture Face", command=save_face_to_folder).pack(pady=5)
def load_known_faces(path='faces'):
    images, names = [], []
    for file in os.listdir(path):
        img = cv2.imread(os.path.join(path, file))
        if img is not None:
            images.append(cv2.resize(img, (100, 100)))
            names.append(os.path.splitext(file)[0])
    return images, names

def recognize_faces():
    known_faces, known_names = load_known_faces()
    if not known_faces:
        messagebox.showerror("Error", "No images found in 'faces' folder.")
        return

    cap = cv2.VideoCapture(0)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.1, 4)

        for (x, y, w, h) in faces:
            face_crop = cv2.resize(frame[y:y+h, x:x+w], (100, 100))
            for i, known in enumerate(known_faces):
                diff = np.mean(cv2.absdiff(known, face_crop))
                if diff < 50:
                    name = known_names[i]
                    mark_attendance(name)
                    cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    break
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        cv2.imshow("Face Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def show_dashboard():
    dash = tk.Toplevel()
    dash.title("Admin Dashboard")
    dash.geometry("400x300")
    tk.Label(dash, text="Welcome Admin!", font=("Arial", 14)).pack(pady=10)
    tk.Button(dash, text="Start Attendance", command=recognize_faces).pack(pady=10)
    tk.Button(dash, text="Add New Face", command=capture_and_save_face).pack(pady=10)
    tk.Button(dash, text="View Attendance", command=view_attendance).pack(pady=10)
    tk.Button(dash, text="Exit", command=dash.destroy).pack(pady=10)

def view_attendance():
    try:
        df = pd.read_excel("attendance.xlsx")
    except:
        messagebox.showerror("Error", "attendance.xlsx not found")
        return

    top = tk.Toplevel()
    top.title("Attendance Data")
    top.geometry("600x400")
    tree = ttk.Treeview(top, columns=list(df.columns), show='headings')
    for col in df.columns:
        tree.heading(col, text=col)
        tree.column(col, width=150)
    for _, row in df.iterrows():
        tree.insert("", tk.END, values=list(row))
    tree.pack(expand=True, fill='both')

def register_user():
    uname = reg_username.get()
    pwd = reg_password.get()
    if not uname or not pwd:
        messagebox.showerror("Error", "All fields are required.")
        return

    conn = sqlite3.connect('admin_users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (uname, pwd))
        conn.commit()
        messagebox.showinfo("Success", "Admin registered successfully!")
        reg_window.destroy()
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Username already exists.")
    conn.close()

def login():
    uname = username_entry.get()
    pwd = password_entry.get()
    conn = sqlite3.connect('admin_users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE username=? AND password=?", (uname, pwd))
    user = c.fetchone()
    conn.close()
    if user:
        login_window.destroy()
        show_dashboard()
    else:
        messagebox.showerror("Login Failed", "Invalid credentials.")

def open_register_window():
    global reg_username, reg_password, reg_window
    reg_window = tk.Toplevel()
    reg_window.title("Register")
    reg_window.geometry("300x200")
    tk.Label(reg_window, text="Username").pack()
    reg_username = tk.Entry(reg_window)
    reg_username.pack()
    tk.Label(reg_window, text="Password").pack()
    reg_password = tk.Entry(reg_window, show="*")
    reg_password.pack()
    tk.Button(reg_window, text="Register", command=register_user).pack(pady=10)

# ------------------- MAIN GUI -------------------
init_db()
root = tk.Tk()
root.withdraw()

login_window = tk.Toplevel()
login_window.title("Admin Login")
login_window.geometry("300x200")
tk.Label(login_window, text="Admin Login", font=("Arial", 14)).pack(pady=10)
tk.Label(login_window, text="Username").pack()
username_entry = tk.Entry(login_window)
username_entry.pack()
tk.Label(login_window, text="Password").pack()
password_entry = tk.Entry(login_window, show="*")
password_entry.pack()
tk.Button(login_window, text="Login", command=login).pack(pady=5)
tk.Button(login_window, text="Register New Admin", command=open_register_window).pack()

login_window.mainloop()
