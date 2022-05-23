import time
from json import dump as dump_json
from json import load as load_json
from pathlib import Path

from ruamel.yaml import safe_dump as dump_yaml
from ruamel.yaml import safe_load as load_yaml


class TerminalAdopter(object):
    def __init__(self) -> None:
        """Base adopter for terminals."""
        super().__init__()
        self.CONFIG_FILE_LOC: str = ""

        self.config: dict
        self.backup_config: dict

    def load_config(self) -> dict | list:
        """Load config from `self.CONFIG_FILE_LOC` .

        Raises:
            ValueError: Config file invalid.

        Returns:
            dict | list: Loaded terminal config.
        """
        if not self.CONFIG_FILE_LOC:
            raise ValueError("Config file location not set")
        file_ext: str = self.CONFIG_FILE_LOC.split(".")[-1].strip().lower()
        if file_ext == "yaml":
            return load_yaml(open(self.CONFIG_FILE_LOC, "r"))
        if file_ext == "json":
            return load_json(open(self.CONFIG_FILE_LOC, "r"))
        with open(self.CONFIG_FILE_LOC, "r") as f:
            return f.read()

    def save_config(self, config: dict | list | str) -> None:
        """Save config to `self.CONFIG_FILE_LOC` .

        Args:
            config (dict | list | str): Config to save.

        Raises:
            ValueError: Config file invalid.
        """
        if self.CONFIG_FILE_LOC == "":
            raise ValueError("Config file location not set")
        file_ext: str = self.CONFIG_FILE_LOC.split(".")[-1].strip().lower()
        if file_ext == "json":
            dump_json(config, open(self.CONFIG_FILE_LOC, "w"))
        elif file_ext == "yaml":
            dump_yaml(config, open(self.CONFIG_FILE_LOC, "w"))
        else:
            with open(self.CONFIG_FILE_LOC, "w") as f:
                f.write(config)

    def adjust_terminal_font_size(self, font_size: int) -> None:
        """Adjust terminal font size.

        Args:
            font_size (int): Font size to set.
        """
        raise NotImplementedError(
            "Call to `adjust_terminal_font_size` are only effective in terminal-specific adopters.")

    def restore_terminal_font_size(self) -> None:
        """Restore terminal font size to the original size."""
        raise NotImplementedError(
            "Call to `restore_terminal_font_size` are only effective in terminal-specific adopters.")


class HyperAdopter(TerminalAdopter):
    def __init__(self) -> None:
        """Adopter for the web-based terminal Hyper."""
        super().__init__()
        self.CONFIG_FILE_LOC = f"{str(Path.home())}/.hyper.js"

        self.config: str = self.load_config()
        self.backup_config: str = self.load_config()

    def adjust_terminal_font_size(self, font_size: int) -> None:
        current_font_size: int = int(self.config[self.config.find(
            "fontSize"):].split(":", 1)[-1].split(",", 1)[0].strip())
        if current_font_size == font_size:
            return
        self.config = self.config.replace(
            f"fontSize: {current_font_size}", f"fontSize: {font_size}")
        self.save_config(self.config)

    def restore_terminal_font_size(self) -> None:
        self.config = self.backup_config
        self.save_config(self.backup_config)


if __name__ == "__main__":
    hyper = HyperAdopter()
    hyper.adjust_terminal_font_size(1)
    time.sleep(10)
    hyper.restore_terminal_font_size()
