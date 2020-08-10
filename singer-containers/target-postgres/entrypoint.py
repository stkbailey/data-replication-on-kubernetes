#!/usr/bin/env python3

import logging
import json
import os
import pathlib
import subprocess
import sys

logging.basicConfig(level=logging.INFO)

class TargetRunner:

    exec_command = "target-redshift"
    config_keys = ["host", "port", "dbname", "user", "password", "aws_access_key_id", "aws_secret_access_key", "s3_bucket", "default_target_schema"]
    _tap_input_path = "/tmp/tap_output.txt"
    _target_output_path = "/tmp/target_output.txt"
    _target_state_path = "/tmp/target_state.txt"

    def __init__(self):
        self.setup_paths()
        self.write_config_file()

    def setup_paths(self, wd=pathlib.Path().cwd()):
        if not isinstance(wd, pathlib.Path):
            wd = pathlib.Path(wd)
        self.config_file = wd.joinpath("config.json")
        self.tap_input_file = pathlib.Path(self._tap_input_path)
        self.target_output_file = pathlib.Path(self._target_output_path)
        self.target_state_file = pathlib.Path(self._target_state_path)

    def write_config_file(self):
        config_from_file = {}
        if self.config_file.exists():
            config_from_file = json.loads(self.config_file.read_text())
            logging.info("Loaded configuration from file.")
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

    def run(self):
        with open(self.tap_input_file, "r") as f1, open(self.target_output_file, "w") as f2:
            target_process = subprocess.Popen(
                [self.exec_command, "-c", self.config_file],
                stdin=f1,
                stdout=subprocess.PIPE
            )
            for line in target_process.stdout:
                sys.stdout.write(line.decode("utf-8"))
                f2.write(line.decode("utf-8"))
            target_process.wait()
        return target_process.returncode


if __name__ == "__main__":
    logging.info("Writing configuration file.")
    target = TargetRunner()

    logging.info("Beginning load into target database.")
    return_code = target.run()
    if return_code != 0:
        logging.error("An error occurred.")
        sys.exit(1)
