import subprocess
import threading
import time
from tkinter import filedialog
import customtkinter as ctk
import queue

# 外観
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class KokoniControlPanel(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("KOKONI Controller")
        self.geometry("700x700")

        # 接続情報
        self.ip = "192.168.11.25:5555"
        self.port = "/dev/ttyS1"

        self.is_printing = False
        self.selected_file = None
        self.tty_queue = queue.Queue()
        
        self.read_process = None
        self.write_process = None

        # UI
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=170, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="KOKONI EC1", font=("Arial", 20, "bold")).pack(pady=20)

        # IPアドレス欄
        ctk.CTkLabel(self.sidebar, text="IP Address", font=("Arial", 12, "bold")).pack(pady=(0, 2))
        self.ip_var = ctk.StringVar(value=self.ip)
        self.ip_entry = ctk.CTkEntry(self.sidebar, textvariable=self.ip_var, width=140)
        self.ip_entry.pack(pady=(0, 15), padx=10)

        self.conn_btn = ctk.CTkButton(self.sidebar, text="CONNECT", command=self.connect)
        self.conn_btn.pack(pady=10, padx=10)

        # 純正アプリ制御
        ctk.CTkLabel(self.sidebar, text="Native App", font=("Arial", 12, "bold")).pack(pady=(15, 0))
        self.enable_app_btn = ctk.CTkButton(
            self.sidebar, text="Enable App", fg_color="#27AE60",
            command=self.enable_native_app
        )
        self.enable_app_btn.pack(pady=5, padx=10)
        
        self.disable_app_btn = ctk.CTkButton(
            self.sidebar, text="Disable App", fg_color="#555555",
            command=self.disable_native_app
        )
        self.disable_app_btn.pack(pady=5, padx=10)
        # ------------------------------

        ctk.CTkLabel(self.sidebar, text="Manual", font=("Arial", 12, "bold")).pack(pady=(20,0))
        self.home_btn = ctk.CTkButton(
            self.sidebar, text="HOME (G28)", fg_color="#D35400",
            command=lambda: threading.Thread(target=self.send_gcode, args=("G28",), daemon=True).start()
        )
        self.home_btn.pack(pady=5, padx=10)
        
        self.level_btn = ctk.CTkButton(
            self.sidebar, text="Leveling Pos",
            command=lambda: threading.Thread(target=self.send_gcode, args=("G28\nG1 Z50 F500",), daemon=True).start()
        )
        self.level_btn.pack(pady=5, padx=10)

        self.stop_btn = ctk.CTkButton(self.sidebar, text="STOP / KILL", fg_color="#C0392B", command=self.stop_print)
        self.stop_btn.pack(pady=30, padx=10)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Not Connected", font=("Arial", 40))
        self.status_label.pack(pady=20)

        self.file_info = ctk.CTkLabel(self.main_frame, text="G-codeファイルを選択してください", text_color="gray")
        self.file_info.pack(pady=5)
        self.file_btn = ctk.CTkButton(self.main_frame, text="ファイルを開く", command=self.select_file)
        self.file_btn.pack(pady=10)

        self.print_btn = ctk.CTkButton(
            self.main_frame, text="印刷開始", state="disabled", height=60, font=("Arial", 20, "bold"),
            command=self.start_print_thread
        )
        self.print_btn.pack(pady=10, fill="x", padx=60)

        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.pack(fill="x", padx=40, pady=(10,0))
        self.progress_bar.set(0)
        self.progress_text = ctk.CTkLabel(self.main_frame, text="進捗: 0%")
        self.progress_text.pack(pady=5)

        # ターミナル出力
        self.log_box = ctk.CTkTextbox(self.main_frame, height=150, font=("Consolas", 12), fg_color="#1E1E1E", text_color="#00FF00")
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        self.log_box.configure(state="disabled")

        # クリックでフォーカスを外す
        self.bind_all("<Button-1>", self.remove_focus)

    # 入力フォーカス
    def remove_focus(self, event):
        try:
            widget_class = event.widget.winfo_class()
            if widget_class not in ("Entry", "Text"):
                self.focus_set()
        except Exception:
            pass

    # ログ出力
    def log_message(self, message):
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        
        lines = int(self.log_box.index('end-1c').split('.')[0])
        if lines > 500:
            self.log_box.delete("1.0", f"{lines - 500}.0")
            
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # 純正アプリ切り替え
    def enable_native_app(self):
        ip = self.ip_var.get().strip()
        if not ip:
            self.log_message("Error: IPアドレスを入力してください。")
            return
        
        self.log_message("Enabling native printer app...")
        conn_res = subprocess.run(f"adb connect {ip}", shell=True, capture_output=True, text=True)
        if "failed" in conn_res.stdout.lower() or "cannot connect" in conn_res.stderr.lower():
            self.log_message("Error: プリンターに接続できません（電源がオフか、IPが間違っています）")
            return
            
        res = subprocess.run(f"adb -s {ip} shell \"pm enable com.dq.printer\"", shell=True, capture_output=True, text=True)
        if "not found" in res.stderr.lower() or "offline" in res.stderr.lower() or "error" in res.stderr.lower():
            self.log_message(f"Error: コマンドの実行に失敗しました - {res.stderr.strip()}")
        else:
            self.log_message("Native printer app is ENABLED.")

    def disable_native_app(self):
        ip = self.ip_var.get().strip()
        if not ip:
            self.log_message("Error: IPアドレスを入力してください。")
            return
            
        self.log_message("Disabling native printer app...")
        conn_res = subprocess.run(f"adb connect {ip}", shell=True, capture_output=True, text=True)
        if "failed" in conn_res.stdout.lower() or "cannot connect" in conn_res.stderr.lower():
            self.log_message("Error: プリンターに接続できません（電源がオフか、IPが間違っています）")
            return
            
        res = subprocess.run(f"adb -s {ip} shell \"pm disable com.dq.printer\"", shell=True, capture_output=True, text=True)
        if "not found" in res.stderr.lower() or "offline" in res.stderr.lower() or "error" in res.stderr.lower():
            self.log_message(f"Error: コマンドの実行に失敗しました - {res.stderr.strip()}")
        else:
            self.log_message("Native printer app is DISABLED.")

    # 接続
    def connect(self):
        self.ip = self.ip_var.get().strip()
        if not self.ip:
            self.log_message("Error: IPアドレスを入力してください。")
            return

        self.status_label.configure(text="Status: Connecting...")
        self.log_message(f"Connecting to {self.ip}...")
        self.update()

        try:
            conn_res = subprocess.run(
                f"adb connect {self.ip}", shell=True, capture_output=True, text=True
            )
            out_text = (conn_res.stdout + conn_res.stderr).lower()
            
            if "failed" in out_text or "cannot connect" in out_text or "no route to host" in out_text:
                raise Exception(f"ADB Connect Failed: {conn_res.stdout.strip()} {conn_res.stderr.strip()}")

            test_res = subprocess.run(
                f"adb -s {self.ip} shell echo 'test'", shell=True, capture_output=True, text=True
            )
            if "not found" in test_res.stderr.lower() or "offline" in test_res.stderr.lower():
                raise Exception("Device is offline or not found.")

            subprocess.run(f"adb -s {self.ip} root", shell=True)
            subprocess.run(f"adb -s {self.ip} shell \"pm disable com.dq.printer\"", shell=True)
            
            self.conn_btn.configure(text="CONNECTED", fg_color="green")
            self.status_label.configure(text="Status: Connected")
            self.log_message("Connected successfully. Printer app disabled.")

            self.read_process = subprocess.Popen(
                ["adb", "-s", self.ip, "shell", f"cat {self.port}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
            )
            
            self.write_process = subprocess.Popen(
                ["adb", "-s", self.ip, "shell", f"while read -r line; do echo \"$line\" > {self.port}; done"],
                stdin=subprocess.PIPE, text=True, bufsize=1
            )

            threading.Thread(target=self.read_tty_loop, daemon=True).start()

        except Exception as e:
            self.log_message(f"Error: {e}")
            self.status_label.configure(text="Status: Connect Error")
            self.conn_btn.configure(text="RETRY", fg_color="#C0392B")

    # ファイル選択 
    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("G-code files", "*.gcode")])
        if file_path:
            self.selected_file = file_path
            self.file_info.configure(text=f"選択中: {file_path.split('/')[-1]}", text_color="white")
            self.print_btn.configure(state="normal")
            self.log_message(f"Selected file: {self.selected_file}")

    # tty
    def read_tty_loop(self):
        if self.read_process:
            for line in self.read_process.stdout:
                line = line.strip()
                if line:
                    self.tty_queue.put(line)
                    self.log_message(f"[RECV] {line}")

    # G-code送信
    def send_gcode(self, gcode_lines):
        if not self.write_process:
            self.log_message("Error: Not connected to printer.")
            return

        if not isinstance(gcode_lines, list):
            gcode_lines = gcode_lines.split("\n")

        for line in gcode_lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue

            if line.startswith("M109"):
                self.after(0, lambda: self.status_label.configure(text="Status: Heating..."))

            try:
                self.write_process.stdin.write(line + '\n')
                self.write_process.stdin.flush()
                self.log_message(f"[SEND] {line}")
            except BrokenPipeError:
                self.log_message("Error: ADB pipe broken.")
                self.stop_print()
                return

            while True:
                try:
                    while not self.tty_queue.empty():
                        output = self.tty_queue.get_nowait()
                        if "ok" in output or output.startswith("k T:") or output.startswith("k "):
                            break
                    else:
                        time.sleep(0.01)
                        continue
                    break
                except Exception:
                    time.sleep(0.01)

            if line.startswith("M109"):
                self.after(0, lambda: self.status_label.configure(text="Status: Ready"))

    # 印刷
    def stop_print(self):
        self.is_printing = False
        
        # UIロック解除
        self.after(0, lambda: self.enable_app_btn.configure(state="normal"))
        self.after(0, lambda: self.disable_app_btn.configure(state="normal"))
        
        if not self.write_process:
            self.after(0, lambda: self.status_label.configure(text="Status: Not Connected"))
            self.after(0, lambda: self.print_btn.configure(state="normal"))
            self.after(0, lambda: self.progress_text.configure(text="未接続のため処理をスキップしました", text_color="red"))
            return
            
        self.after(0, lambda: self.status_label.configure(text="Status: Stopping..."))
        self.log_message("Stopping print. Sending kill commands...")
        
        subprocess.run(f"adb -s {self.ip} shell \"echo 'M104 S0' > {self.port}\"", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run(f"adb -s {self.ip} shell \"echo 'M140 S0' > {self.port}\"", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run(f"adb -s {self.ip} shell \"echo 'M84' > {self.port}\"", shell=True, stderr=subprocess.DEVNULL)

        time.sleep(1.0)
        
        if self.write_process:
            try:
                self.write_process.stdin.close()
            except Exception:
                pass
            self.write_process.terminate()
            self.write_process = None
            
        if self.read_process:
            self.read_process.terminate()
            self.read_process = None

        with self.tty_queue.mutex:
            self.tty_queue.queue.clear()

        subprocess.run(f"adb -s {self.ip} shell \"pm enable com.dq.printer\"", shell=True, stderr=subprocess.DEVNULL)
        
        self.after(0, lambda: self.status_label.configure(text="Status: Stopped"))
        if self.selected_file:
            self.after(0, lambda: self.print_btn.configure(state="normal"))
        self.after(0, lambda: self.progress_text.configure(text="印刷を中止しました", text_color="red"))
        self.log_message("Disconnected and printer app enabled.")

    def start_print_thread(self):
        if self.selected_file and not self.is_printing:
            with self.tty_queue.mutex:
                self.tty_queue.queue.clear()
                
            self.is_printing = True
            
            # UIロック
            self.print_btn.configure(state="disabled")
            self.enable_app_btn.configure(state="disabled")
            self.disable_app_btn.configure(state="disabled")
            
            self.log_message("--- Print Started ---")
            threading.Thread(target=self.print_process, daemon=True).start()

    def print_process(self):
        with open(self.selected_file, 'r') as f:
            lines = f.readlines()
            total = len(lines)
            for i, line in enumerate(lines):
                if not self.is_printing:
                    self.log_message("--- Print Aborted ---")
                    break
                clean_line = line.strip()
                if not clean_line or clean_line.startswith(';'):
                    continue
                self.send_gcode(clean_line)
                
                if i % 10 == 0 or i == total - 1:
                    val = (i+1)/total
                    # プログレスバーの更新をメインスレッドに
                    self.after(0, lambda v=val: self.progress_bar.set(v))
                    self.after(0, lambda v=val, idx=i: self.progress_text.configure(text=f"進捗: {int(v*100)}% ({idx+1}/{total})"))

        self.is_printing = False
        
        # UIロック解除とステータス更新をメインスレッドに
        def _finish_ui():
            self.print_btn.configure(state="normal")
            self.enable_app_btn.configure(state="normal")
            self.disable_app_btn.configure(state="normal")
            self.status_label.configure(text="Status: Finished")
            self.progress_text.configure(text="印刷完了！", text_color="green")
            
        self.after(0, _finish_ui)
        self.log_message("--- Print Finished ---")

if __name__ == "__main__":
    app = KokoniControlPanel()
    app.mainloop()
