import io
import uuid
from dataclasses import dataclass
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

from app.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@dataclass(frozen=True)
class StoredImage:
    key: str
    content_type: str
    data: bytes


class ImageStorage(Protocol):
    def put(self, user_id: str, data: bytes, content_type: str) -> str: ...
    def get(self, key: str) -> StoredImage: ...


class S3ImageStorage:
    def __init__(self) -> None:
        self.bucket = settings.image_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def put(self, user_id: str, data: bytes, content_type: str) -> str:
        suffix = ALLOWED_IMAGE_TYPES.get(content_type)
        if suffix is None:
            raise ValueError("unsupported image type")
        key = f"captures/{user_id}/{uuid.uuid4()}{suffix}"
        self.client.upload_fileobj(
            io.BytesIO(data),
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key

    def get(self, key: str) -> StoredImage:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return StoredImage(
            key=key,
            content_type=response.get("ContentType") or "application/octet-stream",
            data=response["Body"].read(),
        )


class MemoryImageStorage:
    """Test adapter with the same contract as the object store."""

    def __init__(self) -> None:
        self.objects: dict[str, StoredImage] = {}

    def put(self, user_id: str, data: bytes, content_type: str) -> str:
        suffix = ALLOWED_IMAGE_TYPES.get(content_type)
        if suffix is None:
            raise ValueError("unsupported image type")
        key = f"captures/{user_id}/{uuid.uuid4()}{suffix}"
        self.objects[key] = StoredImage(key, content_type, data)
        return key

    def get(self, key: str) -> StoredImage:
        return self.objects[key]


def get_image_storage() -> ImageStorage:
    return S3ImageStorage()
