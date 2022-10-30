import subprocess
from munch import DefaultMunch
from threading import Thread
import berserk
import chess
import random
import webbrowser

munchify = DefaultMunch.fromDict


def output(string, text=True, speech=True, notify=True):
    if text: print(string)
    if speech:
        speech2dict = {
            'x': 'takes',
            '=': 'promotes to',
            '+': 'check',
            '#': 'checkmate',
            'O-O': 'castles kingside',
            'O-O-O': 'castles queenside',
            'K': 'king',
            'Q': 'queen',
            'R': 'rook',
            'B': 'bishop',
            'N': 'knight',
            'O': 'pawn'
        }
        for key, value in speech2dict.items():
            string = string.replace(key, f' {value} ')
        speak(string)
    if notify:
        subprocess.check_call(['notify-send -u normal -a Konsole %s' % string], shell=True)


class Game(Thread):
    
    config = {
        '\rOptions:': '',
        '?':  'Show this message',
        'l':  'Show legal moves',
        'h':  'Show history',
        'o':  'Open game in browser',
        'b':  'Show ASCII board',
        'r':  'Toggle random moves (y accept, n reroll, q back)',
        'R':  'Use a random legal move (use at your own risk)',
        'q':  'Quit/Resign',
        'd':  'Draw/Offer draw',
        'c':  'Clear screen',
    }
    
    def __init__(self, token, random_only=False, game_id=None, **kwargs):
        super().__init__(**kwargs)
        self.client = berserk.Client(berserk.TokenSession(token))
        if game_id is not None:
            self.game_id = game_id
        else:
            self.game_id = self.client.challenges.create_ai()['id']
        print(self.game_id)
        self.stream = self.client.board.stream_game_state(self.game_id)
        self.random_only = random_only
        self.user = munchify(self.client.account.get())
        self.board = chess.Board()

    def run(self):
        self.user.color = self.get_color()
        self.client.board.offer_draw(self.game_id)
        for event in self.stream:
            print('.', end='\r')
            event = munchify(event)
            if event.type == 'gameState':
                self.handle_state_change(event.moves)
            elif event.type == 'gameFull':
                self.handle_state_change(event.state.moves)
            elif event.type == 'chatLine':
                self.handle_chat_line(event)
            else:
                print(event.type, end='\r')

    def handle_state_change(self, moves):
        self.moves = moves.split(' ') if moves else []
        self.load_local_board(self.moves)
        if self.moves:
            uci_move = self.moves[-1]
            # Turn into <chess.Move>
            uci_move = chess.Move.from_uci(uci_move)
            try:
                san_move = self.board.san(uci_move)
                print(san_move)
                self.board.push(uci_move)
            except AssertionError:
                pass
        if self.can_play(len(self.moves)):
            while True:
                user_input = input('>>> ')
                user_output = self.input_handler(user_input)
                if isinstance(user_output, str):
                    print(user_output)
                    try:
                        self.push_san(user_output)
                        break
                    except ValueError:
                        print('Invalid move')
                        continue

    def input_handler(self, user_input):
        match user_input:
            case '?':
                for key, value in self.config.items():
                    print(f'  {key}  {value}')
                return
            case 'l':
                for i in self.board.legal_moves:
                    print(self.board.san(i), end=' ')
                return print()
            case 'o':
                return webbrowser.open(f'https://lichess.org/{self.game_id}')
            case 'b':
                return print(self.board)
            case 'r':
                while True:
                    move = self.generate_random_move()
                    print(self.board.san(move))
                    user_input = input('\rAccept? (y/n/q):')
                    match user_input:
                        case 'y':
                            return move
                        case 'n':
                            continue
                        case 'q':
                            self.input_handler('')
            case 'R':
                return self.generate_random_move()
            case 'q':
                return self.resign()
            case 'd':
                return self.offer_draw()
            case 'c':
                return os.system('clear')
            case other:
                return user_input

    def push_san(self, san):
        uci = self.board.push_san(san).uci()
        self.client.board.make_move(self.game_id, uci)
 
    def resign(self):
        self.board.reset()
        self.client.board.resign(self.game_id)
        
    def generate_random_move(self):
        return random.choice(list(self.board.legal_moves))

    def load_local_board(self, moves):
        self.board.reset()
        for move in moves:
            self.board.push_uci(move)

    def get_color(self, moves=None):
        data = self.client.games.export(self.game_id)
        if 'user' in data['players']['white'].keys():
            if self.user.id == data['players']['white']['user']['id']:
                print('You are white')
                return True
        print('You are black')
        return False

    def can_play(self, moves_len):
        if self.board.outcome() is not None:
            print(self.board.result())
            return False
        is_even = moves_len % 2 == 0
        return is_even == self.user.color