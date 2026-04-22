# import socket
# import os

# # ------------------- Configuration -------------------
# SERVER_HOST = '127.0.0.1'
# SERVER_PORT = 5001
# BUFFER_SIZE = 4096
# CLIENT_FOLDER = 'client_files'   # Local folder for downloads/uploads
# os.makedirs(CLIENT_FOLDER, exist_ok=True)
# # -----------------------------------------------------

# def send_command(sock, command):
#     """Send a command and return the server response."""
#     sock.send(command.encode())
#     return sock.recv(BUFFER_SIZE).decode().strip()


# def upload_file(sock, filename):
#     """Upload a file from CLIENT_FOLDER to the server."""
#     filepath = os.path.join(CLIENT_FOLDER, filename)
#     if not os.path.isfile(filepath):
#         print(f"ERROR: File '{filename}' does not exist in {CLIENT_FOLDER}")
#         return

#     filesize = os.path.getsize(filepath)

#     # Send UPLOAD command with size
#     sock.send(f"UPLOAD {filename} {filesize}".encode())
#     response = sock.recv(BUFFER_SIZE).decode().strip()
#     if response != "READY":
#         print(f"Server error: {response}")
#         return

#     # Send file data
#     with open(filepath, 'rb') as f:
#         while chunk := f.read(BUFFER_SIZE):
#             sock.send(chunk)

#     # Wait for final acknowledgement
#     result = sock.recv(BUFFER_SIZE).decode().strip()
#     print(result)


# def download_file(sock, filename):
#     """Download a file from the server and save it in CLIENT_FOLDER."""
#     # Send DOWNLOAD command
#     sock.send(f"DOWNLOAD {filename}".encode())
#     response = sock.recv(BUFFER_SIZE).decode().strip()

#     if not response.startswith("SIZE"):
#         print(f"Server error: {response}")
#         return

#     # Extract file size
#     try:
#         filesize = int(response.split()[1])
#     except (IndexError, ValueError):
#         print("ERROR: Invalid server response.")
#         return

#     # Tell server we are ready
#     sock.send(b"READY")

#     # Receive file data
#     filepath = os.path.join(CLIENT_FOLDER, filename)
#     received = 0
#     with open(filepath, 'wb') as f:
#         while received < filesize:
#             chunk = sock.recv(min(BUFFER_SIZE, filesize - received))
#             if not chunk:
#                 break
#             f.write(chunk)
#             received += len(chunk)

#     if received == filesize:
#         print(f"SUCCESS: Downloaded {filename} ({filesize} bytes)")
#     else:
#         print("ERROR: Download incomplete.")


# def list_files(sock):
#     """Request file list from server and display it."""
#     response = send_command(sock, "LIST")
#     print("\n--- Server Files ---")
#     print(response)
#     print("--------------------\n")


# def delete_file(sock, filename):
#     """Request deletion of a file on the server."""
#     sock.send(f"DELETE {filename}".encode())
#     response = sock.recv(BUFFER_SIZE).decode().strip()
#     print(response)


# def main():
#     """Main client loop."""
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
#         sock.connect((SERVER_HOST, SERVER_PORT))
#         print(f"Connected to server at {SERVER_HOST}:{SERVER_PORT}")

#         while True:
#             print("\nOptions:")
#             print("1. List files")
#             print("2. Upload file")
#             print("3. Download file")
#             print("4. Delete file")
#             print("5. Quit")
#             choice = input("Enter your choice: ").strip()

#             if choice == '1':
#                 list_files(sock)
#             elif choice == '2':
#                 filename = input("Enter filename to upload: ").strip()
#                 if filename:
#                     upload_file(sock, filename)
#             elif choice == '3':
#                 filename = input("Enter filename to download: ").strip()
#                 if filename:
#                     download_file(sock, filename)
#             elif choice == '4':
#                 filename = input("Enter filename to delete from server: ").strip()
#                 if filename:
#                     delete_file(sock, filename)
#             elif choice == '5':
#                 send_command(sock, "QUIT")
#                 print("Disconnected.")
#                 break
#             else:
#                 print("Invalid choice. Please try again.")


# if __name__ == "__main__":
#     main()
import streamlit as st
import socket
import os
import pandas as pd

# ------------------- Configuration -------------------
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5001
BUFFER_SIZE = 4096
CLIENT_FOLDER = 'client_files'
os.makedirs(CLIENT_FOLDER, exist_ok=True)
# -----------------------------------------------------

# ------------------- Session State Initialization -------------------
if "socket" not in st.session_state:
    st.session_state.socket = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "file_list" not in st.session_state:
    st.session_state.file_list = []

