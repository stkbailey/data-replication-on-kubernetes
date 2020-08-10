import json
import logging
import os
import pathlib
import subprocess
import sys


class TapRunner:
    """Container object for setting up and running taps in Immuta's Argo workflows."""

    exec_command = "tap-covid-19"
    config_keys = ["api_token", "start_date", "user_agent"]
    output_path = "/tmp/tap_output.txt"

    def __init__(self):
        self.setup_paths()
        self.write_config()
        self.write_catalog()

    def setup_paths(self, wd=pathlib.Path().cwd()):
        if not isinstance(wd, pathlib.Path):
            wd = pathlib.Path(wd)
        self.config_file = wd.joinpath("config.json")
        self.catalog_file = wd.joinpath("catalog.json")
        self.state_file = wd.joinpath("state.json")

    def write_config(self):
        """The tap has two methods for running:
        # First, if there is a "config.json" file mapped to the working directory, it will use that as a base
        # Second, if matching environment variables are present, it will override the config file
        # It will run a check of all required "config_keys" are present, it will generate the file."""
        config_from_file = {}
        if self.config_file.exists():
            config_from_file = json.loads(self.config_file.read_text())
            logging.info("Using configuration from file.")
        config_from_env = {
            v: os.environ.get(v.lower(), os.environ.get(v.upper()))
            for v in self.config_keys
            if os.environ.get(v.lower(), os.environ.get(v.upper()))
        }
        self.config = {**config_from_file, **config_from_env}

        # Check that all variables exist
        for var in self.config_keys:
            if not var in self.config.keys():
                msg = f"Missing required key: {var}"
                raise KeyError(msg)

        self.config_file.write_text(json.dumps(self.config))

    def write_catalog(self):
        # If the catalog file exists, do nothing.
        # Otherwise, run the tap in discovery mode and save to the catalog file
        if self.catalog_file.exists():
            logging.info("Using catalog from %s.", self.catalog_file.as_posix())
        else:
            logging.info("Generating catalog via discovery mode.")
            catalog_process = subprocess.run(
                [self.exec_command, "-c", self.config_file.as_posix(), "--discover"],
                capture_output=True,
            )
            self.catalog_file.write_text(catalog_process.stdout.decode("utf-8"))

    def make_tap_command(self):
        # Create the tap command, specifying the state information if available
        tap_command = [
            self.exec_command,
            "--config",
            self.config_file.as_posix(),
            "--catalog",
            self.catalog_file.as_posix(),
        ]
        if self.state_file.exists():
            tap_command += ["--state", self.state_file.as_posix()]
        return tap_command

    def run(self):
        # Run the tap and save output to file
        tap_command = self.make_tap_command()

        with open(self.output_path, "w") as f:
            logging.info("Running tap command: %s", " ".join(tap_command))
            tap_process = subprocess.Popen(tap_command, stdout=subprocess.PIPE)
            for line in tap_process.stdout:
                sys.stdout.write(line.decode("utf-8"))
                f.write(line.decode("utf-8"))
            tap_process.wait()
            if tap_process.returncode != 0:
                sys.exit(1)

        logging.info("Finished running tap.")


if __name__ == "__main__":
    tap = TapRunner()
    tap.run()
