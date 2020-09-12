# Make sure the local MinIO service is mapped for the MinIO CLI
mc config host add argo-artifacts-local http://localhost:9000 YOURACCESSKEY YOURSECRETKEY

# If the `singer` bucket is not created, create it
mc mb argo-artifacts-local/singer

# Copy the whole "tap-exhange-rates" config directory to the bucket
mc cp --recursive                               \
    argo/input-files-example/tap-exchange-rates \
    argo-artifacts-local/singer/config/

mc cp --recursive                           \
    argo/input-files-example/target-csv     \
    argo-artifacts-local/singer/config/