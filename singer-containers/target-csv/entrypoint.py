#!/usr/bin/env python3

from singer_container_utils import TargetRunner


target_configs = dict(
    execute_command="target-csv",
    required_config_keys=["destination_path"],
    path_to_config = "/tmp/config.json",
    path_to_input = "/tmp/tap_input.txt",
    path_to_output = "/tmp/target_output.txt",
)

if __name__ == "__main__":
    target = TargetRunner(**target_configs)
    target.run()