# ------------------- Helper Functions -------------------
def connect_to_server():
    """Create and connect a socket."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, SERVER_PORT))
        st.session_state.socket = sock
        st.session_state.connected = True
        return True, "Connected successfully."
    except Exception as e:
        st.session_state.connected = False
        return False, f"Connection failed: {e}"

def disconnect():
    """Close socket and update state."""
    if st.session_state.socket:
        try:
            st.session_state.socket.send(b"QUIT")
            st.session_state.socket.close()
        except:
            pass
    st.session_state.socket = None
    st.session_state.connected = False
    st.session_state.file_list = []

def send_command(command):
    """Send a command and return response."""
    sock = st.session_state.socket
    if not sock:
        return None
    try:
        sock.send(command.encode())
        return sock.recv(BUFFER_SIZE).decode().strip()
    except Exception as e:
        st.error(f"Communication error: {e}")
        disconnect()
        return None

def list_server_files():
    """Fetch file list from server and update session state."""
    response = send_command("LIST")
    if response:
        files = response.split('\n') if response != "No files found." else []
        st.session_state.file_list = files
        return files
    return []

def upload_file_to_server(uploaded_file):
    """Upload a file from Streamlit uploader to server."""
    if not uploaded_file:
        return
    sock = st.session_state.socket
    filename = uploaded_file.name
    filesize = uploaded_file.size

    # Send UPLOAD command
    sock.send(f"UPLOAD {filename} {filesize}".encode())
    response = sock.recv(BUFFER_SIZE).decode().strip()
    if response != "READY":
        st.error(f"Server error: {response}")
        return

    # Send file data in chunks
    uploaded_file.seek(0)
    while chunk := uploaded_file.read(BUFFER_SIZE):
        sock.send(chunk)

    result = sock.recv(BUFFER_SIZE).decode().strip()
    if "SUCCESS" in result:
        st.success(result)
        list_server_files()  # Refresh list
    else:
        st.error(result)

def download_file_from_server(filename):
    """Download a file from server and save to CLIENT_FOLDER."""
    sock = st.session_state.socket
    sock.send(f"DOWNLOAD {filename}".encode())
    response = sock.recv(BUFFER_SIZE).decode().strip()

    if not response.startswith("SIZE"):
        st.error(f"Server error: {response}")
        return None

    try:
        filesize = int(response.split()[1])
    except:
        st.error("Invalid server response.")
        return None

    sock.send(b"READY")

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
        st.success(f"Downloaded {filename} ({filesize} bytes)")
        return filepath
    else:
        st.error("Download incomplete.")
        return None

def delete_file_on_server(filename):
    """Request deletion of a file on the server."""
    response = send_command(f"DELETE {filename}")
    if response and "SUCCESS" in response:
        st.success(response)
        list_server_files()
    else:
        st.error(response)

# ------------------- Streamlit UI -------------------
st.set_page_config(page_title="File Transfer Client", layout="wide")
st.title("📁 File Transfer Client (Streamlit GUI)")
st.markdown("Connect to the server and manage files.")

# Sidebar for connection
with st.sidebar:
    st.header("🔌 Connection")
    if not st.session_state.connected:
        if st.button("Connect to Server", type="primary"):
            success, msg = connect_to_server()
            if success:
                st.success(msg)
                list_server_files()
            else:
                st.error(msg)
    else:
        st.success(f"Connected to {SERVER_HOST}:{SERVER_PORT}")
        if st.button("Disconnect"):
            disconnect()
            st.rerun()

# Main area – only shown when connected
if st.session_state.connected:
    tab1, tab2, tab3, tab4 = st.tabs(["📋 List Files", "⬆️ Upload", "⬇️ Download", "🗑️ Delete"])

    # ----- List Files Tab -----
    with tab1:
        st.subheader("Files on Server")
        if st.button("Refresh List"):
            list_server_files()
        files = st.session_state.file_list
        if files:
            df = pd.DataFrame(files, columns=["Filename"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No files found on server.")

    # ----- Upload Tab -----
    with tab2:
        st.subheader("Upload a File")
        uploaded_file = st.file_uploader("Choose a file", type=None)
        if uploaded_file:
            st.write(f"Selected: **{uploaded_file.name}** ({uploaded_file.size} bytes)")
            if st.button("Upload to Server"):
                with st.spinner("Uploading..."):
                    upload_file_to_server(uploaded_file)

    # ----- Download Tab -----
    with tab3:
        st.subheader("Download a File")
        files = st.session_state.file_list
        if files:
            selected_file = st.selectbox("Select a file to download", files)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Download to Client Folder"):
                    with st.spinner("Downloading..."):
                        saved_path = download_file_from_server(selected_file)
                        if saved_path:
                            st.info(f"Saved to `{saved_path}`")
            with col2:
                # Option to download directly via browser
                local_path = os.path.join(CLIENT_FOLDER, selected_file)
                if os.path.exists(local_path):
                    with open(local_path, "rb") as f:
                        st.download_button(
                            label="Download to Your Computer",
                            data=f,
                            file_name=selected_file,
                            mime="application/octet-stream"
                        )
                else:
                    st.caption("(File not in local folder yet. Click left button first.)")
        else:
            st.info("No files available to download.")

    # ----- Delete Tab -----
    with tab4:
        st.subheader("Delete a File from Server")
        files = st.session_state.file_list
        if files:
            selected_file = st.selectbox("Select a file to delete", files, key="delete_select")
            if st.button("Delete Selected File", type="secondary"):
                with st.spinner("Deleting..."):
                    delete_file_on_server(selected_file)
        else:
            st.info("No files to delete.")
else:
    st.info("👈 Please connect to the server using the sidebar.")

# Cleanup on app close (optional – Streamlit doesn't guarantee execution)
# but disconnect is handled via button.