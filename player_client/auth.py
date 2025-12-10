import sys
import os

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocol import *
from shared.utils import send_json, recv_json
from shared.gui_auth import AuthDialog

class Auth:
    def __init__(self, sock):
        self.sock = sock
        self.username = None

    def login(self):
        print("\n=== Player Login ===")
        print("Opening Login Dialog...")
        
        dialog = AuthDialog("Player Login")
        creds = dialog.show()
        
        if not creds:
            print("Login cancelled.")
            return False
            
        username, password = creds
        
        msg = create_message(MSG_LOGIN, {
            "username": username,
            "password": password,
            "role": ROLE_PLAYER
        })
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            print("Login successful!")
            self.username = username
            return True
        else:
            print(f"Login failed: {response.get('message', 'Unknown error')}")
            return False

    def register(self):
        print("\n=== Player Registration ===")
        print("Opening Registration Dialog...")
        
        dialog = AuthDialog("Player Registration")
        creds = dialog.show()
        
        if not creds:
            print("Registration cancelled.")
            return False
            
        username, password = creds
        
        msg = create_message(MSG_REGISTER, {
            "username": username,
            "password": password,
            "role": ROLE_PLAYER
        })
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            print("Registration successful! Please login.")
            return True
        else:
            print(f"Registration failed: {response.get('message', 'Unknown error')}")
            return False
