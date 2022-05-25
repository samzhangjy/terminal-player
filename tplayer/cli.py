from player import Player
import click

@click.command()
@click.option("--source", default="./test.mp4", help="The video source file path.")
def play(source):
    tplayer = Player(source)
    tplayer.play()

if __name__ == "__main__":
    play()
