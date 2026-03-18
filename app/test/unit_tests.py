import unittest
from typing import Any, Dict
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.src.config import AppSettings
from app.src.main import app, get_settings

# --- Test Setup ---
# Override the settings dependency for all tests
test_settings = AppSettings(s3_bucket_name='test-bucket', dynamodb_table_name='test-table')
app.dependency_overrides[get_settings] = lambda: test_settings

class TestUserEndpoints(unittest.TestCase):
    client: TestClient

    def setUp(self) -> None:
        """
        Set up the test client and common test data before each test.
        """
        self.client = TestClient(app)
        self.test_files: Dict[str, Any] = {"avatar": ("test.png", b"content", "image/png")}
        self.test_data: Dict[str, str] = {
            "name": "Test",
            "email": "test@test.com",
            "avatar_url": f"https://{test_settings.s3_bucket_name}.s3.{test_settings.aws_region}.amazonaws.com/test.png"
        }

    # --- Tests for GET /users ---

    @patch("app.src.main.session")
    def test_get_users_happy_path(self, mock_session: MagicMock) -> None:
        """
        Test GET /users for a successful response.
        :param mock_session: aioboto3 session mock.
        """
        mock_table: AsyncMock = AsyncMock()
        mock_table.scan.return_value = {"Items": [self.test_data]}
        mock_resource_context: AsyncMock = AsyncMock()
        mock_resource_context.__aenter__.return_value.Table.return_value = mock_table
        mock_session.resource.return_value = mock_resource_context

        response = self.client.get("/users")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["email"], self.test_data["email"])

    @patch("app.src.main.session")
    def test_get_users_db_failure(self, mock_session: MagicMock) -> None:
        """
        Test GET /users for a database failure.
        :param mock_session: aioboto3 session mock.
        """
        mock_session.resource.side_effect = Exception("Database connection error")

        response = self.client.get("/users")

        self.assertEqual(response.status_code, 500)
        self.assertIn("Database scan failed", response.json()["detail"])

    # --- Tests for POST /user ---

    @patch("app.src.main._save_user_to_dynamodb")
    @patch("app.src.main._upload_avatar_to_s3")
    def test_create_user_happy_path(self, mock_upload_s3: AsyncMock, mock_save_db: AsyncMock) -> None:
        """
        Test POST /user for a successful creation.
        :param mock_upload_s3: S3 upload helper function mock.
        :param mock_save_db: DynamoDB save helper function mock.
        """
        mock_upload_s3.return_value = self.test_data["avatar_url"]
        mock_save_db.return_value = self.test_data

        post_data = {"name": self.test_data["name"], "email": self.test_data["email"]}
        response = self.client.post("/user", data=post_data, files=self.test_files)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["email"], self.test_data["email"])
        mock_upload_s3.assert_awaited_once()
        mock_save_db.assert_awaited_once_with(
            self.test_data["name"], self.test_data["email"], self.test_data["avatar_url"], test_settings
        )

    @patch("app.src.main._upload_avatar_to_s3")
    def test_create_user_s3_failure(self, mock_upload_s3: AsyncMock) -> None:
        """
        Test POST /user for a failure during S3 upload.
        :param mock_upload_s3: S3 upload helper function mock.
        """
        mock_upload_s3.side_effect = HTTPException(status_code=500, detail="S3 Upload failed")
        post_data = {"name": self.test_data["name"], "email": self.test_data["email"]}
        response = self.client.post("/user", data=post_data, files=self.test_files)

        self.assertEqual(response.status_code, 500)
        self.assertIn("S3 Upload failed", response.json()["detail"])

    @patch("app.src.main._save_user_to_dynamodb")
    @patch("app.src.main._upload_avatar_to_s3")
    def test_create_user_db_failure(self, mock_upload_s3: AsyncMock, mock_save_db: AsyncMock) -> None:
        """
        Test POST /user for a failure during database write.
        :param mock_upload_s3: S3 upload helper function mock.
        :param mock_save_db: DynamoDB save helper function mock.
        """
        mock_upload_s3.return_value = self.test_data["avatar_url"]
        mock_save_db.side_effect = HTTPException(status_code=500, detail="Database write failed")
        post_data = {"name": self.test_data["name"], "email": self.test_data["email"]}
        response = self.client.post("/user", data=post_data, files=self.test_files)

        self.assertEqual(response.status_code, 500)
        self.assertIn("Database write failed", response.json()["detail"])
        mock_upload_s3.assert_awaited_once()
        mock_save_db.assert_awaited_once()

    def test_create_user_invalid_email(self) -> None:
        """
        Test POST /user with an invalid email address.
        """
        invalid_data = {**self.test_data, "email": "not-an-email"}
        response = self.client.post("/user", data=invalid_data, files=self.test_files)
        self.assertEqual(response.status_code, 422)
