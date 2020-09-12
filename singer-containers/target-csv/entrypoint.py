#!/usr/bin/env python3
import pathlib
import zipfile

from singer_container_utils import TargetRunner


# target-csv does not connect to a database, but rather outputs a set of files
# that need to be zipped up and mapped to an artifact
out = pathlib.Path("/tmp/data")
out.mkdir()

# Run the tap
if __name__ == "__main__":
    target = TargetRunner(
        execute_command="target-csv",
        required_config_keys=["destination_path"],
        path_to_config = "/tmp/config.json",
        path_to_input = "/tmp/tap_input.txt",
        path_to_output = "/tmp/target_output.txt",
    )
    target.run()


# Zip up the outputs and map to outfile
zf = zipfile.ZipFile(out / "data.zip", mode='w')
for f in out.glob("*.csv"):
    zf.write(f)
zf.close()
