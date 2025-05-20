import socket
import threading
import os

HOST = '0.0.0.0'
PORT = 5001
CHUNK_SIZE = 1024 * 1024  # 1MB
FILE_DIR = 'server_files'

def handle_client(conn, addr):
    print(f"[+] Connected by {addr}")

    command = conn.recv(1024).decode().strip()

    if command == "LIST":
        files = os.listdir(FILE_DIR)
        files_list_str = '\n'.join(files)
        conn.send(files_list_str.encode())
        conn.close()
        return

    elif command.startswith("GET "):
        requested_file = command[4:].strip()

        if not requested_file:
            conn.send("FILE_NOT_FOUND|0".encode())
            conn.close()
            return

        file_path = os.path.join(FILE_DIR, requested_file)

        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
            conn.send(f"{requested_file}|{total_chunks}".encode())

            with open(file_path, 'rb') as f:
                for _ in range(total_chunks):
                    chunk = f.read(CHUNK_SIZE)
                    conn.send(f"{len(chunk):<8}".encode())
                    conn.sendall(chunk)

            print(f"[✓] Sent '{requested_file}' to {addr}")
        else:
            conn.send("FILE_NOT_FOUND|0".encode())

    else:
        conn.send(b"INVALID_COMMAND")

    conn.close()

def start_server():
    if not os.path.exists(FILE_DIR):
        os.makedirs(FILE_DIR)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[*] Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()
