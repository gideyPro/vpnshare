import customtkinter as ctk
import tkinter as tk
import threading
import socket
import subprocess
import os
import sys
import time
import shutil
import json
from PIL import Image, ImageDraw, ImageTk
from plyer import notification

# Configuration
SEARCH_PORT = 8022
APP_NAME = "VPN Share Connect"
CONFIG_FILE = "config.json"
ICON_FILENAME = "icon.png"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class FloatingButton(ctk.CTkToplevel):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.title("VPN Floating")
        
        # Initial position
        screen_width = self.winfo_screenwidth()
        self.geometry(f"60x60+{screen_width - 80}+100")
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Make transparent-ish if possible
        self.configure(bg="black") 
        
        # Container Frame
        self.frame = ctk.CTkFrame(self, width=60, height=60, corner_radius=30, fg_color="#1f538d")
        self.frame.pack(fill="both", expand=True)
        
        # Icon/Label
        self.icon_label = ctk.CTkLabel(self.frame, text="VPN", text_color="white", font=("Arial", 14, "bold"))
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        icon_path = resource_path(ICON_FILENAME)
        if os.path.exists(icon_path):
             try:
                 pil_img = Image.open(icon_path).resize((40, 40))
                 self.img = ctk.CTkImage(pil_img, size=(40, 40))
                 self.icon_label.configure(image=self.img, text="")
             except: pass

        # Context Menu (Right Click)
        self.menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        self.menu.add_command(label="Show Window", command=self.on_click)
        self.menu.add_command(label="Connect", command=lambda: self.main_app.start_connection())
        self.menu.add_command(label="Disconnect", command=lambda: self.main_app.stop_connection("Quick Menu"))
        self.menu.add_separator()
        self.menu.add_command(label="Quit", command=self.main_app.quit_app)

        # Events
        self.frame.bind("<ButtonPress-1>", self.start_drag)
        self.frame.bind("<B1-Motion>", self.do_drag)
        self.frame.bind("<ButtonRelease-1>", self.stop_drag)
        self.frame.bind("<Button-3>", self.show_menu)
        
        self.icon_label.bind("<ButtonPress-1>", self.start_drag)
        self.icon_label.bind("<B1-Motion>", self.do_drag)
        self.icon_label.bind("<ButtonRelease-1>", self.stop_drag)
        self.icon_label.bind("<Button-3>", self.show_menu)

        self._drag_data = {"x": 0, "y": 0, "moved": False}
        self.withdraw() # Hidden by default
        self.set_status("disconnected")

    def show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def set_status(self, status):
        # Colors
        colors = {
            "connected": "#2CC985",    # Green
            "connecting": "#FFA500",   # Orange
            "disconnected": "#FF474C"  # Red
        }
        color = colors.get(status, "#1f538d")
        
        # Update frame color
        try:
            self.frame.configure(fg_color=color)
        except: pass

    def start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["moved"] = False

    def do_drag(self, event):
        # Calculate delta
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        
        # If moved significantly, mark as moved
        if abs(dx) > 2 or abs(dy) > 2:
             self._drag_data["moved"] = True

        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def stop_drag(self, event):
        if not self._drag_data["moved"]:
            self.on_click()
        self._drag_data["moved"] = False

    def on_click(self):
        self.withdraw()
        self.main_app.show_from_floating()

class VPNShareApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("500x600") # Compact Size
        self.center_window()
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Set Icon
        icon_path = resource_path(ICON_FILENAME)
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                self.iconphoto(False, ImageTk.PhotoImage(img))
            except Exception as e:
                print(f"Failed to load window icon: {e}")

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) 
        self.grid_rowconfigure(6, weight=1) # Less weight for console

        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, height=40)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_label = ctk.CTkLabel(self.header_frame, text="VPN Share Connect", font=ctk.CTkFont(size=18, weight="bold"))
        self.header_label.pack(pady=5)

        # Controls
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.scan_btn = ctk.CTkButton(self.controls_frame, text="Scan Devices", width=120, command=self.start_scan)
        self.scan_btn.pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(self.controls_frame, text="Ready", text_color="gray")
        self.status_label.pack(side="left", padx=10)

        # Device List - Compact Height
        self.device_scroll = ctk.CTkScrollableFrame(self, height=80, label_text="Found Devices")
        self.device_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=2)

        # Input Fields
        self.details_frame = ctk.CTkFrame(self)
        self.details_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
        self.ip_entry = ctk.CTkEntry(self.details_frame, placeholder_text="IP Address")
        self.ip_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        self.user_entry = ctk.CTkEntry(self.details_frame, placeholder_text="Username", width=100)
        self.user_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        self.pass_entry = ctk.CTkEntry(self.details_frame, placeholder_text="Password", show="*", width=100)
        self.pass_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # Options
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=0)
        
        self.auto_reconnect_var = ctk.BooleanVar(value=True)
        self.auto_reconnect_chk = ctk.CTkCheckBox(self.options_frame, text="Auto Reconnect", variable=self.auto_reconnect_var)
        self.auto_reconnect_chk.pack(side="left", padx=5)
        
        self.save_pass_var = ctk.BooleanVar(value=False)
        self.save_pass_chk = ctk.CTkCheckBox(self.options_frame, text="Save Password", variable=self.save_pass_var)
        self.save_pass_chk.pack(side="left", padx=5)

        self.connect_btn = ctk.CTkButton(self.details_frame, text="Connect", width=100, fg_color="green", hover_color="darkgreen", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=5, pady=5)

        # Embedded Console
        self.console_label = ctk.CTkLabel(self, text="Log:", anchor="w", font=ctk.CTkFont(size=11))
        self.console_label.grid(row=5, column=0, sticky="w", padx=10, pady=(2,0))
        
        self.console_box = ctk.CTkTextbox(self, font=("Courier", 11))
        self.console_box.grid(row=6, column=0, sticky="nsew", padx=10, pady=5)
        self.console_box.configure(state="disabled")

        # Variables
        self.devices = []
        self.is_scanning = False
        self.is_connected = False
        self.connection_process = None
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.sudo_password = None 
        
        # Floating Widget
        self.floating_widget = FloatingButton(self)

        # Load Config
        self.load_config()

        # Protocol - Intercept close
        self.protocol("WM_DELETE_WINDOW", self.switch_to_floating)
        
        # Prompt for sudo immediately
        self.after(500, self.prompt_sudo)

    def center_window(self):
        self.update_idletasks()
        width = 500
        height = 600
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def prompt_sudo(self):
        # Using a dialog to ask for sudo password once
        dialog = ctk.CTkInputDialog(text="Enter your PC Login (sudo) Password:\n(Required for sshuttle network routing)", title="Authentication Required")
        pwd = dialog.get_input()
        
        if pwd:
            if self.verify_sudo(pwd):
                self.sudo_password = pwd
                self.log_to_console("Sudo authentication successful. You won't be asked again.")
            else:
                self.log_to_console("Error: Sudo password incorrect. Relaunch to try again.")
        else:
            self.log_to_console("Warning: No sudo password provided. Automatic connection might fail.")

    def verify_sudo(self, pwd):
        # Verify by running a dummy sudo command
        try:
            # -S accepts password from stdin
            p = subprocess.Popen(['sudo', '-S', '-v', '-k'], stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = p.communicate(input=f'{pwd}\n'.encode())
            return p.returncode == 0
        except:
            return False

    # --- Scanning Logic ---
    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def start_scan(self):
        if self.is_scanning: return
        self.is_scanning = True
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.log_to_console("Scanning local network for SSH devices...")
        
        for widget in self.device_scroll.winfo_children():
            widget.destroy()
        self.devices = []

        threading.Thread(target=self.scan_subnet, daemon=True).start()

    def scan_subnet(self):
        local_ip = self.get_local_ip()
        base_ip = '.'.join(local_ip.split('.')[:-1])
        threads = []
        
        def check_ip(ip):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0) 
            try:
                if s.connect_ex((ip, SEARCH_PORT)) == 0:
                    try:
                        banner = s.recv(1024).decode('utf-8', errors='ignore')
                        if "SSH" in banner:
                            self.add_device(ip)
                    except: pass
            except: pass
            finally: s.close()

        for i in range(1, 255):
            target_ip = f"{base_ip}.{i}"
            if target_ip == local_ip: continue
            t = threading.Thread(target=check_ip, args=(target_ip,))
            threads.append(t)
            t.start()
            if len(threads) > 50:
                for t in threads: t.join()
                threads = []
        
        for t in threads: t.join()
        self.after(0, self.finish_scan)

    def add_device(self, ip):
        self.after(0, lambda: self._add_device_ui(ip))

    def _add_device_ui(self, ip):
        btn = ctk.CTkButton(self.device_scroll, text=f"SSH Device at {ip}", command=lambda: self.select_device(ip), fg_color="transparent", border_width=1, text_color=("gray10", "gray90"))
        btn.pack(fill="x", padx=5, pady=2)
        self.devices.append(ip)

    def select_device(self, ip):
        self.ip_entry.delete(0, "end")
        self.ip_entry.insert(0, ip)

    def finish_scan(self):
        self.is_scanning = False
        self.scan_btn.configure(state="normal", text="Scan for Devices")
        if not self.devices: self.log_to_console("No devices found.")
        else: self.log_to_console(f"Found {len(self.devices)} devices.")
        if self.devices and not self.ip_entry.get():
            self.select_device(self.devices[0])

    # --- Connection Logic ---

    def toggle_connection(self):
        if self.is_connected:
            self.stop_connection("User requested disconnect.")
        else:
            self.start_connection()

    def start_connection(self):
        ip = self.ip_entry.get()
        user = self.user_entry.get()
        password = self.pass_entry.get()
        
        if not ip or not user:
            self.log_to_console("Error: Please enter IP and Username.")
            return

        self.save_config(ip, user, password if self.save_pass_var.get() else "")
        self.is_connected = True
        self.connect_btn.configure(text="Disconnect", fg_color="red", hover_color="darkred")
        self.stop_event.clear()
        
        # Update Status
        self.floating_widget.set_status("connecting")
        
        if password and not shutil.which("sshpass"):
             self.log_to_console("Warning: 'sshpass' not found. Password auto-fill will fail.")
             self.log_to_console("Please install it: sudo apt install sshpass")

        self.monitor_thread = threading.Thread(target=self.connection_loop, args=(ip, user, password), daemon=True)
        self.monitor_thread.start()

    def connection_loop(self, ip, user, password):
        while not self.stop_event.is_set():
            self.log_to_console(f"Connecting to {user}@{ip}...")
            self.after(0, lambda: self.floating_widget.set_status("connecting"))
            
            # Escape password for shell usage
            # We need to be careful with quotes. simple approach: single quote the password, escape single quotes.
            if password:
                safe_pass = password.replace("'", "'\\''")
            
            # SSH Options to bypass headers
            ssh_opts = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
            
            # Construct the inner command string
            # We want: export SSHPASS='...'; sshuttle --dns -e 'sshpass -e ssh -o ...' -r ...
            
            cmd_str = ""
            ssh_cmd_part = f"ssh {ssh_opts}"
            
            if password and shutil.which("sshpass"):
                 cmd_str += f"export SSHPASS='{safe_pass}'; "
                 ssh_cmd_part = f"sshpass -e {ssh_cmd_part}"
            
            cmd_str += f"sshuttle --dns -e '{ssh_cmd_part}' -r {user}@{ip}:{SEARCH_PORT} 0.0.0.0/0 -x {ip}"
            
            # Now wrap this entire command string in sudo/pkexec bash -c
            # This ensures the env var stays with the process
            
            final_popen_cmd = []
            
            if self.sudo_password:
                # sudo -S -p '' bash -c "cmd_str"
                final_popen_cmd = ["sudo", "-S", "-p", "", "bash", "-c", cmd_str]
            else:
                # pkexec bash -c "cmd_str"
                final_popen_cmd = ["pkexec", "bash", "-c", cmd_str]

            try:
                # If using sudo -S, we must pipe stdin
                input_bytes = None
                if self.sudo_password:
                    input_bytes = f"{self.sudo_password}\n".encode()

                self.connection_process = subprocess.Popen(
                    final_popen_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE if self.sudo_password else None,
                    universal_newlines=False, # We need raw bytes for sudo stdin
                    bufsize=0 # Unbuffered
                )
                
                # Write sudo password if needed
                if self.sudo_password:
                    try:
                        self.connection_process.stdin.write(input_bytes)
                        self.connection_process.stdin.close()
                    except BrokenPipeError:
                        pass # Process died instantly?
                    except Exception as e:
                        print(f"Stdin error: {e}")

                # Assume active
                self.after(0, lambda: self.floating_widget.set_status("connected"))
                
                # Handle output (bytes)
                while True:
                    line = self.connection_process.stdout.readline()
                    if not line and self.connection_process.poll() is not None:
                        break
                    if line:
                        try:
                            # Decode for log
                            text = line.decode('utf-8', errors='replace').strip()
                            self.log_to_console(text)
                        except: pass
                
                return_code = self.connection_process.poll()
                
                if self.stop_event.is_set():
                    break 

                self.log_to_console(f"Connection process exited with code {return_code}.")
                
                # Auto-scroll to bottom on error
                self.after(0, self.console_box.see, "end")
                
                self.notify_user("VPN Connection Lost", "The connection was interrupted.")
                self.after(0, lambda: self.floating_widget.set_status("disconnected"))
                
                if self.auto_reconnect_var.get():
                    self.log_to_console("Reconnecting in 3 seconds...")
                    self.after(0, lambda: self.floating_widget.set_status("connecting"))
                    time.sleep(3)
                else:
                    self.after(0, lambda: self.stop_connection("Connection lost."))
                    break

            except Exception as e:
                self.log_to_console(f"Error starting process: {e}")
                self.after(0, lambda: self.floating_widget.set_status("disconnected"))
                time.sleep(5)

    def stop_connection(self, reason=""):
        self.stop_event.set()
        self.floating_widget.set_status("disconnected")
        
        if self.connection_process:
            self.log_to_console("Stopping process...")
            try:
                self.connection_process.terminate()
                self.connection_process.wait(timeout=2)
            except:
                try: self.connection_process.kill()
                except: pass
            
            # Kill sshuttle with sudo if we have pass
            kill_cmd = ["pkill", "sshuttle"]
            if self.sudo_password:
                 try:
                     kp = subprocess.Popen(["sudo", "-S"] + kill_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                     kp.communicate(input=f"{self.sudo_password}\n".encode())
                 except: pass
            else:
                 subprocess.run(["pkexec"] + kill_cmd, stderr=subprocess.DEVNULL)

        self.is_connected = False
        self.connect_btn.configure(text="Connect", fg_color="green", hover_color="darkgreen")
        self.log_to_console(f"Disconnected: {reason}")
        self.connection_process = None

    def log_to_console(self, text):
        self.after(0, lambda: self._append_console(text))

    def _append_console(self, text):
        # We don't disable state, so user can select text. We just insert at end.
        # But to prevent editing, we rely on CTkTextbox behavior or bind events if strictly needed.
        # Simple fix: Just enable, insert, disable? Disabled prevents copy.
        # Better: keep normal but block typing? CTkTextbox is tricky.
        # Actually enabling, inserting, and disabling PREVENTS copy in Tkinter usually.
        # Workaround: Leave it normal but bind <Key> to break.
        
        # NOTE: For now, I'll switch to state=normal so you can copy, but I'll make it read-only log style ideally.
        # But 'disabled' with CTk usually disables interaction. 
        # I will keep it 'normal' so you can select.
        
        self.console_box.configure(state="normal")
        self.console_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
        self.console_box.see("end")
        # self.console_box.configure(state="disabled") # Disabled prevents selection
        
        # To prevent editing, we can do this once in init:
        # self.console_box.bind("<Key>", lambda e: "break")
        pass

    def notify_user(self, title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                app_name=APP_NAME,
                timeout=5
            )
        except Exception as e:
            print(f"Notification error: {e}")

    # --- Config ---
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    if "last_ip" in data: self.ip_entry.insert(0, data["last_ip"])
                    if "last_user" in data: self.user_entry.insert(0, data["last_user"])
                    if "last_pass" in data:
                        self.pass_entry.insert(0, data["last_pass"])
                        if data["last_pass"]: self.save_pass_var.set(True)
        except: pass

    def save_config(self, ip, user, password):
        try:
            data = {"last_ip": ip, "last_user": user, "last_pass": password}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f)
        except: pass

    # --- Floating / Window Logic ---
    def switch_to_floating(self):
        # Only switch if we are explicitly minimizing (iconic) or called directly
        # We withdraw main window and show floating
        self.withdraw()
        self.floating_widget.deiconify()
        self.notify_user("VPN Share", "Switched to floating widget.")

    def show_from_floating(self):
        self.deiconify()
        self.state("normal") # Restore from iconic if needed
        self.lift()
        self.focus_force()

    def check_minimize_event(self, event):
        # Check if the main window state is 'iconic' (minimized)
        if event.widget == self:
            if self.state() == 'iconic':
                self.switch_to_floating()

    def quit_app(self):
        # Clean shutdown
        self.stop_connection("App quitting")
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = VPNShareApp()
    
    # Behavior:
    # 1. 'X' Button -> Close App (Quit)
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    
    # 2. '-' Button (Minimize) -> Switch to Floating
    # We bind to the <Unmap> event to detect when window is minimized (iconified)
    app.bind("<Unmap>", app.check_minimize_event)
    
    app.mainloop()
