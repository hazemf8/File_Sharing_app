import socket
import os

# ------------------- Configuration -------------------
HOST = '127.0.0.1'   # Localhost (same machine)
PORT = 5001          # Arbitrary non‑privileged port
BUFFER_SIZE = 4096   # 4 KB chunks for file transfer
SERVER_FOLDER = 'server_files'  # Directory where server stores files

# Create the server folder if it doesn't exist
os.makedirs(SERVER_FOLDER, exist_ok=True)
# -----------------------------------------------------

def handle_client(conn, addr):
    """Handle a single client connection."""
    print(f"[NEW CONNECTION] {addr} connected.")

    while True:
        # Receive command from client
        command = conn.recv(BUFFER_SIZE).decode().strip()
        if not command:
            break

        print(f"[COMMAND] {command} from {addr}")

        # ---------- LIST command ----------
        if command.upper() == 'LIST':
            try:
                files = os.listdir(SERVER_FOLDER)
                file_list = '\n'.join(files) if files else "No files found."
            except Exception as e:
                file_list = f"ERROR: {str(e)}"
            conn.send(file_list.encode())

        # ---------- UPLOAD command ----------
        elif command.upper().startswith('UPLOAD'):
            # Expected format: UPLOAD <filename> <filesize>
            parts = command.split()
            if len(parts) != 3:
                conn.send(b"ERROR: Invalid UPLOAD format. Use: UPLOAD <filename> <size>")
                continue

            _, filename, filesize_str = parts
            try:
                filesize = int(filesize_str)
            except ValueError:
                conn.send(b"ERROR: File size must be an integer.")
                continue

            # Acknowledge readiness
            conn.send(b"READY")

            # Receive file data
            filepath = os.path.join(SERVER_FOLDER, filename)
            received = 0
            with open(filepath, 'wb') as f:
                while received < filesize:
                    chunk = conn.recv(min(BUFFER_SIZE, filesize - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)

            if received == filesize:
                conn.send(b"SUCCESS: File uploaded.")
                print(f"[UPLOAD] Received {filename} ({filesize} bytes) from {addr}")
            else:
                conn.send(b"ERROR: File transfer incomplete.")

        # ---------- DOWNLOAD command ----------
        elif command.upper().startswith('DOWNLOAD'):
            # Expected format: DOWNLOAD <filename>
            parts = command.split()
            if len(parts) != 2:
                conn.send(b"ERROR: Invalid DOWNLOAD format. Use: DOWNLOAD <filename>")
                continue

            _, filename = parts
            filepath = os.path.join(SERVER_FOLDER, filename)

            if not os.path.isfile(filepath):
                conn.send(b"ERROR: File not found.")
                continue

            # Send file size and wait for client ready signal
            filesize = os.path.getsize(filepath)
            conn.send(f"SIZE {filesize}".encode())

            ack = conn.recv(BUFFER_SIZE).decode().strip()
            if ack.upper() != 'READY':
                conn.send(b"ERROR: Client not ready.")
                continue

            # Send file data
            with open(filepath, 'rb') as f:
                while chunk := f.read(BUFFER_SIZE):
                    conn.send(chunk)

            print(f"[DOWNLOAD] Sent {filename} ({filesize} bytes) to {addr}")

        # ---------- QUIT command ----------
        elif command.upper() == 'QUIT':
            conn.send(b"Goodbye.")
            break

        else:
            conn.send(b"ERROR: Unknown command. Use LIST, UPLOAD, DOWNLOAD, QUIT.")

    conn.close()
    print(f"[DISCONNECTED] {addr} disconnected.")


def start_server():
    """Create and run the server socket."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server stopped.")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()