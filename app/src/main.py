import os
import uuid
from typing import Any, Dict, List

import aioboto3
import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr

from .config import AppSettings, get_settings

app: FastAPI = FastAPI(title="User Management Service")

session: aioboto3.Session = aioboto3.Session()


class UserResponse(BaseModel):
    name: str
    email: EmailStr
    avatar_url: str


async def _upload_avatar_to_s3(avatar: UploadFile, settings: AppSettings) -> str:
    """
    Uploads an avatar file to the configured S3 bucket.
    :param avatar: The avatar file to upload.
    :param settings: The application settings.
    :return: The public URL of the uploaded avatar.
    :raise HTTPException: If the S3 upload fails.
    """
    file_extension: str = os.path.splitext(avatar.filename)[1] if avatar.filename else ""
    file_key: str = f"avatars/{uuid.uuid4()}{file_extension}"

    try:
        async with session.client("s3", region_name=settings.aws_region) as s3_client:
            await s3_client.upload_fileobj(
                avatar.file, settings.s3_bucket_name, file_key, ExtraArgs={"ContentType": avatar.content_type}
            )
        return f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{file_key}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload failed: {str(e)}")


async def _save_user_to_dynamodb(name: str, email: EmailStr, avatar_url: str, settings: AppSettings) -> Dict[str, str]:
    """
    Saves user metadata to the configured DynamoDB table.
    :param name: The user's name.
    :param email: The user's email address.
    :param avatar_url: The URL of the user's avatar.
    :param settings: The application settings.
    :return: A dictionary containing the user's data.
    :raise HTTPException: If the database write operation fails.
    """
    user_data: Dict[str, str] = {"email": str(email), "name": name, "avatar_url": avatar_url}
    try:
        async with session.resource("dynamodb", region_name=settings.aws_region) as dynamo_resource:
            table = await dynamo_resource.Table(settings.dynamodb_table_name)
            await table.put_item(Item=user_data)
        return user_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database write failed: {str(e)}")


@app.get("/users", response_model=List[UserResponse])
async def get_users(settings: AppSettings = Depends(get_settings)) -> List[Dict[str, Any]]:
    """
    Retrieves all users from the DynamoDB database.
    :param settings: The application settings, injected as a dependency.
    :return: A list of user objects.
    :raise HTTPException: If the database scan fails.
    """
    try:
        async with session.resource("dynamodb", region_name=settings.aws_region) as rico:
            table = await rico.Table(settings.dynamodb_table_name)
            response: Dict[str, Any] = await table.scan()
            return response.get("Items", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database scan failed: {str(e)}")


@app.post("/user", response_model=UserResponse, status_code=201)
async def create_user(
    name: str = Form(...),
    email: EmailStr = Form(...),
    avatar: UploadFile = File(...),
    settings: AppSettings = Depends(get_settings),
) -> Dict[str, str]:
    """
    Creates a new user.
    :param name: The user's name.
    :param email: The user's email address.
    :param avatar: The user's avatar image file.
    :param settings: The application settings, injected as a dependency.
    :return: The created user's data.
    """
    avatar_url: str = await _upload_avatar_to_s3(avatar, settings)
    user_data: Dict[str, str] = await _save_user_to_dynamodb(name, email, avatar_url, settings)
    return user_data


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", log_level="info")
