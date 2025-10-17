import os
from dotenv import load_dotenv
import boto3

load_dotenv()  # lee .env montado por docker-compose

def whoami():
    sts = boto3.client("sts", region_name=os.getenv("AWS_REGION"))
    return sts.get_caller_identity()

def list_buckets():
    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
    return [b["Name"] for b in s3.list_buckets().get("Buckets", [])]

if __name__ == "__main__":
    print("Caller:", whoami())
    print("Buckets:", list_buckets())
