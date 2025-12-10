import socket
import threading
import sys
import os

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocol import *
from shared.utils import send_json, recv_json
from server.database import Database
from server.developer_service import DeveloperService
from server.lobby_service import LobbyService
from server.store_service import StoreService

HOST = '0.0.0.0'
PORT = 8888

class GameServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.db = Database()
        self.dev_service = DeveloperService(self.db)
        self.clients = {} # socket -> user_info
        self.lobby_service = LobbyService(self.db, self.broadcast)
        self.store_service = StoreService(self.db)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Try to bind, handle errors gracefully
        try:
            server_socket.bind((self.host, self.port))
        except OSError as e:
            print(f"\nError: Failed to bind to {self.host}:{self.port}")
            if e.errno == 98 or e.errno == 48:  # EADDRINUSE on Linux/Mac
                print(f"Port {self.port} is already in use.")
                print(f"Try running with a different port: python server/main.py --port <PORT>")
            else:
                print(f"Socket error: {e}")
            sys.exit(1)
            
        server_socket.listen(5)
        print(f"\nServer started successfully!")
        print(f"Binding address: {self.host}:{self.port}")
        
        # If binding to all interfaces (0.0.0.0), show the actual IP clients should use
        if self.host == '0.0.0.0':
            local_ip = self.get_local_ip()
            print(f"Clients can connect to: {local_ip}:{self.port}")
            print(f"(Use this IP address in your client configuration)\n")

        try:
            while True:
                client_sock, addr = server_socket.accept()
                print(f"New connection from {addr}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_sock,))
                client_thread.start()
        except KeyboardInterrupt:
            print("\nServer stopping...")
        finally:
            server_socket.close()

    def handle_client(self, sock):
        try:
            while True:
                msg = recv_json(sock)
                if not msg:
                    break
                
                response = self.process_message(sock, msg)
                if response:
                    send_json(sock, response)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            print("Client disconnected")
            self.handle_disconnect(sock)
            sock.close()

    def process_message(self, sock, msg):
        msg_type = msg.get("type")
        data = msg.get("data")
        
        print(f"Received message: {msg_type}")

        if msg_type == MSG_LOGIN:
            return self.handle_login(sock, data)
        elif msg_type == MSG_REGISTER:
            return self.handle_register(data)
        elif msg_type == MSG_LOGOUT:
            self.handle_disconnect(sock)
            return create_response(STATUS_OK, message="Logged out")
        
        # Check authentication for other messages
        if sock not in self.clients:
            return create_response(STATUS_ERROR, message="Not logged in")
        
        user_info = self.clients[sock]
        role = user_info["role"]

        # Route to appropriate service
        if role == ROLE_DEVELOPER:
            return self.dev_service.handle_message(sock, msg_type, data, user_info)
        elif role == ROLE_PLAYER:
            # Player can access both Lobby and Store services
            if msg_type in [MSG_LIST_GAMES, MSG_GAME_DETAILS, MSG_DOWNLOAD_GAME, MSG_SUBMIT_REVIEW, MSG_LIST_REVIEWS, MSG_LIST_PLUGINS, MSG_DOWNLOAD_PLUGIN]:
                return self.store_service.handle_message(sock, msg_type, data, user_info)
            elif msg_type in [MSG_CREATE_ROOM, MSG_JOIN_ROOM, MSG_LIST_ROOMS, MSG_START_GAME, MSG_PLUGIN_MESSAGE, MSG_LEAVE_ROOM, MSG_CHAT]:
                return self.lobby_service.handle_message(sock, msg_type, data, user_info)
            else:
                return create_response(STATUS_ERROR, message="Unknown message type for player")
        
        return create_response(STATUS_ERROR, message="Unknown role")

    def handle_login(self, sock, data):
        username = data.get("username")
        password = data.get("password")
        role = data.get("role")
        
        if self.db.login_user(username, password, role):
            # Check if already logged in with the SAME role
            # We allow the same user to be logged in as DEVELOPER and PLAYER simultaneously
            for client_info in self.clients.values():
                if client_info["username"] == username and client_info["role"] == role:
                    return create_response(STATUS_ERROR, message=f"User already logged in as {role}")

            self.clients[sock] = {"username": username, "role": role}
            return create_response(STATUS_OK, message="Login successful")
        else:
            return create_response(STATUS_ERROR, message="Invalid credentials")

    def handle_register(self, data):
        username = data.get("username")
        password = data.get("password")
        role = data.get("role")
        
        if self.db.register_user(username, password, role):
            return create_response(STATUS_OK, message="Registration successful")
        else:
            return create_response(STATUS_ERROR, message="Username already exists")

    def handle_disconnect(self, sock):
        if sock in self.clients:
            user_info = self.clients[sock]
            if user_info["role"] == ROLE_PLAYER:
                self.lobby_service.handle_player_disconnect(user_info["username"])
            del self.clients[sock]

    def broadcast(self, usernames, message):
        # Send message to specific users
        for sock, info in self.clients.items():
            if info["username"] in usernames:
                try:
                    send_json(sock, message)
                except:
                    pass

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Game Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
            python server/main.py                    # Run with defaults (0.0.0.0:8888)
            python server/main.py --port 9000        # Run on port 9000
            python server/main.py --host 127.0.0.1   # Run on localhost only
        """)
    
    parser.add_argument('--host', type=str, default=HOST, 
                        help=f'Host address to bind to (default: {HOST})')
    parser.add_argument('--port', type=int, default=PORT, 
                        help=f'Port number to bind to (default: {PORT})')
    
    args = parser.parse_args()
    
    server = GameServer(host=args.host, port=args.port)
    server.start()
