import boto3
import os
from botocore.client import Config

class MinioClient:
    def __init__(self):
        self.endpoint = "localhost:9000"
        self.access_key = "minioadmin"
        self.secret_key = "minioadmin"
        self.bucket_name = "raw-data"
        
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http://{self.endpoint}",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except:
            self.client.create_bucket(Bucket=self.bucket_name)

    def upload_file(self, file_path, object_name=None):
        if object_name is None:
            object_name = os.path.basename(file_path)
        
        try:
            self.client.upload_file(file_path, self.bucket_name, object_name)
            return f"s3://{self.bucket_name}/{object_name}"
        except Exception as e:
            print(f"MinIO Upload failed: {e}")
            return None

    def get_file_url(self, object_name):
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": object_name},
            ExpiresIn=3600,
        )
