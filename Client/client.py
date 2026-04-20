import socket
import os

# ------------------- Configuration -------------------
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5001
BUFFER_SIZE = 4096
CLIENT_FOLDER = 'client_files'   # Local folder for downloads/uploads
os.makedirs(CLIENT_FOLDER, exist_ok=True)
# -----------------------------------------------------

def send_command(sock, command):
    """Send a command and return the server response."""
    sock.send(command.encode())
    return sock.recv(BUFFER_SIZE).decode().strip()


def upload_file(sock, filename):
    """Upload a file from CLIENT_FOLDER to the server."""
    filepath = os.path.join(CLIENT_FOLDER, filename)
    if not os.path.isfile(filepath):
        print(f"ERROR: File '{filename}' does not exist in {CLIENT_FOLDER}")
        return

    filesize = os.path.getsize(filepath)

    # Send UPLOAD command with size
    sock.send(f"UPLOAD {filename} {filesize}".encode())
    response = sock.recv(BUFFER_SIZE).decode().strip()
    if response != "READY":
        print(f"Server error: {response}")
        return

    # Send file data
    with open(filepath, 'rb') as f:
        while chunk := f.read(BUFFER_SIZE):
            sock.send(chunk)

    # Wait for final acknowledgement
    result = sock.recv(BUFFER_SIZE).decode().strip()
    print(result)


def download_file(sock, filename):
    """Download a file from the server and save it in CLIENT_FOLDER."""
    # Send DOWNLOAD command
    sock.send(f"DOWNLOAD {filename}".encode())
    response = sock.recv(BUFFER_SIZE).decode().strip()

    if not response.startswith("SIZE"):
        print(f"Server error: {response}")
        return

    # Extract file size
    try:
        filesize = int(response.split()[1])
    except (IndexError, ValueError):
        print("ERROR: Invalid server response.")
        return

    # Tell server we are ready
    sock.send(b"READY")

    # Receive file data
    filepath = os.path.join(CLIENT_FOLDER, filename)
    received = 0
    with open(filepath, 'wb') as f:
        while received < filesize:
            chunk = sock.recv(min(BUFFER_SIZE, filesize - received))
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)

    if received == filesize:
        print(f"SUCCESS: Downloaded {filename} ({filesize} bytes)")
    else:
        print("ERROR: Download incomplete.")


def list_files(sock):
    """Request file list from server and display it."""
    response = send_command(sock, "LIST")
    print("\n--- Server Files ---")
    print(response)
    print("--------------------\n")


def main():
    """Connect to server and provide interactive menu."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((SERVER_HOST, SERVER_PORT))
        print(f"Connected to {SERVER_HOST}:{SERVER_PORT}")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    print("\nCommands: LIST, UPLOAD <filename>, DOWNLOAD <filename>, QUIT")

    while True:
        cmd = input("\n> ").strip()
        if not cmd:
            continue

        if cmd.upper() == "QUIT":
            send_command(client, "QUIT")
            break

        elif cmd.upper() == "LIST":
            list_files(client)

        elif cmd.upper().startswith("UPLOAD "):
            _, filename = cmd.split(maxsplit=1)
            upload_file(client, filename)

        elif cmd.upper().startswith("DOWNLOAD "):
            _, filename = cmd.split(maxsplit=1)
            download_file(client, filename)

        else:
            print("Unknown command. Try LIST, UPLOAD, DOWNLOAD, QUIT.")

    client.close()
    print("Disconnected.")


if __name__ == "__main__":
    main()