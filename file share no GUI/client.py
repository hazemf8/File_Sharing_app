#!/usr/bin/env python3
"""
Client side of the file-sharing system (with registration, login, and file sharing).
Run with:   python3 client.py
"""

import socket
import os

# ---------- Configuration (must match the server) ----------
HOST = '127.0.0.1'
PORT = 5555

# ---------- Helper ----------
def recv_line(reader):
    """Read exactly one newline‑terminated line from the binary reader."""
    line = b''
    while True:
        ch = reader.read(1)
        if not ch:
            return b''
        if ch == b'\n':
            return line.decode()
        line += ch

# ---------- Main client logic ----------
def connect_and_authenticate():
    """Establish connection, present Register/Login/Exit menu.
    Returns (socket, reader, writer, username) on successful login,
    or (None, None, None, None) if the user chooses to exit."""
    while True:
        print("\n" + "=" * 40)
        print("1. Register a new account")
        print("2. Login")
        print("3. Exit")
        choice = input("Choose an option: ").strip()

        if choice == '1':   # Registration
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((HOST, PORT))
            except ConnectionRefusedError:
                print("[!] Could not connect to server. Is it running?")
                continue

            reader = sock.makefile('rb')
            writer = sock.makefile('wb')

            username = input("Choose a username: ").strip()
            password = input("Choose a password: ").strip()

            writer.write(f"REGISTER {username} {password}\n".encode())
            writer.flush()
            resp = recv_line(reader)

            if resp == "REGISTER_OK":
                print("[✓] Registration successful! You can now login.")
            elif resp == "USER_EXISTS":
                print("[!] Username already exists. Please choose another.")
            else:
                print(f"[!] Registration failed: {resp}")

            sock.close()

        elif choice == '2':   # Login
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((HOST, PORT))
            except ConnectionRefusedError:
                print("[!] Could not connect to server. Is it running?")
                continue

            reader = sock.makefile('rb')
            writer = sock.makefile('wb')

            username = input("Username: ").strip()
            password = input("Password: ").strip()
            writer.write(f"LOGIN {username} {password}\n".encode())
            writer.flush()
            resp = recv_line(reader)

            if resp == "LOGIN_OK":
                print(f"[✓] Welcome, {username}!\n")
                return sock, reader, writer, username
            else:
                print("[!] Login failed. Check username and password.")
                sock.close()

        elif choice == '3':   # Exit
            print("Goodbye!")
            return None, None, None, None
        else:
            print("[!] Invalid option. Please choose 1, 2, or 3.")

def file_operations_menu(sock, reader, writer, username):
    """Interactive loop for file operations after successful login."""
    while True:
        print("=" * 40)
        print(f"Logged in as: {username}")
        print("1. List files")
        print("2. Upload file")
        print("3. Download file")
        print("4. Delete file")
        print("5. Share file with another user")
        print("6. Logout and exit")
        choice = input("Choose an option: ").strip()

        if choice == '1':   # List
            writer.write(b"LIST\n"); writer.flush()
            print("\nYour files on server:")
            line = recv_line(reader)
            while line and line != "END":
                parts = line.split(maxsplit=1)
                if len(parts) == 1:
                    print(f"  {parts[0]}  (unknown size)")
                else:
                    print(f"  {parts[0]}  ({parts[1]} bytes)")
                line = recv_line(reader)
            if line != "END":
                print("[!] Unexpected server response."); break

        elif choice == '2': # Upload
            fname = input("Enter local file path to upload: ").strip()
            if not os.path.isfile(fname):
                print("[!] File does not exist.")
                continue
            fsize = os.path.getsize(fname)
            writer.write(f"UPLOAD {os.path.basename(fname)} {fsize}\n".encode())
            writer.flush()
            resp = recv_line(reader)
            if resp != "READY":
                print("[!] Server rejected upload."); continue
            # Send file data
            with open(fname, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk: break
                    writer.write(chunk)
            writer.flush()
            resp = recv_line(reader)
            if resp == "UPLOAD_OK":
                print(f"[✓] File '{fname}' uploaded.")
            else:
                print(f"[!] Upload failed: {resp}")

        elif choice == '3': # Download
            fname = input("Enter filename to download: ").strip()
            writer.write(f"DOWNLOAD {fname}\n".encode()); writer.flush()
            resp = recv_line(reader)
            if resp == "NOTFOUND":
                print("[!] File not found on server.")
            elif resp.startswith("FILE "):
                parts = resp.split()
                if len(parts) < 3:
                    print("[!] Malformed server response."); continue
                srv_fname = parts[1]
                fsize = int(parts[2])
                save_as = input(f"Save as (default: {srv_fname}): ").strip()
                if not save_as:
                    save_as = srv_fname
                data = reader.read(fsize)
                with open(save_as, 'wb') as f:
                    f.write(data)
                print(f"[✓] File saved as '{save_as}' ({fsize} bytes).")
            else:
                print(f"[!] Unexpected response: {resp}")

        elif choice == '4': # Delete
            fname = input("Enter filename to delete: ").strip()
            writer.write(f"DELETE {fname}\n".encode()); writer.flush()
            resp = recv_line(reader)
            if resp == "DELETED":
                print(f"[✓] File '{fname}' deleted.")
            else:
                print(f"[!] File not found or could not be deleted.")

        elif choice == '5': # Share file
            fname = input("Enter the filename you want to share: ").strip()
            recipient = input("Enter the username to share with: ").strip()
            writer.write(f"SHARE {fname} {recipient}\n".encode())
            writer.flush()
            resp = recv_line(reader)
            if resp == "SHARE_OK":
                print(f"[✓] File '{fname}' shared with '{recipient}'.")
            elif resp == "FILE_NOT_FOUND":
                print(f"[!] You don't own a file named '{fname}'.")
            elif resp == "USER_NOT_FOUND":
                print(f"[!] User '{recipient}' does not exist.")
            else:
                print(f"[!] Sharing failed: {resp}")

        elif choice == '6': # Exit & logout
            writer.write(b"EXIT\n"); writer.flush()
            recv_line(reader)  # BYE
            sock.close()
            print("Logged out. Goodbye!")
            break
        else:
            print("[!] Invalid option.")

# ---------- Entry point ----------
if __name__ == "__main__":
    sock, reader, writer, username = connect_and_authenticate()
    if sock:
        file_operations_menu(sock, reader, writer, username)