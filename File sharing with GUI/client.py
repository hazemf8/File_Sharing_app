import socket
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog

# ---------- Configuration ----------
HOST = '127.0.0.1'
PORT = 5555

# ---------- Helper ----------
def recv_line(reader):
    """Read exactly one newline-terminated line from the binary reader."""
    line = b''
    while True:
        ch = reader.read(1)
        if not ch:
            return b''
        if ch == b'\n':
            return line.decode()
        line += ch

# ---------- Main GUI Application ----------
class FileShareClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Sharing Client")
        self.geometry("600x500")
        self.resizable(True, True)
        
        # Socket and file objects (set after login)
        self.sock = None
        self.reader = None
        self.writer = None
        self.username = None

        # Show authentication screen on start
        self.show_auth_screen()

        # Cleanup on window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------- Authentication Screen ----------
    def show_auth_screen(self):
        """Create the initial Register/Login/Exit interface."""
        # Destroy previous frame if exists
        for widget in self.winfo_children():
            widget.destroy()

        self.auth_frame = ttk.Frame(self, padding=20)
        self.auth_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.auth_frame, text="File Sharing Client", font=("Arial", 16)).pack(pady=10)

        # Notebook for Register/Login tabs
        notebook = ttk.Notebook(self.auth_frame)
        notebook.pack(pady=10, fill=tk.BOTH, expand=True)

        # ----- Register Tab -----
        reg_tab = ttk.Frame(notebook)
        notebook.add(reg_tab, text="Register")

        ttk.Label(reg_tab, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.reg_user = ttk.Entry(reg_tab, width=30)
        self.reg_user.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(reg_tab, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.reg_pass = ttk.Entry(reg_tab, width=30, show="*")
        self.reg_pass.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(reg_tab, text="Register", command=self.register).grid(row=2, column=1, pady=10, sticky=tk.E)

        # ----- Login Tab -----
        login_tab = ttk.Frame(notebook)
        notebook.add(login_tab, text="Login")

        ttk.Label(login_tab, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.login_user = ttk.Entry(login_tab, width=30)
        self.login_user.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(login_tab, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.login_pass = ttk.Entry(login_tab, width=30, show="*")
        self.login_pass.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(login_tab, text="Login", command=self.login).grid(row=2, column=1, pady=10, sticky=tk.E)

        # Exit button below the notebook
        ttk.Button(self.auth_frame, text="Exit", command=self.on_closing).pack(pady=10)

    def register(self):
        """Handle registration request."""
        username = self.reg_user.get().strip()
        password = self.reg_pass.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Username and password cannot be empty.")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((HOST, PORT))
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", "Could not connect to server. Is it running?")
            return

        reader = sock.makefile('rb')
        writer = sock.makefile('wb')
        writer.write(f"REGISTER {username} {password}\n".encode())
        writer.flush()
        resp = recv_line(reader)

        if resp == "REGISTER_OK":
            messagebox.showinfo("Success", "Registration successful! You can now login.")
            self.reg_user.delete(0, tk.END)
            self.reg_pass.delete(0, tk.END)
        elif resp == "USER_EXISTS":
            messagebox.showerror("Error", "Username already exists. Please choose another.")
        else:
            messagebox.showerror("Error", f"Registration failed: {resp}")
        sock.close()

    def login(self):
        """Handle login request."""
        username = self.login_user.get().strip()
        password = self.login_pass.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Username and password cannot be empty.")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((HOST, PORT))
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", "Could not connect to server. Is it running?")
            return

        reader = sock.makefile('rb')
        writer = sock.makefile('wb')
        writer.write(f"LOGIN {username} {password}\n".encode())
        writer.flush()
        resp = recv_line(reader)

        if resp == "LOGIN_OK":
            self.username = username
            self.sock = sock
            self.reader = reader
            self.writer = writer
            self.show_file_ops_screen()
        else:
            messagebox.showerror("Login Failed", "Check username and password.")
            sock.close()

    # ---------- File Operations Screen ----------
    def show_file_ops_screen(self):
        """Create the main interface after successful login."""
        # Destroy old auth frame
        for widget in self.winfo_children():
            widget.destroy()

        self.file_frame = ttk.Frame(self, padding=20)
        self.file_frame.pack(fill=tk.BOTH, expand=True)

        # Header with username
        ttk.Label(self.file_frame, text=f"Logged in as: {self.username}", font=("Arial", 12, "bold")).pack(pady=5)

        # Output area (acts as file list + log)
        self.output_text = scrolledtext.ScrolledText(self.file_frame, wrap=tk.WORD, width=70, height=15)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=10)

        # Button frame
        btn_frame = ttk.Frame(self.file_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_file_list).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Upload", command=self.upload_file).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Download", command=self.download_file).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_file).grid(row=0, column=3, padx=5)
        ttk.Button(btn_frame, text="Share", command=self.share_file).grid(row=0, column=4, padx=5)
        ttk.Button(btn_frame, text="Logout", command=self.logout).grid(row=0, column=5, padx=5)

        # Automatically refresh file list
        self.refresh_file_list()

    def refresh_file_list(self):
        """Send LIST command and display the result."""
        try:
            self.writer.write(b"LIST\n")
            self.writer.flush()
        except Exception as e:
            messagebox.showerror("Error", f"Connection lost: {e}")
            self.logout()
            return

        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Your files on server:\n")
        while True:
            line = recv_line(self.reader)
            if not line or line == "END":
                break
            parts = line.split(maxsplit=1)
            if len(parts) == 1:
                self.output_text.insert(tk.END, f"  {parts[0]}  (unknown size)\n")
            else:
                self.output_text.insert(tk.END, f"  {parts[0]}  ({parts[1]} bytes)\n")
        self.output_text.see(tk.END)

    def upload_file(self):
        """Upload a chosen file to the server."""
        filepath = filedialog.askopenfilename(title="Select file to upload")
        if not filepath:
            return
        if not os.path.isfile(filepath):
            messagebox.showerror("Error", "File does not exist.")
            return
        fsize = os.path.getsize(filepath)
        try:
            self.writer.write(f"UPLOAD {os.path.basename(filepath)} {fsize}\n".encode())
            self.writer.flush()
        except Exception as e:
            messagebox.showerror("Error", f"Could not send upload request: {e}")
            return
        resp = recv_line(self.reader)
        if resp != "READY":
            messagebox.showerror("Error", f"Server rejected upload: {resp}")
            return
        # Send file data
        try:
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.writer.write(chunk)
            self.writer.flush()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send file data: {e}")
            return
        resp = recv_line(self.reader)
        if resp == "UPLOAD_OK":
            messagebox.showinfo("Success", f"File '{os.path.basename(filepath)}' uploaded.")
            self.refresh_file_list()
        else:
            messagebox.showerror("Error", f"Upload failed: {resp}")

    def download_file(self):
        """Download a file from the server."""
        fname = simpledialog.askstring("Download", "Enter filename to download:")
        if not fname:
            return
        try:
            self.writer.write(f"DOWNLOAD {fname}\n".encode())
            self.writer.flush()
        except Exception as e:
            messagebox.showerror("Error", f"Connection lost: {e}")
            return
        resp = recv_line(self.reader)
        if resp == "NOTFOUND":
            messagebox.showerror("Error", "File not found on server.")
            return
        elif resp.startswith("FILE "):
            parts = resp.split()
            if len(parts) < 3:
                messagebox.showerror("Error", "Malformed server response.")
                return
            srv_fname = parts[1]
            fsize = int(parts[2])
            save_path = filedialog.asksaveasfilename(title="Save as", initialfile=srv_fname)
            if not save_path:
                return  # user cancelled
            try:
                data = self.reader.read(fsize)
                with open(save_path, 'wb') as f:
                    f.write(data)
                messagebox.showinfo("Success", f"File saved as '{save_path}' ({fsize} bytes).")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
        else:
            messagebox.showerror("Error", f"Unexpected response: {resp}")

    def delete_file(self):
        """Delete a file from the server."""
        fname = simpledialog.askstring("Delete", "Enter filename to delete:")
        if not fname:
            return
        if not messagebox.askyesno("Confirm", f"Are you sure you want to delete '{fname}'?"):
            return
        try:
            self.writer.write(f"DELETE {fname}\n".encode())
            self.writer.flush()
        except Exception as e:
            messagebox.showerror("Error", f"Connection lost: {e}")
            return
        resp = recv_line(self.reader)
        if resp == "DELETED":
            messagebox.showinfo("Success", f"File '{fname}' deleted.")
            self.refresh_file_list()
        else:
            messagebox.showerror("Error", f"File not found or could not be deleted.")

    def share_file(self):
        """Share a file with another user."""
        fname = simpledialog.askstring("Share", "Enter the filename you want to share:")
        if not fname:
            return
        recipient = simpledialog.askstring("Share", "Enter the username to share with:")
        if not recipient:
            return
        try:
            self.writer.write(f"SHARE {fname} {recipient}\n".encode())
            self.writer.flush()
        except Exception as e:
            messagebox.showerror("Error", f"Connection lost: {e}")
            return
        resp = recv_line(self.reader)
        if resp == "SHARE_OK":
            messagebox.showinfo("Success", f"File '{fname}' shared with '{recipient}'.")
        elif resp == "FILE_NOT_FOUND":
            messagebox.showerror("Error", f"You don't own a file named '{fname}'.")
        elif resp == "USER_NOT_FOUND":
            messagebox.showerror("Error", f"User '{recipient}' does not exist.")
        else:
            messagebox.showerror("Error", f"Sharing failed: {resp}")

    def logout(self):
        """Logout and return to authentication screen."""
        if self.sock:
            try:
                self.writer.write(b"EXIT\n")
                self.writer.flush()
                recv_line(self.reader)  # ignore "BYE"
            except:
                pass
            finally:
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
                self.reader = None
                self.writer = None
                self.username = None
        self.show_auth_screen()

    def on_closing(self):
        """Clean up when closing the window."""
        if self.sock:
            self.logout()
        self.destroy()

if __name__ == "__main__":
    app = FileShareClient()
    app.mainloop()