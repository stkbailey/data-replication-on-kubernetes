# data-replication-on-kubernetes

ELT is the hot new data pipelining pattern, and thousands of data teams are using some combination of Stitch / FiveTran, dbt and a cloud data warehouse to manage their data warehouse. There are great SaaS offerings for these tools, but a lot of folks like pain or don't have budget. As a small data team at Immuta, we were both.

This article assumes some familiarity with [Docker](https://docker.com), [Kubernetes](https://kubernetes.io/) and the [Singer](https://singer.io) specification. Even if you're new to these technologies, though, I will try to point out helpful resources to get you pointed in the right direction.

First, we will discuss the problem we are trying to solve and why using containers can make a lot of sense. Then, I'll walk you through setting up some workflows at home (as long as your home is Mac OSX Catalina). And finally, we'll talk about considerations you want to make if you'd like to move into production.

## Motivation

Let's start the discussion with two assertions:

1. Data replication is a "solved" problem.
2. Kubernetes is a scalable data (process) management platform.

ETL is not the reason that anyone gets into data science or engineering. There is little creativity, lots of maintenance, and no recognition until something goes wrong. Fortunately, SaaS tools like [Stitch](www.stitchdata.com) and [FiveTran](www.fivetran.com) have pretty much turned data replication into a commodity that small teams can leverage. And where there are no existing supported connectors (for internal applications, say), a data scientist could write their own [Singer](https://singer.io) script and load data themselves.

Keep this last scenario I want to focus on here, because of course a "data pipeline" is hardly _just_ data replication.

The "solved" nature of data replication makes it easier for data scientists to own projects end-to-end, freeing data engineers to think about the "platform" rather than point solutions. ([StitchFix has a terrific post on this.](https://multithreaded.stitchfix.com/blog/2016/03/16/engineers-shouldnt-write-etl/)) In fact, the players in this market recognize that it's really the stuff "around" the integrations that are differentiators: the [Meltano](https://meltano.com) project out of GitLab, for example, found a niche in being [a "runner" for integration processes](https://www.dataengineeringpodcast.com/meltano-data-integration-episode-141/), rather than managing the end-to-end analytics pipeline.

### Singer taps and targets

A quick summary on the Singer spec mentioned above: there are `taps`, which connect to service, extract data, then emit a standardized stream of schemas and records using JSON, and thre are `targets`, which read the record stream of a tap and load it into a warehouse. The Singer specification facilitates a decoupling of the "extract" step and the "load" step. So an organization with 10 taps (extractors) and 1 target (database) has ten tap-to-target pipelines to manage. If they migrate this database, though, they only need to "swap out" the target; they won't make a single change to any taps.

One pecularity of this isolation is that a best practice for running taps and targets is to isolate them in their own Python virtual environments, since each tap and target may have different dependencies, be built on different Singer versions, etc. And when I first read that, I thought: containers! Yet, there is scarcely a mention of containers in the Singer community, at least as far as I could tell.

### Kubernetes and Argo Workflows

At Immuta, we have a small data team but a world-class engineering organization. As a rule, I like to defer to the engineering team, who have both knowledge and skill, since I, as a data scientist, have neither of these things. 

The rest of our internal infrastructure runs on Kubernetes; as the lone data scientist, I felt the peer pressure of learning k9s and managing kubeconfigs. And I’m here to say -- this is a great approach, if you’re willing to do some dirty work.

[Argo](https://argoproj.github.io/) is the "Kubernetes-Native Workflow Engine"

Argo Workflows is an open source container-native workflow engine for orchestrating parallel jobs on Kubernetes. Argo Workflows is implemented as a Kubernetes CRD

This tutorial talks specifically about Argo Workflows. A good example of this in action is Kai __ talk at Data Council 2019:  [Kubernetes-Native Workflow Orchestration with Argo](https://www.datacouncil.ai/talks/kubernetes-native-workflow-orchestration-with-argo)

## Tutorial

The tutorial has three steps.

1. Set up a local Kubernetes cluster with Argo and Minio storage for artifacts and config files.
2. Review containerized Singer taps and targets.
3. Create and deploy an Argo Workflow combining tap and target.

We could go deep on any one of these areas, but I'll try to keep it shallow and manageable for the tutorial, leaving further discussion for "production" considerations to the end. The tutorial has the following pre-requisites:

1. Docker Desktop. Installed locally, with your Kubernetes for Docker (Minikube / another cluster is fine as well)
2. Helm. We will install both Argo and Minio for running this tutorial.

To start, we are going to be using two of the simplest singer.io packages -- `tap-exchangeratesapi` and `target-csv` -- for demonstrating how this works.

### 1. Setting up Argo

In this first section, we need to set up a Kubernetes cluster, Argo Workflows, an artifact repository, and a couple of storage buckets. Let’s use the containers for Docker for Desktop, which has a kubernetes container in it.

#### Install Docker Desktop and enable Kubernetes

Coming out of this section, you need to have a Kubernetes cluster which you have admin access to and can deploy resources to using `kubectl`. If you already have that, then you can skip this section.

If you don't have that, you will need to set it up, and the easiest way to do it is using Docker for Desktop. You'll want to follow the documentation on Docker's website.

1. Install Docker for Desktop. [Mac](https://docs.docker.com/docker-for-mac/install/).
2. Enable Kubernetes. [Mac](https://docs.docker.com/docker-for-mac/kubernetes/)
3. Test out the `kubectl` command. [Mac](https://docs.docker.com/docker-for-mac/kubernetes/#use-the-kubectl-command)

Once you have that working, feel free to play around with your Kubernetes cluster.

#### Install Argo Workflows

Next, we need to install Argo. You can follow the [Quick Start Guide](https://argoproj.github.io/argo/quick-start/) to get some context, or simply use the commands below to create an `argo` namespace in your cluster and deploy the resources.

```{zsh}
# Create the argo namespace
kubectl create ns argo

# Create the "quick start" resources
kubectl apply -n argo -f https://raw.githubusercontent.com/argoproj/argo/stable/manifests/quick-start-postgres.yaml
```

You should now have an Argo server and a few new Kubernetes resource types used by Argo, including `Workflow` and `CronWorkflow`. To get a glimpse of the Argo Workflows UI, you can forward the Kubernetes port to your localhost.

```{zsh}
kubectl -n argo port-forward deployment/argo-server 2746:2746
```

#### Set up Minio Storage

Argo Workflows can pass files from into or out of a container through the use of "artifacts". For local deployments, an easy way to configure artifact passing is through a Kubernetes deployment of [MinIO](https://min.io/). Argo has [plenty of guidance](https://argoproj.github.io/argo/configure-artifact-repository/) on setting this up with other services, but you can follow along below for a quick MinIO deployment.

Note that you'll need to have `helm` installed (essentially, a Kubernetes package manager). On Mac, you can use Homebrew: `brew install helm`.

```{zsh}
# Add the MinIO helm chart
helm repo add minio https://helm.min.io/
helm repo update

# Deploy MinIO in the "argo" namespace
helm install argo-artifacts minio/minio     \
    -n argo                                 \
    --set service.type=LoadBalancer         \
    --set fullnameOverride=argo-artifacts   \
    --set persistence.size=20M
```

You now have an artifacts server running, but it's empty! Let's create an artifacts bucket, along with a bucket for singer configuration and outputs. To use the commands below, you'll need the MinIO CLI tool: `brew install minio/stable/mc`.

```{zsh}
# Add config host
mc config host add argo-artifacts-local http://localhost:9000 YOURACCESSKEY YOURSECRETKEY

# Create buckets in min.io
mc mb argo-artifacts-local/artifacts
mc mb argo-artifacts-local/singer-configs
mc mb argo-artifacts-local/target-csv-output
```

You can go and check these in your browser using `kubectl port-forward service/argo-artifacts 9000:9000`.

```
mc ls argo-artifacts-local
```

#### Map Argo and MinIO together

Finally, we need 
Let's create a couple secrets to make things easier:

```{zsh}
RESOURCE_BASE=https://raw.githubusercontent.com/stkbailey/data_replication_on_kubernetes/kubernetes/
kubectl apply -f ${RESOURCE_BASE}/asdfasdf
```

```
mc cp ./singer-configs/* argo-artifacts-local/singer-configs/ --recursive
```

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

Then, we’ll invoke the template for a specific tap and target.

### 3. Deploy the workflow

Now, we get to the fun part!

## Next steps and discussion

### Kubernetes is COMPLICATED!

As a data scientist, there are a lot of considerations.

- How are you building and updating the containers? Does your cluster have access to that container repository?
- How are you triggering new workflows?
- Networking can be a pain.

### You need to think about logging and observability

We use a Slack exit-handler to notify our team of successes and failures. 

### Schedules and templates

The "promised land" of Argo, though, is that once it is set up, you simply have to change the image location to add a new tap -- and this is true! The only thing that should change between runs is the container that's invoked and the configuration files passed in.

The questions you need to ask are:

- Do I have the budget to just pay for this (Stitch / Fivetran)?
- Does a simpler (single-node) architecture work, such as Meltano?
- Does a Kubernetes architecture fit with the rest of the company's infrastructure?
- Can I reuse the Argo architecture for other processes, such as transformation pipelines, data quality testing, etc?

At Immuta, we went with this architecture becuase:

1. We didn't have budget (yet) for an enterprise service but found ourselves needing to run custom taps.
2. We were already comfortable with containerized applications.
3. The rest of our company's infrastructure was run on Kubernetes and leveraged other Argo products.
4. We had other projects, such as data quality jobs, that we need a platform to run on, and we did not have previous expertise with Airflow or Prefect.

## Conclusions

Thanks for reading!
