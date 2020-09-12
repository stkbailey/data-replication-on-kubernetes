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

A quick summary on the Singer spec mentioned above:

- a `tap` connects to service, extracts data, then emits a standardized stream of schemas and records using JSON
- a `target` reads the record stream of a tap and load it into a warehouse

This separation of tap and target decouplesthe "extract" step and the "load" step. So an organization with 10 sources and 1 data warehouse has ten tap-to-target pipelines to manage. If they migrate this database, though, they only need to "swap out" the target; they won't make a single change to any taps.

One pecularity of this isolation is that a best practice for running taps and targets is to isolate them in their own Python virtual environments, since each tap and target may have different dependencies, be built on different Singer versions, etc. And when I first read that, I thought: containers! Yet, there is scarcely a mention of containers in the Singer community, at least as far as I could tell.

### Kubernetes and Argo Workflows

At Immuta, we have a small data team but a world-class engineering organization. As a rule, I like to defer to the engineering team, who have both knowledge and skill, since I, as a data scientist, have neither of these things. 

The rest of our internal infrastructure runs on Kubernetes; as the lone data scientist, I felt the peer pressure of learning k9s and managing kubeconfigs. And I’m here to say -- this is a great approach, if you’re willing to do some dirty work.

[Argo](https://argoproj.github.io/) is the "Kubernetes-Native Workflow Engine"

Argo Workflows is an open source container-native workflow engine for orchestrating parallel jobs on Kubernetes. It is an alternative to other orchestration tools, such as Airflow or Prefect, and the key differentiator is that it is container-based. This Data Council talk provides a nice comparison with Airflow specifically:  [Kubernetes-Native Workflow Orchestration with Argo](https://www.datacouncil.ai/talks/kubernetes-native-workflow-orchestration-with-argo)

Now that we have a motivation for using Singer and Argo together, let's get to work!

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
  -n argo                                   \
  --set service.type=LoadBalancer           \
  --set defaultBucket.enabled=true          \
  --set defaultBucket.name=my-bucket        \
  --set persistence.enabled=false           \
  --set fullnameOverride=argo-artifacts
```

You now have an artifacts server running, but it's empty! Let's create an artifacts bucket, along with a bucket for singer configuration and outputs. To use the commands below, you'll need the MinIO CLI tool: `brew install minio/stable/mc`.

`https://sourcegraph.com/github.com/argoproj/argo@095d67f8d0f1d309529c8a400cb16d0a0e2765b9/-/blob/demo.md#5-install-an-artifact-repository`

```
kubectl patch configmap workflow-controller-configmap -n argo --patch "$(cat kubernetes/argo-patch.yml)"
```

```{zsh}
# Add config host
mc config host add argo-artifacts-local http://localhost:9000 YOURACCESSKEY YOURSECRETKEY

# Create buckets in min.io
mc mb argo-artifacts-local/artifacts
mc mb argo-artifacts-local/singer
```

You can go and check these in your browser using `kubectl port-forward service/argo-artifacts 9000:9000`.

```
mc ls argo-artifacts-local
```

#### Map Argo and MinIO together

Finally, we need to tell Argo where the default artifact repository is, so that it knows which bucket to map artifacts to and has the appropriate secrets for authentication. To do this, I've created a `ConfigMap` and `Secret` Kubernetes resources. You can simply use `kubectl apply` to deploy them to your cluster.

```{zsh}
RESOURCE_BASE=https://raw.githubusercontent.com/stkbailey/data_replication_on_kubernetes/kubernetes/
kubectl apply -f ${RESOURCE_BASE}/kubernetes/default-argo-configmap.yml
kubectl apply -f ${RESOURCE_BASE}/kubernetes/default-minio-secrets.yml
```

To make sure you've got everything working in this first section, try running the "artifact-passing" example from the Argo examples repository.

```{zsh}
argo submit -n argo https://raw.githubusercontent.com/argoproj/argo/master/examples/artifact-passing.yaml --watch
```

You should see a two-step Workflow create and finish. Congratulations -- it's all downhill from here.

### 2. Test the tap and target containers

Let's put Kubernetes to the side for a moment and focus on a typical Singer pipeline. It's a linear process:

1. Tap inputs: configuration file, catalog file, state file.
2. Tap outputs: a stream of log data in Singer format.
3. Target inputs: configuration file, tap output stream.
4. Target outputs: loaded/exported data (e.g. to a database or CSV file), state file

We can treat the containers themselves as black boxes, so long as we know how to feed in the appropriate inputs and outputs. To keep things simple in this tutorial, I have pre-created `tap` and `target` containers for our use. To test it out, run this command:

```{zsh}
docker run -e START_DATE=2020-08-01 stkbailey/tap-exchange-rates
```

This should kick off the `tap-exchangeratesapi`, which doesn't require any special configuration to run.

```{zsh}
docker run -e DESTINATION_PATH=/tmp stkbailey/target-csv
```

This will kick off the `target-csv` script, which is also lightweight.

1. Create an Argo Workflow template that uses variables to select the tap and target container. This serves as the backbone of your process; everything else is parameterized.
2. Create a `target` container for your data warehouse. 
3. Save the `config.json` for your target to a secure location.

Once that's set up, for each new tap, you:

1. Create a new `tap` container. The tap runs a Python script on start that checks a few default locations for configs, catalogs, etc. Deploy the new container to ECR so that it is accessible by the Argo service user.
2. Save the `config.json`, `catalog.json`, and an initial `state.json` to a config folder on S3.
3. Create a new CronWorkflow (or Workflow Template) for your job, that references your

I have published a tap and target container publicly -- let's take a look at how they work.

```{zsh}
docker run                              \
    --env START_DATE=2020-09-01         \
    stkbailey/tap-exchange-rates:latest
```

You should see that the container emits a logging stream of updates -- but it does not emit the actual data itself. This is slightly different from how the tap would work if you were to run it locally. What we have done instead is written the tap output to a file inside the container.

This decision makes it less straightforward to simply "pipe" the output of one container to another, but it gives us greater control over where the logs (which are the data) are ultimately stored.

Now, let's try mapping a configuration file into the container, rather than providing a `START_DATE` configuration directly.

```
docker run    \
    --mount type=bind,source="$(pwd)"/singer-configs/tap-exchange-rates/config.json,target=/opt/code/config.json \
    stkbailey/tap-exchange-rates:latest
```

You should see a similar results to the first run.

Next, let's take a quick look at how the target works by running

```{zsh}
docker run                          \
    --env DESTINATION_PATH=/tmp     \
    stkbailey/target-csv:latest
```

Once again, we could map some additional files into the container -- and will need to do so to pass the tap output along.

We won't dig into the details, but each of these Docker containers is running a Python `entrypoint.py` script when they are initialized. The gist of these scripts is:

1. Identify the paths where `config`, `catalog`, `state` and `input` files exist.
2. Build the appropriate tap/target executable command, based on file availability.
3. Run the command and write output to a file.

It's a lot of overhead for a single command, but when you have multiple containers to run, the abstractions make life easier.

### 3. Creating the workflow

Now for the fun part -- our first Argo workflow! Let's run our simplest possible workflow, then break it down

#### The Preamble

We begin the Workflow by adding some metadata andd specifying that we want to create a "Workflow" resource. This is a single run of the workflow.

```

apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: singer-workflow
  namespace: argo
```

Next, we specify our DAG templates. We will be building three of these: a `tap-to-target` DAG, a `tap`, and a `target`. We _could_ do this all in a single step, but we'll talk about reusability in a moment.

Let's begin with the DAG template, which takes a couple input parameters -- names, images and the artifact bucket

```
spec:
  entrypoint: tap-to-target

  templates:
  - name: tap-to-target
    inputs:
      parameters:
      - name: tap_name
        value; tap-exchange-rates
      - name: target_name
        value: target-csv
      - name: tap_image
        value: stkbailey/tap-exchange-rates:latest
      - name: target_image
        value: stkbailey/target-csv:latest
    steps:
    - - name: tap
        template: singer-tap
        arguments:
          parameters:
          - name: tap_image
            value: "{{inputs.parameters.tap_image}}"
    - - name: target
        template: singer-target
        arguments:
          parameters:
          - name: target_image
            value: "{{inputs.parameters.target_image}}"
          artifacts:
          - name: tap-output
            from: "{{steps.tap.outputs.artifacts.tap-output}}"
```

The DAG Workflow references a couple other "templates" that also need to be defined. 
```
  - name: singer-tap
    container:
      image: "{{inputs.parameters.tap_image}}"
    inputs:
      parameters:
      - name: tap_image
      artifacts:
      - name: tap-config
        path: /tmp/config.json
        s3:
          bucket: singer
          key: "configs/{{inputs.parameters.tap_image}}/config.json"
          endpoint: my-minio-endpoint.default:9000
          accessKeySecret:
            name: artifact-credentials
            key: accessKey
          secretKeySecret:
            name: artifact-credentials
            key: secretKey
    outputs:
      artifacts:
      - name: tap-output
        path: /tmp/tap_output.txt
```

These can take a bit of effort to parse

```
  - name: singer-target
    container:
      image: "{{inputs.parameters.target_image}}"
    inputs:
      parameters:
        - name: target_image
      artifacts:
      - name: target-config
        path: /tmp/config.json
        s3:
          bucket: singer
          key: "configs/{{inputs.parameters.target_image}}/config.json"
          endpoint: my-minio-endpoint.default:9000
          accessKeySecret:
            name: s3-artifact-credentials
            key: accessKey
          secretKeySecret:
            name: s3-artifact-credentials
            key: secretKey
      - name: tap-output
        path: /tmp/tap_output.txt
    outputs:
      artifacts:
      - name: target-output
        path: /tmp/target_output.txt
      - name: csv-output
        path: /tmp/target_output.tar.gz
        s3:
          bucket: singer
          key: "output/{{inputs.parameters.target_image}}/output.tar.gz"
          endpoint: my-minio-endpoint.default:9000
          accessKeySecret:
            name: s3-artifact-credentials
            key: accessKey
          secretKeySecret:
            name: s3-artifact-credentials
            key: secretKey
```

Now that we've defined the workflow, tap and target templates, we are ready to go! If you've followed all the steps so far, you should be in good shape to run the following Argo command:

```
argo submit -n argo <filename> --watch
```

You should see the DAG materialize and then complete. The `target-csv` step will create a new output file in your MinIO bucket with the exchange rates for the past few days. If you explore the bucket, you'll find the tap-output, the state files, and the output file have all been generated and stored in your artifact repository.

```
mc ls argo-artifacts-local/singer/outputs/target-csv/
```

You can re-run the workflow, changing the configuration as desired. And that's the beauty of this workflow: once set up, it's simply a matter of changing some container locations and config files to add a new tap. 

## Discussion

It is hopefully not hard to see how, with a few additional tweaks and some well-protected S3 buckets, this couldl be turned into a fairly robust architecture. We can easily turn the workflow specified above into an Argo `TemplateWorkflows` and reference it in a `CronWorkflow` to have it run on an hourly or daily basis.

But, exciting as all this is, it has to be noted that this is not for the faint of heart.

### Kubernetes is COMPLICATED

As a data scientist, there are a lot of considerations.

- How are you building and updating the containers? Does your cluster have access to that container repository?
- How are you triggering new workflows?
- Networking can be a pain.

You may find that `pipelinewise` or `meltano` can do the same work for you, with less overhead. Alternatively, you may find that running them on Argo gives you a nice method for doing custom replications.

### You need to think about logging and observability

We use a Slack exit-handler to notify our team of successes and failures. 

### The Singer ecosystem is loosely regulated

What seems like a Nirvana at first -- an open source ecosystem of pre-built integrations -- can quickly become a bit of a nightmare. Our team has found fundamental deficiencies in a few taps -- such as not pulling all the relevant data.

But, teams at Pipelinewise and Meltano are doing soem great work building up the ecosystem and making them reliable.

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

Thanks for reading!
