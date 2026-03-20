# user-management
Yet another REST api to deploy in k8s and show how to do CI/CD and IaC

## Implementation
### Python REST API
The repository, under the path [/app](./app), provides an application to be deployed in a K8s cluster.
It needs a DynamoDB database and a S3 bucket in order to work.

We include a GitHub Action Workflow that implement the continuous integration steps for the application.
([app-ci.yaml](.github/workflows/app-ci.yaml)) Lints and tests the application when we open a PR

We also include a helm chart [/helm](./helm) that would deploy the application in the K8s cluster.
It would create deployment, service, ingress and service account. It also has the option to implement a horizontal pod
autoscaler. The chart also includes a CI workflow [helm-ci.yaml](./.github/workflows/helm-ci.yaml) that checks the
chart on PR

### IaC
The path [/IaC](./IaC) contains a terraform project that creates the database and the bucket needed by the python
application. It also includes a workflow ([iac-ci.yaml](./.github/workflows/iac-ci.yaml)) for its CI that validates and
tests the project on PR

## Continuous delivery
The repository includes a CD workflow [cd.yaml](./.github/workflows/cd.yaml) that builds and pushes the docker image
and helm chart to the internal storage of GitHub
