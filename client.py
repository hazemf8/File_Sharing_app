import socket
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

HOST = 'x.x.x.x' # the static ip of the server
PORT = 5000 #any unused port

# ---------- Helper ----------
def recv_line(reader):
    line = b''
    while True:
        ch = reader.read(1)
        if not ch:
            return b''
        if ch == b'\n':
            return line.decode()
        line += ch

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

class FileShareClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Sharing Client")
        self.geometry("800x600")
        self.resizable(True, True)
        self.minsize(600, 450)

        style = ttk.Style(self)
        style.theme_use('clam')

        self.sock = None
        self.reader = None
        self.writer = None
        self.username = None
        self.file_list = []

        self.show_auth_screen()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_auth_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.auth_frame = ttk.Frame(self, padding=30)
        self.auth_frame.pack(fill=tk.BOTH, expand=True)

        container = ttk.Frame(self.auth_frame)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ttk.Label(container, text="File Sharing Client",
                  font=("Arial", 18, "bold")).pack(pady=(0, 20))

        notebook = ttk.Notebook(container)
        notebook.pack(pady=10, fill=tk.BOTH, expand=True)

        # Register tab
        reg_tab = ttk.Frame(notebook, padding=20)
        notebook.add(reg_tab, text="Register")

        ttk.Label(reg_tab, text="Username:").grid(row=0, column=0, padx=5, pady=8, sticky=tk.W)
        self.reg_user = ttk.Entry(reg_tab, width=30)
        self.reg_user.grid(row=0, column=1, padx=5, pady=8)

        ttk.Label(reg_tab, text="Password:").grid(row=1, column=0, padx=5, pady=8, sticky=tk.W)
        self.reg_pass = ttk.Entry(reg_tab, width=30, show="*")
        self.reg_pass.grid(row=1, column=1, padx=5, pady=8)

        ttk.Button(reg_tab, text="Register", command=self.register).grid(
            row=2, column=1, pady=15, sticky=tk.E)

        # Login tab
        login_tab = ttk.Frame(notebook, padding=20)
        notebook.add(login_tab, text="Login")

        ttk.Label(login_tab, text="Username:").grid(row=0, column=0, padx=5, pady=8, sticky=tk.W)
        self.login_user = ttk.Entry(login_tab, width=30)
        self.login_user.grid(row=0, column=1, padx=5, pady=8)

        ttk.Label(login_tab, text="Password:").grid(row=1, column=0, padx=5, pady=8, sticky=tk.W)
        self.login_pass = ttk.Entry(login_tab, width=30, show="*")
        self.login_pass.grid(row=1, column=1, padx=5, pady=8)

        ttk.Button(login_tab, text="Login", command=self.login).grid(
            row=2, column=1, pady=15, sticky=tk.E)

        ttk.Button(container, text="Exit", command=self.on_closing).pack(pady=15)

    def register(self):
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
            messagebox.showerror("Error", "Username already exists.")
        else:
            messagebox.showerror("Error", f"Registration failed: {resp}")
        sock.close()

    def login(self):
        username = self.login_user.get().strip()
        password = self.login_pass.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Username and password cannot be empty.")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((HOST, PORT))
        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", "Could not connect to server.")
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

    def show_file_ops_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.file_frame = ttk.Frame(self, padding=20)
        self.file_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(self.file_frame)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Logged in as:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(header, text=self.username, font=("Arial", 10, "bold")).pack(side=tk.LEFT)

        table_frame = ttk.Frame(self.file_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.tree = ttk.Treeview(table_frame, columns=("size",),
                                 show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="File Name")
        self.tree.heading("size", text="Size")
        self.tree.column("#0", width=400, stretch=True)
        self.tree.column("size", width=120, stretch=False)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Download", command=self._download_selected)
        self.context_menu.add_command(label="Delete", command=self._delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Share...", command=self._share_selected)
        self.tree.bind("<Button-2>", self._show_context_menu)
        self.tree.bind("<Button-3>", self._show_context_menu)

        btn_frame = ttk.Frame(self.file_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        refresh_btn = ttk.Button(btn_frame, text="Refresh", command=self.refresh_file_list)
        refresh_btn.pack(side=tk.LEFT, padx=2)

        self.upload_btn = ttk.Button(btn_frame, text="Upload", command=self.upload_file)
        self.upload_btn.pack(side=tk.LEFT, padx=2)

        self.download_btn = ttk.Button(btn_frame, text="Download",
                                       command=self._download_selected, state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=2)

        self.delete_btn = ttk.Button(btn_frame, text="Delete",
                                     command=self._delete_selected, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=2)

        self.share_btn = ttk.Button(btn_frame, text="Share",
                                    command=self._share_selected, state=tk.DISABLED)
        self.share_btn.pack(side=tk.LEFT, padx=2)

        logout_btn = ttk.Button(btn_frame, text="Logout", command=self.logout)
        logout_btn.pack(side=tk.RIGHT, padx=2)

        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.file_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN, anchor=tk.W, padding=(10, 2))
        status_bar.pack(fill=tk.X, pady=(5, 0))

        self.refresh_file_list()

    def refresh_file_list(self):
        try:
            self.writer.write(b"LIST\n")
            self.writer.flush()
        except Exception as e:
            self.status_var.set("Connection lost")
            messagebox.showerror("Error", f"Connection lost: {e}")
            self.logout()
            return

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.file_list.clear()

        while True:
            line = recv_line(self.reader)
            if not line or line == "END":
                break
            fsize_str, fname = line.split(maxsplit=1)
            try:
                fsize = int(fsize_str)
            except ValueError:
                fsize = 0
            self.file_list.append((fname, fsize))
            self.tree.insert("", tk.END, text=fname, values=(format_size(fsize),))

        self.status_var.set(f"Loaded {len(self.file_list)} file(s).")
        self._update_action_buttons()

    def _on_tree_select(self, event):
        self._update_action_buttons()

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._update_action_buttons()
            self.context_menu.post(event.x_root, event.y_root)

    def _update_action_buttons(self):
        selected = self.tree.selection()
        state = tk.NORMAL if selected else tk.DISABLED
        self.download_btn.config(state=state)
        self.delete_btn.config(state=state)
        self.share_btn.config(state=state)

    def _get_selected_filename(self):
        sel = self.tree.selection()
        if sel:
            return self.tree.item(sel[0], "text")
        return None

    def _download_selected(self):
        fname = self._get_selected_filename()
        if not fname:
            messagebox.showwarning("No file selected", "Please select a file.")
            return
        self.download_file(fname)

    def _delete_selected(self):
        fname = self._get_selected_filename()
        if not fname:
            messagebox.showwarning("No file selected", "Please select a file.")
            return
        self.delete_file(fname)

    def _share_selected(self):
        fname = self._get_selected_filename()
        if not fname:
            messagebox.showwarning("No file selected", "Please select a file.")
            return
        recipient = simpledialog.askstring("Share File", f"Share '{fname}' with user:")
        if recipient:
            self.share_file(fname, recipient)
        else:
            self.status_var.set("Share cancelled.")

    def upload_file(self):
        filepath = filedialog.askopenfilename(title="Select file to upload")
        if not filepath:
            return
        if not os.path.isfile(filepath):
            messagebox.showerror("Error", "File does not exist.")
            return
        fsize = os.path.getsize(filepath)
        fname = os.path.basename(filepath)
        try:
            self.writer.write(f"UPLOAD {fsize} {fname}\n".encode())
            self.writer.flush()
        except Exception as e:
            self.status_var.set("Upload failed: connection error")
            messagebox.showerror("Error", f"Could not send upload request: {e}")
            return

        resp = recv_line(self.reader)
        if resp == "FILE_EXISTS":
            self.status_var.set("Upload cancelled: file already exists")
            messagebox.showerror("Error",
                                 f"A file named '{fname}' already exists on the server.\n"
                                 "Please delete it first or rename your file.")
            return
        elif resp != "READY":
            self.status_var.set(f"Upload rejected: {resp}")
            messagebox.showerror("Error", f"Server rejected upload: {resp}")
            return

        try:
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.writer.write(chunk)
            self.writer.flush()
        except Exception as e:
            self.status_var.set("Upload failed during data transfer")
            messagebox.showerror("Error", f"Failed to send file data: {e}")
            return

        resp = recv_line(self.reader)
        if resp == "UPLOAD_OK":
            self.status_var.set(f"Uploaded '{fname}'")
            messagebox.showinfo("Success", f"File '{fname}' uploaded.")
            self.refresh_file_list()
        else:
            self.status_var.set(f"Upload failed: {resp}")
            messagebox.showerror("Error", f"Upload failed: {resp}")

    def download_file(self, fname):
        if not fname:
            return
        try:
            self.writer.write(f"DOWNLOAD {fname}\n".encode())
            self.writer.flush()
        except Exception as e:
            self.status_var.set("Download failed: connection lost")
            messagebox.showerror("Error", f"Connection lost: {e}")
            return
        resp = recv_line(self.reader)
        if resp == "NOTFOUND":
            self.status_var.set(f"File '{fname}' not found")
            messagebox.showerror("Error", "File not found on server.")
            return
        elif resp.startswith("FILE "):
            parts = resp.split(maxsplit=2)
            if len(parts) < 3:
                messagebox.showerror("Error", "Malformed server response.")
                return
            _, fsize_str, srv_fname = parts
            fsize = int(fsize_str)
            save_path = filedialog.asksaveasfilename(
                title="Save as", initialfile=srv_fname)
            if not save_path:
                self.status_var.set("Download cancelled.")
                return
            try:
                data = self.reader.read(fsize)
                with open(save_path, 'wb') as f:
                    f.write(data)
                self.status_var.set(f"Downloaded '{srv_fname}' ({fsize} bytes)")
                messagebox.showinfo("Success", f"File saved as '{save_path}'.")
            except Exception as e:
                self.status_var.set("Download failed while saving file")
                messagebox.showerror("Error", f"Failed to save file: {e}")
        else:
            self.status_var.set(f"Unexpected response: {resp}")
            messagebox.showerror("Error", f"Unexpected response: {resp}")

    def delete_file(self, fname):
        if not fname:
            return
        if not messagebox.askyesno("Confirm", f"Are you sure you want to delete '{fname}'?"):
            self.status_var.set("Deletion cancelled.")
            return
        try:
            self.writer.write(f"DELETE {fname}\n".encode())
            self.writer.flush()
        except Exception as e:
            self.status_var.set("Delete failed: connection lost")
            messagebox.showerror("Error", f"Connection lost: {e}")
            return
        resp = recv_line(self.reader)
        if resp == "DELETED":
            self.status_var.set(f"Deleted '{fname}'")
            messagebox.showinfo("Success", f"File '{fname}' deleted.")
            self.refresh_file_list()
        else:
            self.status_var.set(f"Delete failed: {resp}")
            messagebox.showerror("Error", "File not found or could not be deleted.")

    def share_file(self, fname, recipient):
        if not fname or not recipient:
            return
        try:
            self.writer.write(f"SHARE {fname} {recipient}\n".encode())
            self.writer.flush()
        except Exception as e:
            self.status_var.set("Share failed: connection lost")
            messagebox.showerror("Error", f"Connection lost: {e}")
            return
        resp = recv_line(self.reader)
        if resp == "SHARE_OK":
            self.status_var.set(f"Shared '{fname}' with '{recipient}'")
            messagebox.showinfo("Success", f"File '{fname}' shared with '{recipient}'.")
        elif resp == "FILE_NOT_FOUND":
            self.status_var.set("Share failed: you don't own this file")
            messagebox.showerror("Error", f"You don't own a file named '{fname}'.")
        elif resp == "USER_NOT_FOUND":
            self.status_var.set(f"Share failed: user '{recipient}' not found")
            messagebox.showerror("Error", f"User '{recipient}' does not exist.")
        else:
            self.status_var.set(f"Share failed: {resp}")
            messagebox.showerror("Error", f"Sharing failed: {resp}")

    def logout(self):
        if self.sock:
            try:
                self.writer.write(b"EXIT\n")
                self.writer.flush()
                recv_line(self.reader)
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
        if self.sock:
            self.logout()
        self.destroy()

if __name__ == "__main__":
    app = FileShareClient()
    app.mainloop()
