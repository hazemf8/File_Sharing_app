#!/usr/bin/env python3
"""
Server side of the file-sharing system (with registration, login, and file sharing).
Run with:   python3 server.py
"""

import socket
import threading
import sqlite3

# ---------- Configuration ----------
HOST = '127.0.0.1'
PORT = 5555
DB_FILE = 'server.db'

# ---------- Database Initialisation ----------
def init_db():
    """Create the users and files tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        filesize INTEGER NOT NULL,
                        filedata BLOB NOT NULL,
                        UNIQUE(username, filename),
                        FOREIGN KEY(username) REFERENCES users(username))""")
    conn.commit()
    conn.close()

# ---------- Client handler (runs in a separate thread) ----------
def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    reader = conn.makefile('rb')
    writer = conn.makefile('wb')
    username = None

    try:
        # ---- Authentication phase: accept LOGIN or REGISTER ----
        auth_line = reader.readline().decode().strip()
        if not auth_line:
            return

        if auth_line.startswith("REGISTER "):
            _, user, pwd = auth_line.split(maxsplit=2)
            db = sqlite3.connect(DB_FILE)
            try:
                db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pwd))
                db.commit()
                writer.write(b"REGISTER_OK\n")
                print(f"[REGISTER] New user '{user}' registered from {addr}")
            except sqlite3.IntegrityError:
                writer.write(b"USER_EXISTS\n")
            db.close()
            writer.flush()
            return

        elif auth_line.startswith("LOGIN "):
            _, user, pwd = auth_line.split(maxsplit=2)
            db = sqlite3.connect(DB_FILE)
            db.execute("PRAGMA journal_mode=WAL")
            cur = db.execute("SELECT password FROM users WHERE username=?", (user,))
            row = cur.fetchone()
            if row and row[0] == pwd:
                username = user
                writer.write(b"LOGIN_OK\n"); writer.flush()
                print(f"[LOGIN] User '{username}' logged in from {addr}")
            else:
                writer.write(b"LOGIN_FAIL\n"); writer.flush()
                db.close()
                return
            db.close()
        else:
            writer.write(b"INVALID\n"); writer.flush()
            return

        # ---- Command loop (only for logged-in users) ----
        while True:
            cmd_line = reader.readline().decode().strip()
            if not cmd_line:
                break
            parts = cmd_line.split(maxsplit=2)

            if parts[0] == "LIST":
                handle_list(username, writer)

            elif parts[0] == "UPLOAD":
                if len(parts) < 3:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                _, fname, fsize_str = parts
                try:
                    fsize = int(fsize_str)
                except ValueError:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                writer.write(b"READY\n"); writer.flush()
                handle_upload(username, fname, fsize, reader, writer)

            elif parts[0] == "DOWNLOAD":
                if len(parts) < 2:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                handle_download(username, parts[1], writer)

            elif parts[0] == "DELETE":
                if len(parts) < 2:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                handle_delete(username, parts[1], writer)

            elif parts[0] == "SHARE":
                if len(parts) < 3:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                handle_share(username, parts[1], parts[2], writer)

            elif parts[0] == "EXIT":
                writer.write(b"BYE\n"); writer.flush()
                break

            else:
                writer.write(b"INVALID\n"); writer.flush()

    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        reader.close()
        writer.close()
        conn.close()
        if username:
            print(f"[DISCONNECT] {username} @ {addr}")
        else:
            print(f"[DISCONNECT] {addr}")

# ---------- Command handlers ----------
def handle_list(username, writer):
    db = sqlite3.connect(DB_FILE)
    cur = db.execute("SELECT filename, filesize FROM files WHERE username=?",
                     (username,))
    files = cur.fetchall()
    for fname, fsize in files:
        writer.write(f"{fname} {fsize}\n".encode())
    writer.write(b"END\n")
    writer.flush()
    db.close()

def handle_upload(username, fname, fsize, reader, writer):
    data = reader.read(fsize)
    db = sqlite3.connect(DB_FILE)
    # Replace existing file with same name
    db.execute("DELETE FROM files WHERE username=? AND filename=?",
               (username, fname))
    db.execute("INSERT INTO files (username, filename, filesize, filedata) "
               "VALUES (?, ?, ?, ?)", (username, fname, fsize, data))
    db.commit()
    db.close()
    writer.write(b"UPLOAD_OK\n"); writer.flush()

def handle_download(username, fname, writer):
    db = sqlite3.connect(DB_FILE)
    cur = db.execute("SELECT filesize, filedata FROM files "
                     "WHERE username=? AND filename=?", (username, fname))
    row = cur.fetchone()
    if row:
        fsize, data = row
        writer.write(f"FILE {fname} {fsize}\n".encode())
        writer.flush()
        writer.write(data)
        writer.flush()
    else:
        writer.write(b"NOTFOUND\n"); writer.flush()
    db.close()

def handle_delete(username, fname, writer):
    db = sqlite3.connect(DB_FILE)
    cur = db.execute("DELETE FROM files WHERE username=? AND filename=?",
                     (username, fname))
    if cur.rowcount > 0:
        db.commit()
        writer.write(b"DELETED\n")
    else:
        writer.write(b"NOTFOUND\n")
    writer.flush()
    db.close()

def handle_share(sender, filename, recipient, writer):
    """Copy a file from sender to recipient if both exist."""
    db = sqlite3.connect(DB_FILE)
    # 1. Check sender owns the file
    cur = db.execute("SELECT filesize, filedata FROM files "
                     "WHERE username=? AND filename=?", (sender, filename))
    file_row = cur.fetchone()
    if not file_row:
        db.close()
        writer.write(b"FILE_NOT_FOUND\n"); writer.flush()
        return

    # 2. Check recipient exists
    cur = db.execute("SELECT username FROM users WHERE username=?", (recipient,))
    if not cur.fetchone():
        db.close()
        writer.write(b"USER_NOT_FOUND\n"); writer.flush()
        return

    # 3. Copy the file to recipient (replace if already exists)
    fsize, data = file_row
    db.execute("DELETE FROM files WHERE username=? AND filename=?",
               (recipient, filename))
    db.execute("INSERT INTO files (username, filename, filesize, filedata) "
               "VALUES (?, ?, ?, ?)", (recipient, filename, fsize, data))
    db.commit()
    db.close()
    writer.write(b"SHARE_OK\n"); writer.flush()

# ---------- Main server loop ----------
def start_server():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[SERVER] Listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down.")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()