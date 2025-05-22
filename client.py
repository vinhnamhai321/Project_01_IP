import socket
import os
import sys
import threading
import re

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

def download_file(file_name):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER_HOST, SERVER_PORT))

    # Send GET command
    client.send(f"GET {file_name}".encode())

    file_info = client.recv(1024).decode()
    received_name, total_parts = file_info.split('|')

    if received_name == "FILE_NOT_FOUND":
        print(f"[-] File '{file_name}' not found on server.")
        client.close()
        return

    total_parts = int(total_parts)
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    with file_lock:
        unique_filename = get_unique_filename(SAVE_DIR, received_name)
        file_path = os.path.join(SAVE_DIR, unique_filename)
        if unique_filename != received_name:
            print(f"[i] File '{received_name}' exists. Saving as '{unique_filename}'.")

    with open(file_path, 'wb') as f:
        for part_num in range(1, total_parts + 1):
            chunk_size_data = client.recv(8).decode()
            chunk_size = int(chunk_size_data.strip())
            received = 0
            last_percent = -1

            while received < chunk_size:
                data = client.recv(min(4096, chunk_size - received))
                if not data:
                    break
                f.write(data)
                received += len(data)
                percent = int((received / chunk_size) * 100)
                if percent != last_percent:
                    last_percent = percent
                    sys.stdout.write(
                        f"\rDownloading '{file_name}' part {part_num} ... {percent}%"
                    )
                    sys.stdout.flush()
            print()
    print(f"\n[✓] File '{file_name}' downloaded successfully.")
    client.close()

def show_file_list():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_HOST, SERVER_PORT))
        client.send(b"LIST")
        files_list = client.recv(4096).decode()
        print("\n📁 Available files on server:")
        print(files_list)
        client.close()
    except Exception as e:
        print(f"Error getting file list: {e}")

def main():
    print("[*] File Downloader is running. Type 'exit' to quit.")
    show_file_list()

    while True:
        file_input = input("\nEnter file names to download (comma separated): ").strip()
        if file_input.lower() == 'exit':
            print("Exiting...")
            break

        file_names = [f.strip() for f in file_input.split(',') if f.strip()]
        if not file_names:
            print("Please enter at least one valid filename.")
            continue

        for file_name in file_names:
            thread = threading.Thread(target=download_file, args=(file_name,))
            thread.daemon = True  # Optional: don't block exit
            thread.start()

if __name__ == "__main__":
    main()
