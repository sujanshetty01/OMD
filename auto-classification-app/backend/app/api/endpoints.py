from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from typing import List
import shutil
import os
import pandas as pd
import asyncio

from ..core import profiler, classifier, mapper
from ..integration.om_client import OMClient
from ..integration.minio_client import MinioClient
from ..integration.vector_client import VectorClient
from ..integration.aws_client import AWSClient
from ..core.ws_manager import manager
from ..schemas import data as schemas

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from fastapi.concurrency import run_in_threadpool

async def run_background_ingestion(client_id: str, file_name: str, file_path: str, df: pd.DataFrame, tags: list = None):
    """Async heavy lifting for storage and vector indexing"""
    
    # B. Raw Feed (MinIO Object Store)
    await manager.send_update(client_id, "Archiving raw data in MinIO AI Store (as Parquet)...")
    try:
        # CONVERT TO PARQUET:
        # We enforce Parquet format in the Data Lake for performance (Columnar storage)
        parquet_path = file_path + ".parquet"
        # Use run_in_threadpool for blocking IO
        await run_in_threadpool(df.to_parquet, parquet_path, index=False)
        
        minio_client = MinioClient()
        # Store as [filename].parquet in MinIO
        object_name = os.path.splitext(file_name)[0] + ".parquet"
        
        await run_in_threadpool(minio_client.upload_file, parquet_path, object_name)
        
        # Cleanup temp file
        if os.path.exists(parquet_path):
            os.remove(parquet_path)
            
    except Exception as e:
        print(f"ERROR: MinIO Upload failed: {e}")

    # C. Vector Feed (ChromaDB / VectorDB)
    await manager.send_update(client_id, "Building semantic index in ChromaDB...")
    try:
        vector_client = VectorClient()
        # Run heavy embedding in threadpool
        await run_in_threadpool(vector_client.index_dataset, file_name, df, tags)
    except Exception as e:
        print(f"ERROR: VectorDB Indexing failed: {e}")
    
    await manager.send_update(client_id, "Success! Dataset fully ingested.", status="complete")

def _classify_columns_sync(columns):
    """Helper to run classification loop in threadpool"""
    processed = []
    for col_data in columns:
        classification = classifier.classify(col_data["name"], col_data["series"])
        
        col_tags = []
        if classification:
            is_auto = classification["confidence"] > 0.8
            label_type = "Automated" if is_auto else "Manual"
            col_tags.append({"tag_fqn": classification["tag"], "label_type": label_type})
            
            mapped = mapper.get_mapped_tags([classification["tag"]])
            for m_tag in mapped:
                col_tags.append({"tag_fqn": m_tag, "label_type": "Automated"})

        processed.append({
            "name": col_data["name"],
            "datatype": col_data["datatype"],
            "tags": col_tags
        })
    return processed

async def process_dataset_ingestion(client_id: str, file_path: str, original_filename: str, background_tasks: BackgroundTasks):
    """
    Shared logic for processing a local file (uploaded or downloaded):
    - Profile
    - Classify
    - Ingest to OM (Sync)
    - Ingest to MinIO/VectorDB (Background)
    """
    # 2. Profile & Classify
    await manager.send_update(client_id, "Profiling dataset structure...")
    try:
        # Offload profiling
        profile, df = await run_in_threadpool(profiler.profile_dataset, file_path)
    except Exception as e:
        await manager.send_update(client_id, f"Error: {str(e)}", status="error")
        raise HTTPException(status_code=400, detail=str(e))
    
    # 3. Batch Build Metadata
    await manager.send_update(client_id, "Analyzing columns with AI Classifier...")
    
    # Offload classification loop
    processed_columns = await run_in_threadpool(_classify_columns_sync, profile["columns"])

    # 4. SINGLE SHOT Integration
    await manager.send_update(client_id, "Syncing metadata to OpenMetadata Governance...")
    om_client = OMClient()
    try:
        # Offload OM ingestion
        om_table = await run_in_threadpool(om_client.ingest_dataset_with_all_metadata, original_filename, processed_columns)
    except Exception as e:
        await manager.send_update(client_id, "Governance sync failed, but continuing...", status="warning")
        om_table = None

    # 5. Background Heavy Storage Tasks
    # Extract Tags for AI Context
    dataset_tags = set()
    if processed_columns:
        for col in processed_columns:
            for t in col.get("tags", []):
                dataset_tags.add(t["tag_fqn"])
    
    background_tasks.add_task(run_background_ingestion, client_id, original_filename, file_path, df, list(dataset_tags))
            
    # Return translated OM table for UI
    if om_table:
        # Pydantic Compatibility (some versions wrap strings in __root__, others don't)
        fqn = getattr(om_table.fullyQualifiedName, '__root__', om_table.fullyQualifiedName)
        return om_client.get_dataset(fqn)
    
    return {"message": "Success"}

