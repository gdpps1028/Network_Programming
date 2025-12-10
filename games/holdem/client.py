import socket
import sys
import json
import os
import time

if len(sys.argv) < 5:
    print("Usage: client.py <username> <room_id> <host> <port>")
    sys.exit(1)

USERNAME = sys.argv[1]
ROOM_ID = sys.argv[2]
HOST = sys.argv[3]
PORT = int(sys.argv[4])


COLORS = [  "\033[1;107;38;5;21m",          # CLUB
            "\033[1;107;38;2;255;140;25m",  # DIAMOND
            "\033[1;107;38;5;160m",         # HEART
            "\033[1;107;38;5;232m",         # SPADE
            "\033[1;40;38;2;255;255;255m",  # BACK
            "\033[1;38;2;250;50;145m",      # PLR
            "\033[1;38;2;19;156;6m",        # OPP
            "\033[1;38;5;226m",             # MONEY
            "\033[0m"   ]                   # RESET

BACK  = 4
PLR   = 5
OPP   = 6
MONEY = 7
RESET = 8

def print_cards(cards, label="Cards"):
    SUITS = ['♣', '♦', '♥', '♠']
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    
    if label:
        print(f"{label}:")

    # Top line
    for card in cards:
        if card == -1:
            print(f"{COLORS[BACK]}╱╳╳╳╲{COLORS[RESET]}", end=" ")
        else:
            suit = card % 4
            rank = card // 4
            if (rank + 2) == 10:
                print(f"{COLORS[suit]}{RANKS[rank]} ─┐{COLORS[RESET]}", end=" ")
            else:
                print(f"{COLORS[suit]}{RANKS[rank]} ──┐{COLORS[RESET]}", end=" ")
    print()

    # Middle line
    for card in cards:
        if card == -1:
            print(f"{COLORS[BACK]}╳╳╳╳╳{COLORS[RESET]}", end=" ")
        else:
            suit = card % 4
            print(f"{COLORS[suit]}│ {SUITS[suit]} │{COLORS[RESET]}", end=" ")
    print()

    # Bottom line
    for card in cards:
        if card == -1:
            print(f"{COLORS[BACK]}╲╳╳╳╱{COLORS[RESET]}", end=" ")
        else:
            suit = card % 4
            rank = card // 4
            if (rank + 2) == 10:
                print(f"{COLORS[suit]}└─ {RANKS[rank]}{COLORS[RESET]}", end=" ")
            else:
                print(f"{COLORS[suit]}└── {RANKS[rank]}{COLORS[RESET]}", end=" ")
    print()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Handshake
    sock.sendall(json.dumps({"username": USERNAME}).encode() + b"\n")

    while True:
        try:
            data = sock.recv(4096).decode()
            if not data:
                break
            
            for line in data.strip().split('\n'):
                if not line: continue
                msg = json.loads(line)
                handle_message(sock, msg)
                
        except Exception as e:
            print(f"Error: {e}")
            break

def handle_message(sock, msg):
    m_type = msg.get("type")
    
    if m_type == "GAME_STATE":
        clear_screen()
        print(f"--- Texas Hold'em (Room: {ROOM_ID if 'ROOM_ID' in globals() else 'LOC'}) ---")
        print(f"Pot: ${msg['pot']}")
        print(f"Status: {msg.get('status_msg', '')}")
        print("-" * 20)
        
        community = msg.get("community_cards", [])
        if community:
            print_cards(community, "Community")
        else:
            print("Community: [Waiting]")
            
        print("-" * 20)
        print("Players:")
        for p in msg["players"]:
            me_ind = " (YOU)" if p['username'] == USERNAME else ""
            status = "FOLDED" if p['folded'] else ("ALL-IN" if p['allin'] else f"Bet: {p['bet']}")
            print(f"{p['username']}{me_ind}: ${p['money']} | {status}")
            
        print("-" * 20)
        my_cards = msg.get("my_cards", [])
        if my_cards:
            print_cards(my_cards, "Your Hand")
            
    elif m_type == "REQUEST_ACTION":
        print("\nYOUR TURN!")
        print(f"To Call: ${msg['to_call']}")
        print("Options:")
        actions = msg['actions']
        for i, act in enumerate(actions):
            print(f"{i+1}. {act}")
        
        while True:
            choice = input(f"Choose option (1-{len(actions)}): ").strip()
            
            # Check for direct number or number + amount
            parts = choice.split()
            if not parts or not parts[0].isdigit():
                print("Invalid input. Please enter a number.")
                continue
            
            idx = int(parts[0]) - 1
            if not (0 <= idx < len(actions)):
                print("Invalid option.")
                continue
                
            act = actions[idx]
            amt = 0
            
            if act == "RAISE":
                # Check if amount was provided in same line: "2 100"
                if len(parts) > 1 and parts[1].isdigit():
                    amt = int(parts[1])
                else:
                    # Ask for amount
                    while True:
                        val = input("Enter raise amount (additional): ")
                        if val.isdigit():
                            amt = int(val)
                            break
                        print("Invalid amount.")

            resp = {"action": act, "amount": amt}
            sock.sendall(json.dumps(resp).encode() + b"\n")
            break

    elif m_type == "GAME_OVER":
        print("\n=== HAND OVER ===")
        print(msg.get("message"))
        print("Hands:")
        for p in msg.get("players", []):
            print(f"{p['username']}: {p.get('hand_text', '')}")
            if 'cards' in p and p['cards']:
                print_cards(p['cards'], "")

        print("\nWaiting for next hand...")
        time.sleep(5)

    elif m_type == "ERROR":
        print(f"Error: {msg['message']}")

if __name__ == "__main__":
    main()
