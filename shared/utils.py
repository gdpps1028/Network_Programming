import socket
import struct
import json
import os
import hashlib

def send_json(sock, data):
    """Sends a JSON object over the socket with a length prefix."""
    json_str = json.dumps(data)
    json_bytes = json_str.encode('utf-8')
    # Send 4-byte length prefix (big-endian)
    sock.sendall(struct.pack('>I', len(json_bytes)))
    sock.sendall(json_bytes)

def recv_json(sock):
    """Receives a JSON object from the socket."""
    # Read 4-byte length prefix
    len_bytes = recv_all(sock, 4)
    if not len_bytes:
        return None
    msg_len = struct.unpack('>I', len_bytes)[0]
    # Read the JSON data
    json_bytes = recv_all(sock, msg_len)
    if not json_bytes:
        return None
    return json.loads(json_bytes.decode('utf-8'))

def recv_all(sock, n):
    """Helper to receive exactly n bytes."""
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def send_file(sock, file_path):
    """Sends a file over the socket."""
    file_size = os.path.getsize(file_path)
    # Send file size first
    sock.sendall(struct.pack('>Q', file_size))
    
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            sock.sendall(chunk)

def recv_file(sock, dest_path):
    """Receives a file from the socket."""
    # Read file size
    size_bytes = recv_all(sock, 8)
    if not size_bytes:
        return False
    file_size = struct.unpack('>Q', size_bytes)[0]
    
    with open(dest_path, 'wb') as f:
        remaining = file_size
        while remaining > 0:
            chunk_size = 4096 if remaining > 4096 else remaining
            chunk = recv_all(sock, chunk_size)
            if not chunk:
                return False
            f.write(chunk)
            remaining -= len(chunk)
    return True

def calculate_file_hash(file_path):
    """Calculates SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
