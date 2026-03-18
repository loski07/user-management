# User Management API

## Abstract

This service provides a RESTful API for user management. It exposes endpoints to create new users and retrieve a list of existing users. User metadata is stored in DynamoDB, and user avatars are stored in an S3 bucket.

## Requirements

- Python 3.13
- Docker Engine
- Docker Compose (for local development environment)
- AWS CLI and configured credentials (for deploying to AWS or local testing with Localstack)
- Environment Variables: The application requires specific environment variables (`S3_BUCKET_NAME`, `DYNAMODB_TABLE_NAME`, `AWS_REGION`) to be set for proper configuration. These can be provided directly in the environment or via a `.env` file.

## Design

The application is built using the FastAPI framework for Python. It is containerized using a multi-stage Dockerfile.

The first stage, the builder, installs dependencies into a separate directory. The second stage copies the application code and the installed dependencies into a minimal, non-root distroless image from Google Container Registry. This approach reduces the final image size and attack surface.

The application server is `uvicorn`, which listens on port 8000. It is configured to interact with AWS DynamoDB and S3 for data storage, with all configuration managed via `pydantic-settings` using environment variables.

## Test

The project uses the `pytest` framework for both unit and integration tests.

IDE Execution: The project is configured to run tests directly from an IDE (like PyCharm/IntelliJ). The IDE's test runner handles the Python path and environment variable injection automatically, allowing tests to run seamlessly.

Command-Line Execution: To run tests from the command line, you must be in the `app` directory. The `PYTHONPATH` must be set to the parent directory to allow Python to find the `app` module, and the required environment variables must be present for `pydantic-settings` to initialize the application configuration.

### Unit Tests

Unit tests are located in `test/unit_tests.py` and do not require any external services. They use FastAPI's `dependency_overrides` to inject mock settings, ensuring isolation.

To run the unit tests from the `app` directory:
```sh
PYTHONPATH=.. pytest test/unit_tests.py
```

### Integration Tests

Integration tests are located in `test/integration_tests.py` and require a running instance of the application and its dependent services (Localstack).

1.  Start the local environment:
    ```sh
    # Make sure you are in the 'app' directory
    docker-compose up -d
    ```

2.  Run the integration tests:
    ```sh
    # Make sure you are in the 'app' directory
    PYTHONPATH=.. pytest test/integration_tests.py
    ```

## Build

The application is packaged as a Docker image. To build the image locally, run the following command from the `app` directory:

```sh
docker build -t user-management:latest .
```

## API Reference

### GET /users

Retrieves a list of all users.

- Response (200 OK)
  - Content-Type: `application/json`
  - Body:
    ```json
    [
      {
        "name": "string",
        "email": "user@example.com",
        "avatar_url": "string"
      }
    ]
    ```

### POST /user

Creates a new user. The request should be a `multipart/form-data` request.

- Request Body:
  - `name` (string, required): The user's name.
  - `email` (string, required): The user's email address.
  - `avatar` (file, required): The user's avatar image file.

- Response (201 Created)
  - Content-Type: `application/json`
  - Body:
    ```json
    {
      "name": "string",
      "email": "user@example.com",
      "avatar_url": "string"
    }
    ```

## Continuous Integration/Continuous Deployment (CI/CD)

This project utilizes GitHub Actions to implement a CI/CD pipeline, ensuring code quality, automated testing, and streamlined deployment processes.

### Workflow Triggers

The CI/CD pipeline is configured to run on the following events:

- Pull Requests to `master` branch: Triggers the Continuous Integration (CI) job when changes are made to relevant application, Docker, or Helm files.
- Pushes to `master` branch: Triggers both the CI and Continuous Deployment (CD) jobs. The CD job only runs if the CI job passes successfully.

### Continuous Integration (CI)

The CI job focuses on validating code quality and functionality before merging changes into the `master` branch. It includes the following steps:

- Code Checkout: Retrieves the latest code from the repository.
- Environment Setup: Configures the Python environment and starts a Localstack service to emulate AWS services (S3, DynamoDB).
- Dependency Installation: Installs all project dependencies.
- Linting & Static Analysis:
    - Runs `Black` for code formatting checks.
    - Runs `isort` for import sorting checks.
    - Runs `Mypy` for static type checking.
- Docker Image Validation: Builds the Docker image to ensure the `Dockerfile` is valid and the application can be containerized.
- Helm Chart Linting: Lints the Helm chart to check for syntax errors and best practices.
- Unit Tests: Executes all unit tests to verify individual components.
- Integration Tests: Initializes Localstack resources and runs integration tests against the emulated AWS services to validate end-to-end functionality.

### Continuous Deployment (CD)

The CD job is responsible for building and releasing the application artifacts once changes are successfully merged into the `master` branch. It performs the following actions:

- Code Checkout: Retrieves the latest code.
- Docker Image Build & Push: Builds the Docker image and pushes it to GitHub Container Registry (GHCR) with `latest` and `SHA` tags.
- Helm Chart Package & Push: Packages the Helm chart and pushes it to GitHub Packages (configured as an OCI registry).

This automated pipeline ensures that every change to the `master` branch is thoroughly tested and that deployable artifacts are always up-to-date and ready for deployment.
