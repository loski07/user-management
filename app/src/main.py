import os
import uuid
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, EmailStr
import aioboto3
import uvicorn

# --- FastAPI App Initialization ---
app: FastAPI = FastAPI(title="User Management Service")

# --- Configuration ---
S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "")
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

if not S3_BUCKET_NAME or not DYNAMODB_TABLE_NAME:
    raise ValueError("S3_BUCKET_NAME and DYNAMODB_TABLE_NAME must be set as environment variables.")

session: aioboto3.Session = aioboto3.Session()

# --- Pydantic Models ---
class UserResponse(BaseModel):
    name: str
    email: EmailStr
    avatar_url: str

# --- Helper Functions ---

async def _upload_avatar_to_s3(avatar: UploadFile) -> str:
    """
    Uploads an avatar file to the configured S3 bucket.
    :param avatar: The avatar file to upload.
    :return: The public URL of the uploaded avatar.
    :raise HTTPException: If the S3 upload fails.
    """
    file_extension: str = os.path.splitext(avatar.filename)[1] if avatar.filename else ""
    file_key: str = f"avatars/{uuid.uuid4()}{file_extension}"

    try:
        async with session.client("s3", region_name=AWS_REGION) as s3_client:
            await s3_client.upload_fileobj(
                avatar.file,
                S3_BUCKET_NAME,
                file_key,
                ExtraArgs={"ContentType": avatar.content_type}
            )
        return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload failed: {str(e)}")

async def _save_user_to_dynamodb(name: str, email: EmailStr, avatar_url: str) -> Dict[str, str]:
    """
    Saves user metadata to the configured DynamoDB table.
    :param name: The user's name.
    :param email: The user's email address.
    :param avatar_url: The URL of the user's avatar.
    :return: A dictionary containing the user's data.
    :raise HTTPException: If the database write operation fails.
    """
    user_data: Dict[str, str] = {
        "email": str(email),
        "name": name,
        "avatar_url": avatar_url
    }
    try:
        async with session.resource("dynamodb", region_name=AWS_REGION) as dynamo_resource:
            table = await dynamo_resource.Table(DYNAMODB_TABLE_NAME)
            await table.put_item(Item=user_data)
        return user_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database write failed: {str(e)}")

# --- API Endpoints ---

@app.get("/users", response_model=List[UserResponse])
async def get_users() -> List[Dict[str, Any]]:
    """
    Retrieves all users from the DynamoDB database.
    :return: A list of user objects.
    :raise HTTPException: If the database scan fails.
    """
    try:
        async with session.resource("dynamodb", region_name=AWS_REGION) as rico:
            table = await rico.Table(DYNAMODB_TABLE_NAME)
            response: Dict[str, Any] = await table.scan()
            return response.get("Items", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database scan failed: {str(e)}")

@app.post("/user", response_model=UserResponse, status_code=201)
async def create_user(name: str = Form(...), email: EmailStr = Form(...), avatar: UploadFile = File(...)) -> Dict[str, str]:
    """
    Creates a new user.
    :param name: The user's name.
    :param email: The user's email address.
    :param avatar: The user's avatar image file.
    :return: The created user's data.
    """
    avatar_url: str = await _upload_avatar_to_s3(avatar)
    user_data: Dict[str, str] = await _save_user_to_dynamodb(name, email, avatar_url)
    return user_data

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", log_level="info")
