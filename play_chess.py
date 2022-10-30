#!chenv/bin/python3
from dotenv import load_dotenv
import os
from helpers import Game

load_dotenv()

token = os.environ.get('LICHESS_TOKEN')

game = Game(token=token,
            game_id='f4vD2sWC',
            random_only=True)

game.run()