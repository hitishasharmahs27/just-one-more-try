"""main.py — Entry point for "Just One More Try"."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from game import Game


def main():
    g = Game()
    g.run()


if __name__ == '__main__':
    main()
