import json
import os
import pickle
from hashlib import md5
from os import get_terminal_size
from time import sleep, time
from uuid import uuid4

import cv2
import moviepy.editor as mp
from climage import convert as convert_image
from playsound import playsound
from rich.console import Console
from rich.progress import Progress
from rich.text import Text

from adopters import HyperAdopter, TerminalAdopter


class Player(object):
    def __init__(self, video_path: str) -> None:
        """Video player for the terminal.

        Args:
            video_path (str): The video path.
        """
        super().__init__()
        self.adopter: TerminalAdopter = None
        self.video = cv2.VideoCapture(video_path)
        self.video_path = video_path
        self.video_name = video_path.split("/")[-1].split(".", 1)[0]
        self.console = Console()
        self.cache_dir = "./cache"
        self.cache_config = os.path.join(self.cache_dir, "cache.json")
        self.adopter = HyperAdopter()

        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)

    def image_to_ansi(self, image: str) -> str:
        """Convert an image (frame) to ANSI strings

        Args:
            image (str): image path.

        Returns:
            str: ANSI string of the original image given.
        """
        return convert_image(image, width=self.terminal_columns, is_unicode=True)

    def extract_audio(self, output_path: str = "audio.mp3"):
        """Extract audio from given video.

        Args:
            output_path (str, optional): Audio output filepath. Defaults to "audio.mp3".
        """
        clip = mp.VideoFileClip(self.video_path)
        clip.audio.write_audiofile(output_path)

    def load_cache(self, md5: str) -> tuple[dict, str] | None:
        """Load local cache.

        Try to load the stored local cache from `self.cache_config` file.

        Args:
            md5 (str): The target video's md5.

        Returns:
            tuple[dict, str] | None: A tuple containing the video data and audio path if md5 matches or else will return None.
        """
        print(f"Trying to load cache from {self.cache_config} ...")
        if not os.path.exists(self.cache_config):
            print("No cache found.")
            return None
        with open(self.cache_config, "r") as f:
            caches = json.loads(f.read())
        for cache in caches:
            if cache.get("md5", None) == md5:
                print(f"Cache {cache.get('md5')} found.")
                return (pickle.load(open(cache["video"], "rb")), cache["audio_path"])
        print("No cache found.")
        return None

    def save_cache(self, name: str, vid_path: str, data: dict, audio_path: str):
        """Save processed video and audio to cache.

        Args:
            name (str): Video name
            vid_path (str): Original video path
            data (dict): Converted ANSI video data
            audio_path (str): Extracted audio path
        """
        if os.path.exists(self.cache_config):
            with open(self.cache_config, "r") as f:
                caches = json.loads(f.read())
        else:
            caches = []
        uuid = uuid4()
        pickle.dump(data, open(f"./cache/{uuid}.pickle", "wb"))
        caches.append({
            "name": name,
            "video": f"./cache/{uuid}.pickle",
            "audio_path": audio_path,
            "md5": self.get_md5(vid_path)
        })
        with open(self.cache_config, "w") as f:
            f.write(json.dumps(caches, indent=2, ensure_ascii=False))

    def convert_to_ansi(self, fps: int = 2) -> list[str]:
        """Convert given video to ANSI characters.

        Args:
            fps (int, optional): Frames per second of the output video. Defaults to 2.

        Returns:
            list[str]: Converted ANSI characters where each frame is a string stored in the list.
        """
        fps_in = self.video.get(cv2.CAP_PROP_FPS)
        fps_out = fps
        index_in = -1
        index_out = -1
        result = []
        frame_loc = os.path.join(self.cache_dir, ".cur-frame.jpg")
        with Progress() as progress:
            task = progress.add_task(
                "Converting to ANSI", total=self.video.get(cv2.CAP_PROP_FRAME_COUNT))
            while True:
                success = self.video.grab()
                if not success:
                    break
                index_in += 1

                out_due = int(index_in / fps_in * fps_out)
                if out_due > index_out:
                    success, frame = self.video.retrieve()
                    if not success:
                        break
                    index_out += 1
                    cv2.imwrite(frame_loc, frame)
                    f = self.image_to_ansi(frame_loc)
                    result.append(f)
                progress.update(task, advance=1)
        return result

    def get_md5(self, vid_path: str) -> str:
        """Get the md5 value of the given video.

        Args:
            vid_path (str): Video path.

        Returns:
            str: The md5 value.
        """
        with open(vid_path, "rb") as f:
            vid_content = f.read()
        return md5(vid_content).hexdigest()

    def _play(self, fps: int = 5, font_size: int = 13):
        """Plays the video in the terminal.

        NOTE: this method will **not** restore the terminal font size after the video is played
        or the user terminates the process. Use `Player.play()` instead.

        Args:
            fps (int, optional): FPS of the video. Defaults to 5.
            font_size (int, optional): The font size to set for the terminal when playing the video. Defaults to 13.
        """
        # Try to load video data from cache first
        # Because converting video to ANSI takes a quite a long time
        try:
            (video, audio_path) = self.load_cache(
                self.get_md5(self.video_path))
        except TypeError:
            self.adopter.adjust_terminal_font_size(font_size)
            sleep(1)
            self.terminal_columns = get_terminal_size().columns
            self.adopter.restore_terminal_font_size()
            video = self.convert_to_ansi(fps)
            audio_path = f"./cache/{uuid4()}.mp3"
            self.extract_audio(audio_path)
            print("Converted. Saving cache...")
            self.save_cache(self.video_name, self.video_path,
                            video, audio_path)
            print("Cache saved.")

        self.adopter.adjust_terminal_font_size(font_size)

        SLEEP_PER_FRAME = 1 / fps

        with self.console.screen() as screen:
            start_time = time()
            delta = 0
            playsound(audio_path, block=False)
            for frame in video:
                # if the current frame is delayed one frame time or more, skip it
                if delta >= SLEEP_PER_FRAME:
                    delta -= SLEEP_PER_FRAME
                    start_time = time()
                    continue
                screen.update(Text.from_ansi(frame))
                end_time = time()
                est = SLEEP_PER_FRAME - (end_time - start_time)
                if est < 0:
                    delta += abs(est)  # adds up the total delayed time
                sleep(max(est, 0))
                start_time = time()

    def play(self, fps: int = 5, font_size: int = 13):
        """Plays the video in the terminal.

        Unlike `Player._play()`, this method adds an error boundary to handle the `ctrl+c` event.

        Args:
            fps (int, optional): FPS of the output video. Defaults to 5.
            font_size (int, optional): The font size to set for the terminal when playing the video. Defaults to 13.
        """
        try:
            self._play(fps, font_size)
        except KeyboardInterrupt:
            self.shutdown()
        else:
            self.shutdown()

    def shutdown(self):
        """Run tasks before the player exits."""
        self.adopter.restore_terminal_font_size()
        print("Exiting...")


if __name__ == "__main__":
    player = Player("./test.mp4")
    player.play()