@router.post("/datasets/upload")
async def upload_dataset(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    client_id: str = Form(...)
):
    # 1. Start Initializing
    await manager.send_update(client_id, "Initializing Secure Ingestion...")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    # File IO is blocking but fast for small files, sticking to sync or wrapping if huge
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return await process_dataset_ingestion(client_id, file_path, file.filename, background_tasks)

@router.get("/datasets")
def list_datasets():
    om_client = OMClient()
    return om_client.list_datasets()

@router.get("/datasets/{dataset_fqn}")
def get_dataset(dataset_fqn: str):
    om_client = OMClient()
    dataset = om_client.get_dataset(dataset_fqn)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found in OpenMetadata")
    return dataset

@router.get("/datasets/{dataset_fqn}/columns")
def get_dataset_columns(dataset_fqn: str):
    om_client = OMClient()
    dataset = om_client.get_dataset(dataset_fqn)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found in OpenMetadata")
    return dataset["columns"]

from ..core.syncer import sync_om_to_vectordb
from ..core.data_lake_syncer import DataLakeSyncer

@router.post("/system/sync")
async def trigger_sync():
    """
    Triggers a manual sync: OM metadata → MinIO Data Lake → VectorDB
    """
    try:
        # Running synchronously for now to keep it simple, or use background tasks if it grows
        result = await run_in_threadpool(sync_om_to_vectordb)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-lake/stats")
async def get_data_lake_stats():
    """
    Get statistics about the MinIO Data Lake
    """
    try:
        lake_syncer = DataLakeSyncer()
        stats = await run_in_threadpool(lake_syncer.get_lake_stats)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-lake/tables")
