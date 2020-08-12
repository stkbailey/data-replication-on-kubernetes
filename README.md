# data-replication-on-kubernetes
Tutorial on deploying Singer taps and targets on Kubernetes with Argo Workflows


Tap at https://github.com/singer-io/tap-covid-19

There are three areas of development:
1. a container with the tap/target and a custom entrypoint
2. a configs bucket in s3 that has the config.json, catalog.json and state.json
3. a workflow template parameterized with the tap/target container that maps the s3 config artifacts to the file paths that the customer entrypoint.py file expects
