import socket
import threading
import sqlite3

HOST = '127.0.0.1'
PORT = 5555
DB_FILE = 'server.db'

def init_db():
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

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    reader = conn.makefile('rb')
    writer = conn.makefile('wb')
    username = None

    try:
        auth_line = reader.readline().decode().strip()
        if not auth_line:
            return

        if auth_line.startswith("REGISTER "):
            _, user, pwd = auth_line.split(maxsplit=2)
            db = sqlite3.connect(DB_FILE)
            try:
                db.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                           (user, pwd))
                db.commit()
                writer.write(b"REGISTER_OK\n")
                print(f"[REGISTER] New user '{user}'")
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
                writer.write(b"LOGIN_OK\n")
                writer.flush()
                print(f"[LOGIN] User '{username}' logged in")
            else:
                writer.write(b"LOGIN_FAIL\n")
                writer.flush()
                db.close()
                return
            db.close()
        else:
            writer.write(b"INVALID\n")
            writer.flush()
            return

        while True:
            cmd_line = reader.readline().decode().strip()
            if not cmd_line:
                break

            parts = cmd_line.split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if command == "LIST":
                handle_list(username, writer)

            elif command == "UPLOAD":
                if not args:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                try:
                    fsize_str, fname = args.split(maxsplit=1)
                    fsize = int(fsize_str)
                except (ValueError, IndexError):
                    writer.write(b"INVALID\n"); writer.flush(); continue

                # --- New check: reject if file exists ---
                db = sqlite3.connect(DB_FILE)
                cur = db.execute("SELECT 1 FROM files WHERE username=? AND filename=?",
                                 (username, fname))
                exists = cur.fetchone() is not None
                db.close()

                if exists:
                    writer.write(b"FILE_EXISTS\n"); writer.flush()
                    continue

                writer.write(b"READY\n"); writer.flush()
                handle_upload(username, fname, fsize, reader, writer)

            elif command == "DOWNLOAD":
                if not args:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                handle_download(username, args, writer)

            elif command == "DELETE":
                if not args:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                handle_delete(username, args, writer)

            elif command == "SHARE":
                if not args:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                words = args.split()
                if len(words) < 2:
                    writer.write(b"INVALID\n"); writer.flush(); continue
                recipient = words[-1]
                fname = " ".join(words[:-1])
                handle_share(username, fname, recipient, writer)

            elif command == "EXIT":
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

def handle_list(username, writer):
    db = sqlite3.connect(DB_FILE)
    cur = db.execute("SELECT filename, filesize FROM files WHERE username=?",
                     (username,))
    files = cur.fetchall()
    for fname, fsize in files:
        writer.write(f"{fsize} {fname}\n".encode())
    writer.write(b"END\n")
    writer.flush()
    db.close()

def handle_upload(username, fname, fsize, reader, writer):
    data = reader.read(fsize)
    db = sqlite3.connect(DB_FILE)
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
        writer.write(f"FILE {fsize} {fname}\n".encode())
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
    db = sqlite3.connect(DB_FILE)
    cur = db.execute("SELECT filesize, filedata FROM files "
                     "WHERE username=? AND filename=?", (sender, filename))
    file_row = cur.fetchone()
    if not file_row:
        db.close()
        writer.write(b"FILE_NOT_FOUND\n"); writer.flush()
        return

    cur = db.execute("SELECT username FROM users WHERE username=?", (recipient,))
    if not cur.fetchone():
        db.close()
        writer.write(b"USER_NOT_FOUND\n"); writer.flush()
        return

    fsize, data = file_row
    db.execute("DELETE FROM files WHERE username=? AND filename=?",
               (recipient, filename))
    db.execute("INSERT INTO files (username, filename, filesize, filedata) "
               "VALUES (?, ?, ?, ?)", (recipient, filename, fsize, data))
    db.commit()
    db.close()
    writer.write(b"SHARE_OK\n"); writer.flush()

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