
# https://github.com/argoproj/argo/blob/master/docs/quick-start.md
kubectl create ns argo
kubectl apply -n argo -f https://raw.githubusercontent.com/argoproj/argo/stable/manifests/quick-start-postgres.yaml


# To forward the ports
kubectl -n argo port-forward deployment/argo-server 2746:2746

# Set up min.io
# https://argoproj.github.io/argo/configure-artifact-repository/

helm repo add stable https://kubernetes-charts.storage.googleapis.com/
helm repo update
helm install argo-artifacts stable/minio --set service.type=LoadBalancer --set fullnameOverride=argo-artifacts

kubectl port-forward service/argo-artifacts 9000:9000
# USER: AKIAIOSFODNN7EXAMPLE
# PASS: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Creaete "artifacts" bucket

kubectl apply -f kubernetes/default-minio-secrets.yaml 
kubectl apply -f kubernetes/default-argo-configmap.yaml 