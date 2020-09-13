#!/usr/bin/env python3
from singer_container_utils import TapRunner

tap_configs = dict(
    execute_command="tap-covid-19",
    required_config_keys=["api_token", "start_date"],
    path_to_config="/tmp/config.json",
    path_to_catalog= "/tmp/catalog.json",
    path_to_state = "/tmp/state.json",
    path_to_output="/tmp/tap_output.txt",
    discover_catalog=True,
)

if __name__ == "__main__":
    tap = TapRunner(**tap_configs)
    tap.run()
