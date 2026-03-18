import os
import threading
import time
from typing import Any, AsyncGenerator, Dict, List

import aioboto3
import httpx
import pytest
import pytest_asyncio
import uvicorn

from app.src.main import app as fastapi_app

BASE_URL: str = "http://localhost:8000"
AWS_ENDPOINT_URL: str | None = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION: str = "us-east-1"
S3_BUCKET: str = "user-avatars"
DYNAMO_TABLE: str = "users-table"
TEST_AVATAR_PATH: str = os.path.join(os.path.dirname(__file__), "resources", "tux-slash.png")


async def _create_s3_bucket(session: aioboto3.Session) -> None:
    """
    Creates the S3 bucket required for the tests.
    :param session: The aioboto3 session to use for creating the client.
    """
    async with session.client("s3", endpoint_url=AWS_ENDPOINT_URL, region_name=AWS_REGION) as s3:
        await s3.create_bucket(Bucket=S3_BUCKET)


async def _create_dynamodb_table(session: aioboto3.Session) -> None:
    """
    Creates the DynamoDB table required for the tests and waits for it to exist.
    :param session: The aioboto3 session to use for creating the resource.
    """
    async with session.resource("dynamodb", endpoint_url=AWS_ENDPOINT_URL, region_name=AWS_REGION) as dynamo:
        table = await dynamo.create_table(
            TableName=DYNAMO_TABLE,
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        await table.wait_until_exists()


async def _teardown_s3_bucket(session: aioboto3.Session) -> None:
    """
    Deletes all objects in the S3 bucket and then deletes the bucket itself.
    :param session: The aioboto3 session to use for creating the resource.
    """
    async with session.resource("s3", endpoint_url=AWS_ENDPOINT_URL, region_name=AWS_REGION) as s3_resource:
        bucket = await s3_resource.Bucket(S3_BUCKET)
        await bucket.objects.all().delete()
        await bucket.delete()


async def _teardown_dynamodb_table(session: aioboto3.Session) -> None:
    """
    Deletes the DynamoDB table used for the tests.
    :param session: The aioboto3 session to use for creating the client.
    """
    async with session.client("dynamodb", endpoint_url=AWS_ENDPOINT_URL, region_name=AWS_REGION) as dynamo_client:
        await dynamo_client.delete_table(TableName=DYNAMO_TABLE)


def _run_fastapi_app() -> None:
    """
    Runs the FastAPI application using uvicorn."""
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="info")


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_infrastructure() -> AsyncGenerator[None, None]:
    """
    Set up and tear down the required AWS infrastructure in LocalStack and start/stop the FastAPI app.
    """
    api_thread = threading.Thread(target=_run_fastapi_app)
    api_thread.daemon = True
    api_thread.start()
    time.sleep(5)

    session: aioboto3.Session = aioboto3.Session(
        aws_access_key_id="test", aws_secret_access_key="test", region_name=AWS_REGION
    )
    await _create_s3_bucket(session)
    await _create_dynamodb_table(session)
    yield
    await _teardown_s3_bucket(session)
    await _teardown_dynamodb_table(session)


async def _create_user(client: httpx.AsyncClient, name: str, email: str) -> None:
    """
    Sends a POST request to the /user endpoint to create a new user and asserts a successful creation.
    :param client: The httpx.AsyncClient to use for the request.
    :param name: The name of the user to create.
    :param email: The email of the user to create.
    """
    with open(TEST_AVATAR_PATH, "rb") as image_file:
        img_raw: bytes = image_file.read()

    payload: Dict[str, str] = {"name": name, "email": email}
    files: Dict[str, Any] = {"avatar": ("pixel.png", img_raw, "image/png")}

    post_res: httpx.Response = await client.post("/user", data=payload, files=files)

    assert post_res.status_code == 201, f"Failed to create user. Response: {post_res.json()}"
    created_user: Dict[str, Any] = post_res.json()
    assert S3_BUCKET in created_user["avatar_url"]


async def _verify_user_in_list(client: httpx.AsyncClient, email: str) -> None:
    """
    Sends a GET request to the /users endpoint and asserts that a user with the specified email exists.
    :param client: The httpx.AsyncClient to use for the request.
    :param email: The email of the user to verify.
    """
    get_res: httpx.Response = await client.get("/users")
    assert get_res.status_code == 200
    users: List[Dict[str, Any]] = get_res.json()
    user_emails: List[str] = [u["email"] for u in users]
    assert email in user_emails, f"User with email {email} not found in user list."


@pytest.mark.asyncio
async def test_full_user_flow_integration() -> None:
    """
    Test the full user creation and retrieval flow against a live LocalStack environment.
    """
    test_email: str = "integration.test@example.com"
    test_name: str = "Integration Tester"

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        await _create_user(client, name=test_name, email=test_email)
        await _verify_user_in_list(client, email=test_email)
