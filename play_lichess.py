#!chenv/bin/python3
import berserk
from munch import DefaultMunch
from dotenv import load_dotenv
import chess
import os
import webbrowser
import random
import re
import click

load_dotenv()


@click.command()
@click.option('--type', default='AI',
              help='The type of game you would like to play.')
@click.option('--game_id', default=None,
              help='The game id of the ongoing game you would like to play.')
@click.option('--random_only/-r', default=False,
              help='If True random legal moves will be used on your turn.')
@click.option('--token', default=os.environ.get('LICHESS_TOKEN'),
              hide_input=True,
              help="""Your lichess token.
              If none provided the token will be read from the .env file.
              If .env file does not exist either the programm will exit.
              If you do not have a token, you can get one here: 
              https://lichess.org/account/oauth/token/create'.
              """)
def game_engine(type, game_id, random_only, token):
    os.system('clear')
    if not token:
        token = print('No Auth Token provided. Exiting.')
        quit()
    session = berserk.TokenSession(token)
    client = berserk.Client(session)
    board = chess.Board()
    user = DefaultMunch.fromDict(client.account.get())
    print('Welcome', user.username)
    board.reset()

    if game_id:
        data_stream = client.board.stream_game_state(game_id)
    else:
        game_id = client.challenges.create_ai()['id']
        data_stream = client.board.stream_game_state(game_id)


    for data in data_stream:
        data = DefaultMunch.fromDict(data)
        if data.state:
            data.moves = data.state.moves
            if data.white:
                if data.white.id == user.id:
                    print('You are white')
                else:
                    print('You are black')
                print('Press ? to show options')
        if data.moves:
            move = data.moves.split(' ')[-1]
            move = chess.Move.from_uci(move)
            try:
                if san_move := board.san(move):
                    print(san_move)
                    board.push(move)
            except AssertionError:
                continue
        while True:
            try:
                if random_only:
                    move = random.choice(list(board.legal_moves))
                    print(board.san(move))
                    board.push(move)
                    client.board.make_move(game_id, move.uci())
                    break
                move = input('>>> ')
                if move == '?': # Show options
                    print("""
                        Options:
                        ?: Show this message
                        l: Show legal moves
                        o: Open game in browser
                        r: Toggle random moves (y: accept, n: decline, q: quit-toggle)
                        R: Use a random legal move (use at your own risk)
                        q: Quit
                        d: Draw
                        q: Resign
                        c: Clear screen""".replace('                        ',''))
                    continue
                if move == 'l': # Show legal moves
                    print(board.legal_moves)
                    continue
                elif move == 'b': # Show ASCII board and san moves
                    print(board)
                elif move == 'o': # Open game in browser
                    webbrowser.open_new_tab(f'https://lichess.org/{game_id}')
                elif move == 'R': # Use random move
                    move = random.choice(list(board.legal_moves))
                    print(board.san(move))
                    board.push(move)
                    client.board.make_move(game_id, move.uci())
                    break
                elif move == 'r': # Toggle random moves
                    while True:
                        move = random.choice(list(board.legal_moves))
                        print(board.san(move))
                        i = input('(y/n/q)>>> ')
                        if i == 'y':
                            board.push(move)
                            client.board.make_move(game_id, move.uci())
                            break
                        elif i == 'n':
                            continue
                        elif i == 'q':
                            break
                    if i == 'y':
                        break
                    elif i == 'q':
                        continue
                elif move == 'q': # Resign
                    client.board.resign_game(game_id)
                    quit()
                elif move == 'd': # Draw
                    client.board.offer_draw(game_id)
                    break
                elif move == 'c': # Clear screen
                    os.system('clear')
                    continue
                elif move := board.push_san(move).uci():
                    client.board.make_move(game_id, move)
                    break
            except ValueError:
                print('Invalid move')
                continue

if __name__ == '__main__':
    game_engine()