import boto3
import os
from typing import List, Dict, Any

class AWSClient:
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # We allow initialization even if keys are missing, 
        # but operations will fail if called.
        self.client = boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )

    def list_buckets(self) -> List[str]:
        """List all available S3 buckets"""
        try:
            response = self.client.list_buckets()
            return [b["Name"] for b in response.get("Buckets", [])]
        except Exception as e:
            print(f"Error listing AWS buckets: {e}")
            raise e

    def list_objects(self, bucket_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects in a specific bucket with optional prefix"""
        try:
            response = self.client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            params = ["Key", "Size", "LastModified"]
            results = []
            for obj in response.get("Contents", []):
                results.append({k: obj[k] for k in params if k in obj})
            return results
        except Exception as e:
            print(f"Error listing objects in bucket {bucket_name}: {e}")
            raise e

    def download_file(self, bucket_name: str, key: str, dest_path: str):
        """Download an S3 object to a local file path"""
        try:
            self.client.download_file(bucket_name, key, dest_path)
            return dest_path
        except Exception as e:
            print(f"Error downloading file {key} from {bucket_name}: {e}")
            raise e
