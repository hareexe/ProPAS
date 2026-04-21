import io
import os
from dataclasses import dataclass

DEFAULT_URL_EXPIRATION = 3600


@dataclass
class StorageSettings:
    backend: str
    local_upload_root: str
    bucket: str | None = None
    endpoint_url: str | None = None
    region: str | None = None
    key_prefix: str = ''
    url_expiration: int = DEFAULT_URL_EXPIRATION


class LocalStorage:
    def __init__(self, upload_root: str):
        self.upload_root = upload_root
        os.makedirs(self.upload_root, exist_ok=True)

    def _full_path(self, filename: str) -> str:
        return os.path.join(self.upload_root, filename)

    def save_upload(self, file_storage, filename: str) -> None:
        os.makedirs(self.upload_root, exist_ok=True)
        file_storage.save(self._full_path(filename))

    def write_bytes(self, filename: str, payload: bytes) -> None:
        os.makedirs(self.upload_root, exist_ok=True)
        with open(self._full_path(filename), 'wb') as handle:
            handle.write(payload)

    def read_bytes(self, filename: str) -> bytes:
        with open(self._full_path(filename), 'rb') as handle:
            return handle.read()

    def exists(self, filename: str) -> bool:
        return os.path.exists(self._full_path(filename))

    def full_path(self, filename: str) -> str:
        return self._full_path(filename)


class S3Storage:
    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        region: str | None = None,
        key_prefix: str = '',
        url_expiration: int = DEFAULT_URL_EXPIRATION,
    ):
        self.bucket = bucket
        self.key_prefix = (key_prefix or '').strip('/')
        self.url_expiration = url_expiration
        import boto3
        from botocore.config import Config

        session = boto3.session.Session()
        self.client = session.client(
            's3',
            region_name=region or None,
            endpoint_url=endpoint_url or None,
            config=Config(signature_version='s3v4'),
        )

    def _object_key(self, filename: str) -> str:
        cleaned = filename.lstrip('/').replace('\\', '/')
        return f'{self.key_prefix}/{cleaned}' if self.key_prefix else cleaned

    def save_upload(self, file_storage, filename: str) -> None:
        extra_args = {}
        if getattr(file_storage, 'mimetype', None):
            extra_args['ContentType'] = file_storage.mimetype
        file_storage.stream.seek(0)
        self.client.upload_fileobj(
            file_storage.stream,
            self.bucket,
            self._object_key(filename),
            ExtraArgs=extra_args or None,
        )

    def write_bytes(self, filename: str, payload: bytes, content_type: str | None = None) -> None:
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        self.client.upload_fileobj(
            io.BytesIO(payload),
            self.bucket,
            self._object_key(filename),
            ExtraArgs=extra_args or None,
        )

    def read_bytes(self, filename: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=self._object_key(filename))
        return response['Body'].read()

    def exists(self, filename: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=self._object_key(filename))
            return True
        except ClientError:
            return False

    def generate_url(self, filename: str, download_name: str | None = None) -> str:
        params = {'Bucket': self.bucket, 'Key': self._object_key(filename)}
        if download_name:
            params['ResponseContentDisposition'] = f'attachment; filename="{download_name}"'
        return self.client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=self.url_expiration,
        )


class StorageService:
    def __init__(self):
        self.backend_name = 'local'
        self.backend = None

    def init_app(self, app):
        upload_root = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
        backend_name = (app.config.get('STORAGE_BACKEND') or '').strip().lower()
        bucket = (app.config.get('S3_BUCKET') or '').strip()

        if backend_name == 's3' or (backend_name != 'local' and bucket):
            self.backend_name = 's3'
            self.backend = S3Storage(
                bucket=bucket,
                endpoint_url=app.config.get('S3_ENDPOINT_URL'),
                region=app.config.get('S3_REGION'),
                key_prefix=app.config.get('S3_KEY_PREFIX') or '',
                url_expiration=int(app.config.get('S3_URL_EXPIRATION') or DEFAULT_URL_EXPIRATION),
            )
        else:
            self.backend_name = 'local'
            self.backend = LocalStorage(upload_root)

    @property
    def is_remote(self) -> bool:
        return self.backend_name == 's3'

    def save_upload(self, file_storage, filename: str) -> None:
        self.backend.save_upload(file_storage, filename)

    def write_bytes(self, filename: str, payload: bytes, content_type: str | None = None) -> None:
        if self.is_remote:
            self.backend.write_bytes(filename, payload, content_type=content_type)
        else:
            self.backend.write_bytes(filename, payload)

    def read_bytes(self, filename: str) -> bytes:
        return self.backend.read_bytes(filename)

    def exists(self, filename: str) -> bool:
        return self.backend.exists(filename)

    def generate_download_url(self, filename: str, download_name: str | None = None) -> str:
        if not self.is_remote:
            raise RuntimeError('Download URL generation is only available for remote storage backends.')
        return self.backend.generate_url(filename, download_name=download_name)

    def local_full_path(self, filename: str) -> str | None:
        if self.is_remote:
            return None
        return self.backend.full_path(filename)


storage = StorageService()
