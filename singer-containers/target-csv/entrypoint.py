#!/usr/bin/env python3

import logging
import json
import os
import pathlib
import subprocess
import sys

logging.basicConfig(level=logging.INFO)


class TargetRunner:
    """
    The TargetRunner is a configurable object for running singer.io taps. It is
    intended to facilitate the re-use of an entrypoint script across Argo
    workflows.
    """

    config = None

    def __init__(
        self,
        execute_command: str,
        required_config_keys: list = [],
        path_to_config: str = "/tmp/config.json",
        path_to_input: str = "/tmp/tap_input.txt",
        path_to_output: str = "/tmp/target_output.txt",
    ) -> None:

        self.execute_command = execute_command
        self.required_config_keys = required_config_keys
        self.config_file = pathlib.Path(path_to_config)
        self.input_file = pathlib.Path(path_to_input)
        self.output_file = pathlib.Path(path_to_output)

        self.write_config()

    def write_config(self, use_environment=True, validate_keys=True) -> None:

        config_from_file = {}
        if self.config_file.exists():
            config_from_file = json.loads(self.config_file.read_text())

        config_from_env = {}
        if use_environment:
            config_from_env = {
                v: os.environ.get(v.lower(), os.environ.get(v.upper()))
                for v in self.required_config_keys
                if os.environ.get(v.lower(), os.environ.get(v.upper()))
            }

        config = {**config_from_file, **config_from_env}

        if validate_keys:
            missing = [
                var for var in self.required_config_keys if var not in config.keys()
            ]
            if any(missing):
                raise KeyError(f"Missing required key(s): {missing}")

        self.config_file.write_text(json.dumps(config))

    def make_command(self):
        "Create the tap command using the available config files."
        command = [self.execute_command]

        if self.config_file.exists():
            command.extend(["--config", self.config_file.as_posix()])

        return command

    def run(self):
        cmd = self.make_command()

        logging.info("Beginning load into target database.")
        with open(self.input_file, "r") as f_inp, open(self.output_file, "w") as f_out:
            proc = subprocess.Popen(cmd, stdin=f_inp, stdout=subprocess.PIPE,)
            for line in proc.stdout:
                f_out.write(line.decode("utf-8"))
            proc.wait()

            if proc.returncode != 0:
                sys.exit(1)
        logging.info("Finished running target.")


if __name__ == "__main__":
    target = TargetRunner(
        execute_command="target-csv",
        required_config_keys=["destination_path"],
        path_to_output="/tmp/target_output.txt",
    )
    target.run()