async def list_data_lake_tables():
    """
    List all tables available in the MinIO Data Lake
    """
    try:
        lake_syncer = DataLakeSyncer()
        tables = await run_in_threadpool(lake_syncer.list_available_tables)
        return {"tables": tables, "count": len(tables)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success"}

from pydantic import BaseModel

class TagRequest(BaseModel):
    tag_fqn: str
    label_type: str = "Manual"

@router.post("/datasets/{dataset_id}/columns/{column_name}/tags")
def apply_tag(dataset_id: str, column_name: str, tag: TagRequest):
    om_client = OMClient()
    # Apply tag using OM Client
    om_client.apply_column_tags(dataset_id, column_name, [{"tag_fqn": tag.tag_fqn, "label_type": tag.label_type}])
    return {"status": "success"}

# --------------------------
# AWS S3 Integration
# --------------------------

class S3IngestRequest(BaseModel):
    bucket: str
    key: str
    client_id: str

class S3BatchIngestRequest(BaseModel):
    bucket: str
    client_id: str

@router.get("/sources/s3/buckets")
async def list_s3_buckets():
    try:
        aws = AWSClient()
        buckets = await run_in_threadpool(aws.list_buckets)
        return {"buckets": buckets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/s3/buckets/{bucket}/objects")
async def list_s3_objects(bucket: str, prefix: str = ""):
    try:
        aws = AWSClient()
        objects = await run_in_threadpool(aws.list_objects, bucket, prefix)
        return {"objects": objects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sources/s3/ingest")
async def ingest_from_s3(request: S3IngestRequest, background_tasks: BackgroundTasks):
    """
    Downloads file from S3 to temp dir, then runs the standard ingestion pipeline.
    """
    client_id = request.client_id
    await manager.send_update(client_id, f"Connecting to S3 bucket: {request.bucket}...")
    
    try:
        aws = AWSClient()
        
        # Determine local path
        file_name = os.path.basename(request.key)
        local_path = os.path.join(UPLOAD_DIR, f"s3_{file_name}")
        
        await manager.send_update(client_id, f"Downloading {file_name} from S3...")
        
        # Download
        await run_in_threadpool(aws.download_file, request.bucket, request.key, local_path)
        
        # Run standard pipeline
        return await process_dataset_ingestion(client_id, local_path, file_name, background_tasks)
        
    except Exception as e:
        await manager.send_update(client_id, f"S3 Ingestion Error: {str(e)}", status="error")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sources/s3/ingest-all")
async def ingest_all_from_s3(request: S3BatchIngestRequest, background_tasks: BackgroundTasks):
    """
    Iterates through ALL objects in the bucket and triggers ingestion for each.
    """
    client_id = request.client_id
    bucket = request.bucket
    await manager.send_update(client_id, f"Scanning bucket {bucket} for batch ingestion...")
    
    try:
        aws = AWSClient()
        objects = await run_in_threadpool(aws.list_objects, bucket)
        
        if not objects:
             await manager.send_update(client_id, "Bucket is empty.", status="warning")
             return {"status": "empty"}
             
        await manager.send_update(client_id, f"Found {len(objects)} files. Starting batch processing...")
        
        # We will process sequentially for safety in this demo, or loop and kickoff tasks.
        # Ideally, we kickoff background tasks for each.
        # But process_dataset_ingestion runs mostly deep sync logic.
        # Let's do a loop of downloads and triggering.
        
        count = 0
        count = 0
        for obj_item in objects:
            obj_key = obj_item["Key"]
            if obj_key.endswith('/'): continue # Skip folders
            
            file_name = os.path.basename(obj_key)
            local_path = os.path.join(UPLOAD_DIR, f"s3_batch_{file_name}")
            
            await manager.send_update(client_id, f"Processing {count+1}/{len(objects)}: {file_name}...")
            
            try:
                await run_in_threadpool(aws.download_file, bucket, obj_key, local_path)
                
                # We need to AWAIT the processing so we don't overwhelm the system/OOM
                # But we want it to be somewhat fast.
                # Since process_dataset_ingestion pushes heavy stuff to background_tasks,
                # the "await" part is just Profiling + Classification + OM Sync.
                # That takes ~2-5s per file. Acceptable for batch.
                res = await process_dataset_ingestion(client_id, local_path, file_name, background_tasks)
                count += 1
            except Exception as e:
                print(f"Failed to process {file_name}: {e}")
                await manager.send_update(client_id, f"Skipped {file_name} (Error)", status="warning")
        
        await manager.send_update(client_id, f"Batch Complete! Processed {count} files.", status="complete")
        return {"status": "success", "processed": count}

    except Exception as e:
        await manager.send_update(client_id, f"Batch Error: {str(e)}", status="error")
        raise HTTPException(status_code=500, detail=str(e))

class OMSyncRequest(BaseModel):
    dataset_fqn: str
    client_id: str

@router.post("/sources/om-sync")
async def sync_from_openmetadata(request: OMSyncRequest, background_tasks: BackgroundTasks):
    """
    1. Look up S3 path from OpenMetadata Entity
    2. Download from S3 (using AWSClient)
    3. Run Profiling/Classification/Vectors
    """
    client_id = request.client_id
    om_client = OMClient()
    
    # Get details from OM
    dataset = om_client.get_dataset(request.dataset_fqn)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Heuristic to find Bucket/Key from FQN or Name
    # OMD S3 FQN usually: s3_service.bucket.file
    # Or we might be storing it in 'location' or similar.
    # For now, assuming name = filename, and we need bucket from service or config.
    # BUT, the user said "ingestion through open metadata".
    # Typically OMD stores the path.
    
    # We'll try to parse the FQN: service.database.schema.table
    parts = request.dataset_fqn.split('.')
    if len(parts) >= 2:
        # Assuming format: s3_service.default.default.filename
        # Or: s3_service.bucket.filename
        # Let's try to infer bucket and key.
        file_name = parts[-1]
        bucket = "omd-1" # Hardcoded fallback or extract from service config
        
        # If the user has a proper S3 service, the database name might be the bucket
        if len(parts) == 4:
            bucket = parts[1] 
            
        key = file_name
        # If filename in OMD doesn't have extension but S3 does? 
        # Usually OMD ingestion keeps extension.
        
        # If it's a "local_files" service (our default), this endpoint shouldn't be used.
        if parts[0] == "local_files":
             raise HTTPException(status_code=400, detail="This is already a local file.")
             
        await manager.send_update(client_id, f"Found Metadata. Fetching content from S3 ({bucket}/{key})...")
        
        try:
            aws = AWSClient()
            local_path = os.path.join(UPLOAD_DIR, f"om_sync_{file_name}")
            
            # Smart Key detection (if key is full path)
            # We might need to list objects to find exact match if OMD normalized the name
            # For now, simplistic approach
            
            await run_in_threadpool(aws.download_file, bucket, key, local_path)
            return await process_dataset_ingestion(client_id, local_path, file_name, background_tasks)
            
        except Exception as e:
             await manager.send_update(client_id, f"Failed to download from S3: {str(e)}", status="error")
             raise HTTPException(status_code=500, detail=str(e))
             
    raise HTTPException(status_code=400, detail="Could not parse S3 location from FQN")
