import socket
import threading
import os
from pathlib import Path

HOST        = '0.0.0.0'
PORT        = 5001
CHUNK_SIZE  = 1024 * 1024         # 1 MB
FILE_DIR    = 'server_files'

# ────────────────────────────────────────────────────────────────────────────────
def safe_join(base_dir: Path, user_path: str) -> Path:
    """
    Return an absolute Path that *must* stay inside *base_dir*,
    or raise ValueError if the user tries path traversal.
    """
    target = (base_dir / user_path).resolve()        # collapse '..', symlinks, etc.
    if base_dir not in target.parents and target != base_dir:
        raise ValueError("path traversal attempted")
    return target

# ────────────────────────────────────────────────────────────────────────────────
def handle_client(conn: socket.socket, addr):
    print(f"[+] Connected by {addr}")

    try:
        command = conn.recv(1024).decode(errors="replace").strip()
    except UnicodeDecodeError:
        conn.send(b"INVALID_COMMAND")
        conn.close()
        return

    # LIST ----------------------------------------------------------------------
    if command == "LIST":
        files = os.listdir(FILE_DIR)
        conn.send("\n".join(files).encode())
        conn.close()
        return

    # GET <filename> ------------------------------------------------------------
    elif command.startswith("GET "):
        requested_file = command[4:].strip()

        if not requested_file:
            conn.send(b"FILE_NOT_FOUND|0")
            conn.close()
            return

        try:
            base = Path(FILE_DIR).resolve()
            file_path = safe_join(base, requested_file)
        except ValueError:
            print(f"[!] Path-traversal blocked from {addr}: {requested_file!r}")
            conn.send(b"INVALID_PATH|0")
            conn.close()
            return

        # Normal file-transfer path
        if file_path.is_file():
            file_size     = file_path.stat().st_size
            total_chunks  = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
            conn.send(f"{requested_file}|{total_chunks}".encode())

            with file_path.open('rb') as f:
                for _ in range(total_chunks):
                    chunk = f.read(CHUNK_SIZE)
                    conn.send(f"{len(chunk):<8}".encode())   # 8-byte length prefix
                    conn.sendall(chunk)

            print(f"[✓] Sent '{requested_file}' to {addr}")
        else:
            conn.send(b"FILE_NOT_FOUND|0")

    # Any other verb ------------------------------------------------------------
    else:
        conn.send(b"INVALID_COMMAND")

    conn.close()

# ────────────────────────────────────────────────────────────────────────────────
def start_server():
    Path(FILE_DIR).mkdir(exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"[*] Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    start_server()
