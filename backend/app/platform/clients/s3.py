"""S3 client abstraction.

LocalS3Client  — stores files under backend/uploads/ for dev/test.
S3Client       — aioboto3-backed real AWS S3 client.

Provides bytes-level get/put plus path-based upload/download and presigned URL
generation used by the media and document upload flows.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseS3Client(ABC):
    @abstractmethod
    async def get_bytes(self, bucket: str, key: str) -> bytes: ...

    @abstractmethod
    async def put_bytes(
        self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None: ...

    @abstractmethod
    async def download(self, bucket: str, key: str, local_path: str | Path) -> None: ...

    @abstractmethod
    async def upload(
        self, bucket: str, key: str, local_path: str | Path, content_type: str = "application/octet-stream"
    ) -> None: ...

    @abstractmethod
    async def delete_file(self, bucket: str, key: str) -> None: ...

    @abstractmethod
    async def file_exists(self, bucket: str, key: str) -> bool: ...

    @abstractmethod
    def generate_presigned_upload_url(self, bucket: str, key: str, content_type: str, expires_in: int = 300) -> str: ...

    @abstractmethod
    def generate_presigned_download_url(self, bucket: str, key: str, expires_in: int = 3600) -> str: ...


class LocalS3Client(BaseS3Client):
    """Stores objects on the local filesystem under `uploads/{bucket}/{key}`.

    Presigned URLs are mock URLs pointing back at the dev API; the frontend
    uploads via a normal multipart POST in dev rather than a real S3 PUT.
    """

    def __init__(self, uploads_dir: str | Path = "uploads") -> None:
        self._root = Path(uploads_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, bucket: str, key: str) -> Path:
        return self._root / bucket / key.lstrip("/")

    async def get_bytes(self, bucket: str, key: str) -> bytes:
        p = self._path(bucket, key)
        if not p.exists():
            raise FileNotFoundError(f"LocalS3: s3://{bucket}/{key} not found")
        return p.read_bytes()

    async def put_bytes(
        self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        p = self._path(bucket, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    async def download(self, bucket: str, key: str, local_path: str | Path) -> None:
        src = self._path(bucket, key)
        if not src.exists():
            raise FileNotFoundError(f"LocalS3: s3://{bucket}/{key} not found")
        dst = Path(local_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

    async def upload(
        self, bucket: str, key: str, local_path: str | Path, content_type: str = "application/octet-stream"
    ) -> None:
        src = Path(local_path)
        dst = self._path(bucket, key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

    async def delete_file(self, bucket: str, key: str) -> None:
        p = self._path(bucket, key)
        if p.exists():
            p.unlink()

    async def file_exists(self, bucket: str, key: str) -> bool:
        return self._path(bucket, key).exists()

    def generate_presigned_upload_url(self, bucket: str, key: str, content_type: str, expires_in: int = 300) -> str:
        return f"http://localhost:8000/local-upload/{bucket}/{key.lstrip('/')}"

    def generate_presigned_download_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        return f"http://localhost:8000/local-download/{bucket}/{key.lstrip('/')}"


class S3Client(BaseS3Client):
    """AWS S3 client backed by aioboto3 / boto3."""

    def __init__(self, region: str) -> None:
        self._region = region

    async def get_bytes(self, bucket: str, key: str) -> bytes:
        import aioboto3  # noqa: PLC0415

        session = aioboto3.Session()
        async with session.client("s3", region_name=self._region) as client:  # type: ignore[reportGeneralTypeIssues]
            response = await client.get_object(Bucket=bucket, Key=key)
            async with response["Body"] as stream:
                return await stream.read()

    async def put_bytes(
        self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        import aioboto3  # noqa: PLC0415

        session = aioboto3.Session()
        async with session.client("s3", region_name=self._region) as client:  # type: ignore[reportGeneralTypeIssues]
            await client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

    async def download(self, bucket: str, key: str, local_path: str | Path) -> None:
        import aioboto3  # noqa: PLC0415

        dst = Path(local_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        session = aioboto3.Session()
        async with session.client("s3", region_name=self._region) as client:  # type: ignore[reportGeneralTypeIssues]
            await client.download_file(bucket, key, str(dst))

    async def upload(
        self, bucket: str, key: str, local_path: str | Path, content_type: str = "application/octet-stream"
    ) -> None:
        import aioboto3  # noqa: PLC0415

        session = aioboto3.Session()
        async with session.client("s3", region_name=self._region) as client:  # type: ignore[reportGeneralTypeIssues]
            await client.upload_file(str(local_path), bucket, key, ExtraArgs={"ContentType": content_type})

    async def delete_file(self, bucket: str, key: str) -> None:
        import aioboto3  # noqa: PLC0415

        session = aioboto3.Session()
        async with session.client("s3", region_name=self._region) as client:  # type: ignore[reportGeneralTypeIssues]
            await client.delete_object(Bucket=bucket, Key=key)

    async def file_exists(self, bucket: str, key: str) -> bool:
        import aioboto3  # noqa: PLC0415

        session = aioboto3.Session()
        async with session.client("s3", region_name=self._region) as client:  # type: ignore[reportGeneralTypeIssues]
            try:
                await client.head_object(Bucket=bucket, Key=key)
                return True
            except Exception:
                return False

    def generate_presigned_upload_url(self, bucket: str, key: str, content_type: str, expires_in: int = 300) -> str:
        import boto3  # noqa: PLC0415

        client = boto3.client("s3", region_name=self._region)
        return client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )

    def generate_presigned_download_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        import boto3  # noqa: PLC0415

        client = boto3.client("s3", region_name=self._region)
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
