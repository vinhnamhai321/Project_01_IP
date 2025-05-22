import socket
import os
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5001
CHUNK_SIZE = 1024 * 1024
SAVE_DIR = 'client_files'

file_lock = threading.Lock()

def get_unique_filename(save_dir, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(save_dir, new_filename)):
        new_filename = f"{base}({counter}){ext}"
        counter += 1
    return new_filename

class FileDownloaderGUI:
    def __init__(self, root):
        self.root = root
        root.title("File Downloader")

        self.output_area = scrolledtext.ScrolledText(root, height=20, width=80, state='disabled')
        self.output_area.pack(pady=10)

        self.input_field = tk.Entry(root, width=60)
        self.input_field.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))
        self.input_field.bind("<Return>", lambda event: self.start_download())

        self.download_btn = tk.Button(root, text="Download", command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=10, pady=(0, 10))

        self.refresh_btn = tk.Button(root, text="Refresh File List", command=self.show_file_list)
        self.refresh_btn.pack(side=tk.LEFT, padx=10, pady=(0, 10))

        self.show_file_list()

    def append_output(self, message):
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, message + '\n')
        self.output_area.yview(tk.END)
        self.output_area.config(state='disabled')

    def show_file_list(self):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((SERVER_HOST, SERVER_PORT))
            client.send(b"LIST")
            files_list = client.recv(4096).decode()
            client.close()
            self.append_output("📁 Available files:\n" + files_list)
        except Exception as e:
            self.append_output(f"Error retrieving file list: {e}")

    def download_file(self, file_name):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((SERVER_HOST, SERVER_PORT))
            client.send(f"GET {file_name}".encode())
            file_info = client.recv(1024).decode()
            received_name, total_parts = file_info.split('|')

            if received_name == "FILE_NOT_FOUND":
                self.append_output(f"[-] File '{file_name}' not found on server.")
                client.close()
                return

            total_parts = int(total_parts)
            if not os.path.exists(SAVE_DIR):
                os.makedirs(SAVE_DIR)

            with file_lock:
                unique_filename = get_unique_filename(SAVE_DIR, received_name)
                file_path = os.path.join(SAVE_DIR, unique_filename)
                if unique_filename != received_name:
                    self.append_output(f"[i] File '{received_name}' exists. Saving as '{unique_filename}'.")

            with open(file_path, 'wb') as f:
                for part_num in range(1, total_parts + 1):
                    chunk_size_data = client.recv(8).decode()
                    chunk_size = int(chunk_size_data.strip())
                    received = 0
                    while received < chunk_size:
                        data = client.recv(min(4096, chunk_size - received))
                        if not data:
                            break
                        f.write(data)
                        received += len(data)

                    # After full part received
                    self.append_output(f"Downloading '{file_name}' part {part_num} ... 100%")

            self.append_output(f"[✓] File '{file_name}' downloaded successfully.")
            client.close()

        except Exception as e:
            self.append_output(f"Error downloading '{file_name}': {e}")


    def start_download(self):
        file_input = self.input_field.get().strip()
        if not file_input:
            messagebox.showinfo("Input Required", "Please enter at least one filename.")
            return

        file_names = [f.strip() for f in file_input.split(',') if f.strip()]
        self.input_field.delete(0, tk.END)
        for file_name in file_names:
            threading.Thread(target=self.download_file, args=(file_name,), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = FileDownloaderGUI(root)
    root.mainloop()
