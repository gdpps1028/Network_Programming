import socket
import sys
import json
import threading
import random
import time

HOST = '0.0.0.0'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9002

STRAIGHT_FLUSH  = 8
FOUR_OF_A_KIND  = 7
FULL_HOUSE      = 6
FLUSH           = 5
STRAIGHT        = 4
THREE_OF_A_KIND = 3
TWO_PAIR        = 2
ONE_PAIR        = 1
HIGH_CARD       = 0

HANDTEXT = ["High card", "One pair", "Two pair", "Three of a Kind", "Straight", 
            "Flush", "Full House", "Four of a Kind", "Straight Flush"]

class Deck:
    def __init__(self):
        self.cards = list(range(52))
        random.shuffle(self.cards)

    def draw(self, n=1):
        drawn = self.cards[:n]
        self.cards = self.cards[n:]
        return drawn

def evaluate_7_cards(cards):
    # 0-indexed 2-Ace order
    ranks_list = [(card // 4) + 2 for card in cards]
    suits_list = [card % 4 for card in cards]

    # Count ranks and suits
    rank_count = {}
    suit_count = {}
    for r in ranks_list:
        rank_count[r] = rank_count.get(r, 0) + 1
    for s in suits_list:
        suit_count[s] = suit_count.get(s, 0) + 1

    # Flush check
    is_flush = False
    flush_cards = []
    for s, count in suit_count.items():
        if count >= 5:
            is_flush = True
            flush_cards = sorted([r for r, suit in zip(ranks_list, suits_list) if suit == s], reverse=True)
            break

    # Straight check
    unique_ranks = sorted(set(ranks_list), reverse=True)
    straight_high = None
    ranks_for_straight = unique_ranks
    if 14 in unique_ranks:  # Ace-low straight
        ranks_for_straight.append(1)

    if len(ranks_for_straight) >= 5:
        for i in range(len(ranks_for_straight) - 4):
            window = ranks_for_straight[i:i + 5]
            if window[0] - window[4] == 4:
                straight_high = window[0]
                break

    # Quads, trips, pairs
    quads = sorted([r for r, count in rank_count.items() if count == 4], reverse=True)
    trips = sorted([r for r, count in rank_count.items() if count == 3], reverse=True)
    pairs = sorted([r for r, count in rank_count.items() if count == 2], reverse=True)
    
    if is_flush and straight_high is not None:
        return (STRAIGHT_FLUSH, [straight_high])
    if quads:
        kicker = max([r for r in ranks_list if r != quads[0]], default=quads[0])
        return (FOUR_OF_A_KIND, [quads[0], kicker])
    if trips and pairs:
        return (FULL_HOUSE, [trips[0], pairs[0]])
    if is_flush:
        return (FLUSH, flush_cards[:5])
    if straight_high is not None:
        return (STRAIGHT, [straight_high])
    if trips:
        kickers = sorted([r for r in ranks_list if r != trips[0]], reverse=True)[:2]
        return (THREE_OF_A_KIND, [trips[0]] + kickers)
    if len(pairs) >= 2:
        top_two = pairs[:2]
        kicker = max([r for r in ranks_list if r not in top_two], default=top_two[0])
        return (TWO_PAIR, top_two + [kicker])
    if len(pairs) == 1:
        kickers = sorted([r for r in ranks_list if r != pairs[0]], reverse=True)[:3]
        return (ONE_PAIR, [pairs[0]] + kickers)
    high_cards = sorted(ranks_list, reverse=True)[:5]
    return (HIGH_CARD, high_cards)

def compare_hands(h1, h2):
    if h1[0] > h2[0]: return 0
    if h2[0] > h1[0]: return 1
    for i in range(len(h1[1])):
        if h1[1][i] > h2[1][i]: return 0
        if h2[1][i] > h1[1][i]: return 1
    return 2

class Player:
    def __init__(self, conn, username):
        self.conn = conn
        self.username = username
        self.money = 1000
        self.cards = []
        self.hand_res = None
        self.current_bet = 0
        self.folded = False
        self.allin = False
    
    def send(self, data):
        try:
            self.conn.sendall(json.dumps(data).encode() + b"\n")
        except Exception:
            pass

class HoldemServer:
    def __init__(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.players = []
        self.lock = threading.Lock()
        self.running = True
        self.game_started = False
        
        # Game State
        self.pot = 0
        self.community_cards = []
        self.deck = None
        self.dealer_idx = 0
        
        # Phases
        self.PHASE_PREFLOP = 0
        self.PHASE_FLOP = 1
        self.PHASE_TURN = 2
        self.PHASE_RIVER = 3
        self.PHASE_SHOWDOWN = 4
        self.phase = self.PHASE_PREFLOP
        self.new_players = []

    def start(self):
        # Retry binding
        start_port = PORT
        max_retries = 5
        bound = False
        
        for i in range(max_retries):
            try:
                current_port = start_port + i
                self.server_sock.bind((HOST, current_port))
                bound = True
                print(f"Game Server started on {current_port}")
                sys.stdout.flush()
                break
            except OSError:
                continue
                
        if not bound:
            print(f"Error: Could not bind to any port in range {start_port}-{start_port+max_retries-1}")
            sys.exit(1)

        self.server_sock.listen(10)
        threading.Thread(target=self.accept_loop, daemon=True).start()
        self.game_loop()

    def accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_sock.accept()
                threading.Thread(target=self.handle_new_player, args=(conn,), daemon=True).start()
            except Exception:
                break

    def handle_new_player(self, conn):
        try:
            data = conn.recv(1024).decode().strip()
            msg = json.loads(data)
            username = msg.get("username", "Unknown")
            
            player = Player(conn, username)
            
            with self.lock:
                if self.game_started:
                    self.new_players.append(player)
                    spectator_list = []
                    for p in self.players:
                        spectator_list.append({
                            "username": p.username,
                            "money": p.money,
                            "bet": p.current_bet,
                            "folded": p.folded,
                            "allin": p.allin,
                            "is_turn": False
                        })
                    player.send({"type": "GAME_STATE", "pot": self.pot, "community_cards": self.community_cards, "players": spectator_list, "status_msg": "Game in progress. You will join next hand."})
                else:
                    self.players.append(player)
                
            self.broadcast_game_state(f"{username} joined.")
            
        except Exception:
            conn.close()

    def broadcast_game_state(self, status_msg=""):
        with self.lock:
            state = {
                "type": "GAME_STATE",
                "pot": self.pot,
                "community_cards": self.community_cards,
                "players": [],
                "status_msg": status_msg
            }
            
            for p in self.players:
                p_info = {
                    "username": p.username,
                    "money": p.money,
                    "bet": p.current_bet,
                    "folded": p.folded,
                    "allin": p.allin,
                    "is_turn": False
                }
                state["players"].append(p_info)
            
            for i, p in enumerate(self.players):
                my_state = state.copy()
                my_state["my_cards"] = p.cards
                p.send(my_state)

    def game_loop(self):
        while len(self.players) < 2:
            time.sleep(1)
            
        time.sleep(5)
        
        self.game_started = True
        
        while self.running:
            active_players = [p for p in self.players if p.money > 0]
            if len(active_players) < 2:
                self.broadcast_game_state("Waiting for more players/funds...")
                time.sleep(2)
                break
                
            self.play_hand()
            time.sleep(5)

    def play_hand(self):
        self.deck = Deck()
        self.pot = 0
        self.community_cards = []
        
        with self.lock:
            if self.new_players:
                self.players.extend(self.new_players)
                self.new_players = []

            for p in self.players:
                p.cards = []
                p.current_bet = 0
                p.folded = False
                p.allin = False
                p.hand_res = None
                
            # Blinds
            sb_idx = (self.dealer_idx + 1) % len(self.players)
            bb_idx = (self.dealer_idx + 2) % len(self.players)
            
            # Force bets
            p_sb = self.players[sb_idx]
            p_bb = self.players[bb_idx]
            
            sb_amt = min(5, p_sb.money)
            bb_amt = min(10, p_bb.money)
            
            p_sb.money -= sb_amt
            p_sb.current_bet = sb_amt
            
            p_bb.money -= bb_amt
            p_bb.current_bet = bb_amt
            
            self.pot = sb_amt + bb_amt
            
            # Deal Cards
            for p in self.players:
                if p.money > 0 or p.current_bet > 0:
                    p.cards = self.deck.draw(2)
        
        self.broadcast_game_state("Pre-Flop")
        
        # Betting Pre-Flop
        if not self.betting_round(start_idx=(bb_idx + 1) % len(self.players)): return

        # Flop
        self.community_cards = self.deck.draw(3)
        self.broadcast_game_state("Flop")
        if not self.betting_round(start_idx=(self.dealer_idx + 1) % len(self.players)): return

        # Turn
        self.community_cards += self.deck.draw(1)
        self.broadcast_game_state("Turn")
        if not self.betting_round(start_idx=(self.dealer_idx + 1) % len(self.players)): return

        # River
        self.community_cards += self.deck.draw(1)
        self.broadcast_game_state("River")
        if not self.betting_round(start_idx=(self.dealer_idx + 1) % len(self.players)): return
        
        # Showdown
        self.showdown()
        
        self.dealer_idx = (self.dealer_idx + 1) % len(self.players)

    def betting_round(self, start_idx):
        active_in_hand = [p for p in self.players if not p.folded]
        if len(active_in_hand) <= 1: return False
        
        current_bet_level = max(p.current_bet for p in self.players)
        idx = start_idx
        
        aggressor_idx = -1 
        if current_bet_level > 0:
            aggressor_idx = (start_idx - 1) % len(self.players)
            
        players_to_act = len(active_in_hand) 
        
        last_raiser = None
        current_bet_level = max(p.current_bet for p in self.players)
        
        acting_queue = []
        n = len(self.players)
        for i in range(n):
            p_idx = (start_idx + i) % n
            p = self.players[p_idx]
            if not p.folded and not p.allin:
                acting_queue.append(p_idx)
                
        if not acting_queue: return True

        last_aggressor = acting_queue[-1]
        if self.phase == self.PHASE_PREFLOP:
            pass
        else:
            last_aggressor = (start_idx - 1) % n
        
        current_idx = start_idx
        stop_idx = start_idx
        first_pass = True
        
        while True:
            active = [p for p in self.players if not p.folded]
            if len(active) == 1:
                self.winner_takes_pot([active[0]])
                return False

            p = self.players[current_idx]
            
            if p.folded or p.allin:
                current_idx = (current_idx + 1) % len(self.players)
                if current_idx == stop_idx and not first_pass:
                    break
                continue
            
            if current_idx == stop_idx and not first_pass:
                if p.current_bet == current_bet_level:
                    break

            to_call = current_bet_level - p.current_bet
            actions = ["FOLD", "ALLIN"]
            if to_call == 0:
                actions.append("CHECK")
                actions.append("RAISE")
            elif to_call < p.money:
                actions.append("CALL")
                actions.append("RAISE")
            else:
                pass
            
            self.broadcast_game_state(f"{p.username}'s Turn")
            p.send({"type": "REQUEST_ACTION", "actions": actions, "to_call": to_call})

            response = self.get_player_response(p)
            
            action = response.get("action")
            amount = response.get("amount", 0)
            
            if action == "FOLD":
                p.folded = True
            elif action == "CHECK":
                pass
            elif action == "CALL":
                p.money -= to_call
                p.current_bet += to_call
                self.pot += to_call
            elif action == "RAISE":
                
                total_bet = current_bet_level + amount
                additional = total_bet - p.current_bet
                
                if p.money >= additional:
                    p.money -= additional
                    p.current_bet += additional
                    self.pot += additional
                    current_bet_level = p.current_bet
                    stop_idx = current_idx
                else:
                    pass
            elif action == "ALLIN":
                self.pot += p.money
                p.current_bet += p.money
                p.money = 0
                p.allin = True
                if p.current_bet > current_bet_level:
                    current_bet_level = p.current_bet
                    stop_idx = current_idx
            
            first_pass = False
            current_idx = (current_idx + 1) % len(self.players)
            
        return True

    def get_player_response(self, player):
        try:
            data = player.conn.recv(1024).decode().strip()
            if not data:
                return {"action": "FOLD"}
            return json.loads(data)
        except:
            return {"action": "FOLD"}

    def showdown(self):
        active = [p for p in self.players if not p.folded]
        if len(active) <= 1:
            self.winner_takes_pot(active)
            return

        # Reveal cards
        for p in active:
            p.hand_res = evaluate_7_cards(p.cards + self.community_cards)

        final_state = {
            "type": "GAME_OVER",
            "community_cards": self.community_cards,
            "players": []
        }
        for p in self.players:
            p_data = {
                "username": p.username,
                "cards": p.cards if not p.folded else [],
                "hand_text": HANDTEXT[p.hand_res[0]] if p.hand_res else "Folded"
            }
            final_state["players"].append(p_data)
        
        # Determine winner
        winners = [active[0]]
        for p in active[1:]:
            res = compare_hands(p.hand_res, winners[0].hand_res)
            if res == 0: # p wins
                winners = [p]
            elif res == 2: # Tie
                winners.append(p)
                
        # Split pot
        share = self.pot // len(winners)
        win_msg = "Winner: "
        for w in winners:
            w.money += share
            win_msg += w.username + " "
            
        final_state["message"] = win_msg
        
        for p in self.players:
            p.send(final_state)
            
    def winner_takes_pot(self, winners):
        share = self.pot // len(winners)
        for w in winners:
            w.money += share
        msg = {"type": "GAME_OVER", "message": f"Winner: {[w.username for w in winners]}", "players": []}
        for p in self.players:
            p.send(msg)


if __name__ == "__main__":
    server = HoldemServer()
    server.start()
