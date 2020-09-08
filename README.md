# data-replication-on-kubernetes

ELT is the hot new data pipelining pattern, and thousands of data teams are using some combination of Stitch / FiveTran, dbt and a cloud data warehouse to manage their data warehouse. There are great SaaS offerings for these tools, but a lot of folks like pain or don't have budget. As a small data team at Immuta, we were both.

This article assumes familiarity with the Singer specification. In particular, the existence of `taps` and `targets`. In most environments, individuals will have many taps, some of which will be home-grown (or forks to fix a bug), and a single target: their data warehouse.

There are three areas of development:

1. a container with the tap/target and a custom entrypoint
2. a configs bucket in s3 that has the config.json, catalog.json and state.json
3. a workflow template parameterized with the tap/target container that maps the s3 config  artifacts to the file paths that the customer entrypoint.py file expects

In this blog post, I will walk you through the architecture, a brief tutorial, and a discussion on the design decisions and other ways you might want to do this.

## Discussion

The rest of our internal infrastructure runs on Kubernetes; as the lone data scientist, I felt the peer pressure of learning k9s and managing kubeconfigs. And I’m here to say -- this is a great approach, if you’re willing to do some dirty work.

[Argo](https://argoproj.github.io/) is the "Kubernetes-Native Workflow Engine"

- Argo Workflows is an open source container-native workflow engine for orchestrating parallel jobs on Kubernetes. Argo Workflows is implemented as a Kubernetes CRD
- ArgoCD is a declarative, GitOps continuous delivery tool
- Argo Rollouts is a Kubernetes controller and set of CRDs which provide advanced deployment capabilities such as blue-green, canary, canary analysis, experimentation, and progressive delivery features to Kubernetes.
- Argo Events is an event-based dependency manager for Kubernetes which helps you define multiple dependencies from a variety of event sources like webhook, s3, schedules, streams etc. and trigger Kubernetes objects after successful event dependencies resolution.

This tutorial talks specifically about Argo Workflows. A good example of this in action is Kai __ talk at Data Council 2019:  [Kubernetes-Native Workflow Orchestration with Argo](https://www.datacouncil.ai/talks/kubernetes-native-workflow-orchestration-with-argo)

I want to say a few things up front:

1. It's not for the faint of heart. You're working in Docker, Kubernetes and Python. That said, I was emotionally invested in learning more Kubernetes, but not in learning Airflow.
2. There are
3. It's a platform that can do more than Extract and Load. The advantage to this approach for us is that no engineers have to learn Airflow to support our team, and it's all container-based, which simplifies deployment.

## Tutorial

The tutorial has the following pre-requisites:

1. Docker Desktop. Installed locally, with your Kubernetes for Docker (Minikube / another cluster is fine as well)
2. Helm. We will install both Argo and Minio for running this tutorial.

We are going to be using two simple singer.io packages -- `tap-exchangeratesapi` and `target-csv` -- for demonstrating how this works.

### 1. Setting up Argo

In this first section, we need to set up a Kubernetes cluster, Argo Workflows, an artifact repository, and a couple of input / output buckes. This is on Mac OSX Catalina. Let’s use the containers for Docker for Desktop, which has a kubernetes container in it.

1. Install Docker Desktop.
2. Enable Kubernetes for Docker Desktop. (Preferences > Kubernetes).
3. Install Argo. [Quick Start](https://argoproj.github.io/argo/quick-start/)

1. An S3 bucket to store container artifacts and Singer configs

```{zsh}
# https://github.com/argoproj/argo/blob/master/docs/quick-start.md
kubectl create ns argo
kubectl apply -n argo -f https://raw.githubusercontent.com/argoproj/argo/stable/manifests/quick-start-postgres.yaml
```

```{zsh}
kubectl -n argo port-forward deployment/argo-server 2746:2746
```

Next we need to set up min.io . 
(https://argoproj.github.io/argo/configure-artifact-repository/)

```{zsh}
brew install helm
<!-- helm repo add stable https://kubernetes-charts.storage.googleapis.com/ -->
helm repo add minio https://helm.min.io/
helm repo update
helm install argo-artifacts minio/minio     \
    --set service.type=LoadBalancer         \
    --set fullnameOverride=argo-artifacts   \
    --set persistence.size=20M
```

You now have an artifacts server running. Let's create a couple secrets to make things easier;

```{zsh}
kubectl apply -f https://raw.githubusercontent.com/stkbailey/data_replicationi...kubernetes/default-minio-secrets.yaml
kubectl apply -f kubernetes/default-argo-configmap.yaml 
```

Let's create a few buckets.

```{zsh}
# install the minio client
brew install minio/stable/mc

# Add config host
mc config host add argo-artifacts-local http://localhost:9000 YOURACCESSKEY YOURSECRETKEY

# Create / Copy buckets into min.io
mc mb argo-artifacts-local/target-csv-output
mc mb argo-artifacts-local/artifacts
mc cp ./singer-configs argo-artifacts-local/

mc ls argo-artifacts-local
```

You can go and check these in your browser using `kubectl port-forward service/argo-artifacts 9000:9000`.

### 2. Test the tap and target containers

The general process once everything is set up is:

1. Create an Argo Workflow template that uses variables to select the tap and target container. This serves as the backbone of your process; everything else is parameterized.
2. Create a `target` container for your data warehouse. 
3. Save the `config.json` for your target to a secure location.

Once that's set up, for each new tap, you:

1. Create a new `tap` container. The tap runs a Python script on start that checks a few default locations for configs, catalogs, etc. Deploy the new container to ECR so that it is accessible by the Argo service user.
2. Save the `config.json`, `catalog.json`, and an initial `state.json` to a config folder on S3.
3. Create a new CronWorkflow (or Workflow Template) for your job, that references your

I have published a tap and target container publicly -- let's take a look at how they work.

```{zsh}
docker run \
    --mount type=bind,source="$(pwd)"/singer-configs/tap-exchange-rates/config.json,target=/opt/code/config.json \
    stkbailey/tap-exchange-rates:latest
```

```{zsh}
docker run \
    --mount type=bind,source="$(pwd)"/singer-configs/target-csv/config.json,target=/tmp/config.json \
    --mount type=bind,source="$(pwd)"/singer-configs/target-csv/input.txt,target=/tmp/tap_input.txt \
    --mount type=bind,source="$(pwd)"/singer-configs/target-csv/output.txt,target=/tmp/tap_output.txt \
    stkbailey/target-csv:latest
```

### Creating the workflow

First ,we’ll create a template that has both tap and target.

```{}

Then, we’ll invoke the template for a specific tap and target.

### 3. Deploy the workflow

Now, we get to the fun part!

## Next steps and discussion



2. You're managing multiple services.
3. Egress
3. We have not yet gotten ArgoCD  implemented, but there is the hope that all resources will be 

- You want to run these taps on a schedule, so you'll want to use a `cronworkflow`. 
- You may want an exit handler for sending to Slack.
- Network connectivity can be a pain :/



Should you just bake in both the tap and target into a single container? Couldn’t you use something like Meltano? 
