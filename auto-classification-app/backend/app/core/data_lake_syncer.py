import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
import io
from app.integration.minio_client import MinioClient

class DataLakeSyncer:
    """
    Manages synchronization of data from various sources to MinIO Data Lake
    Stores data in efficient Parquet format with versioning support
    """
    
    def __init__(self):
        self.minio = MinioClient()
        self.data_lake_bucket = 'data-lake'
        self._ensure_bucket()
        
    def _ensure_bucket(self):
        """Ensure data-lake bucket exists"""
        try:
            self.minio.client.head_bucket(Bucket=self.data_lake_bucket)
        except:
            try:
                self.minio.client.create_bucket(Bucket=self.data_lake_bucket)
                print(f"[DataLake] Created bucket: {self.data_lake_bucket}")
            except Exception as e:
                print(f"[DataLake] Bucket creation note: {e}")
    
    def sync_source_to_lake(self, source_type, database, table_name, df):
        """
        Stores data from any source into MinIO in Parquet format
        
        Args:
            source_type: 'postgres', 'mysql', 'sap', 'api', etc.
            database: database name
            table_name: table name
            df: pandas DataFrame with the data
            
        Returns:
            dict: Information about stored data
        """
        if df is None or df.empty:
            print(f"[DataLake] Skipping empty dataset: {source_type}/{database}/{table_name}")
            return None
            
        # Create object path
        object_path = f"sources/{source_type}/{database}/{table_name}.parquet"
        
        try:
            # Convert to Parquet (efficient columnar format)
            parquet_buffer = io.BytesIO()
            df.to_parquet(
                parquet_buffer, 
                engine='pyarrow', 
                compression='snappy',
                index=False
            )
            parquet_buffer.seek(0)
            
            # Upload to MinIO
            self.minio.client.put_object(
                Bucket=self.data_lake_bucket,
                Key=object_path,
                Body=parquet_buffer,
                ContentType='application/parquet'
            )
            
            size_bytes = parquet_buffer.tell()
            
            # Also create timestamped snapshot
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            snapshot_path = f"snapshots/{source_type}/{database}/{table_name}_{timestamp}.parquet"
            
            parquet_buffer.seek(0)
            self.minio.client.put_object(
                Bucket=self.data_lake_bucket,
                Key=snapshot_path,
                Body=parquet_buffer,
                ContentType='application/parquet'
            )
            
            result = {
                'current': f"s3://{self.data_lake_bucket}/{object_path}",
                'snapshot': f"s3://{self.data_lake_bucket}/{snapshot_path}",
                'rows': len(df),
                'columns': len(df.columns),
                'size_mb': size_bytes / (1024 * 1024),
                'timestamp': timestamp
            }
            
            print(f"[DataLake] ✅ Stored {result['rows']} rows, {result['columns']} cols ({result['size_mb']:.2f} MB) -> {object_path}")
            
            return result
            
        except Exception as e:
            print(f"[DataLake] ❌ Failed to store {source_type}/{database}/{table_name}: {e}")
            return None
    
    def read_from_lake(self, source_type, database, table_name):
        """
        Reads data from MinIO data lake
        
        Returns:
            pandas DataFrame or None
        """
        object_path = f"sources/{source_type}/{database}/{table_name}.parquet"
        
        try:
            response = self.minio.client.get_object(
                Bucket=self.data_lake_bucket,
                Key=object_path
            )
            
            parquet_data = response['Body'].read()
            df = pd.read_parquet(io.BytesIO(parquet_data))
            
            print(f"[DataLake] 📖 Read {len(df)} rows from {object_path}")
            return df
            
        except Exception as e:
            print(f"[DataLake] Failed to read from data lake: {e}")
            return None
    
    def list_available_tables(self):
        """
        Lists all tables available in the data lake
        
        Returns:
            list: Table metadata
        """
        tables = []
        
        try:
            response = self.minio.client.list_objects_v2(
                Bucket=self.data_lake_bucket,
                Prefix='sources/'
            )
            
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.parquet'):
                    parts = key.split('/')
                    if len(parts) >= 4:
                        tables.append({
                            'source_type': parts[1],
                            'database': parts[2],
                            'table': parts[3].replace('.parquet', ''),
                            'size_bytes': obj['Size'],
                            'size_mb': obj['Size'] / (1024 * 1024),
                            'last_modified': obj['LastModified'],
                            'path': key
                        })
            
            print(f"[DataLake] Found {len(tables)} tables in data lake")
            return tables
            
        except Exception as e:
            print(f"[DataLake] Failed to list tables: {e}")
            return []
    
    def get_lake_stats(self):
        """
        Get statistics about the data lake
        
        Returns:
            dict: Lake statistics
        """
        tables = self.list_available_tables()
        
        total_size = sum(t['size_bytes'] for t in tables)
        
        stats = {
            'total_tables': len(tables),
            'total_size_mb': total_size / (1024 * 1024),
            'total_size_gb': total_size / (1024 * 1024 * 1024),
            'sources': {},
            'databases': {}
        }
        
        # Group by source type
        for table in tables:
            source = table['source_type']
            db = table['database']
            
            if source not in stats['sources']:
                stats['sources'][source] = {'count': 0, 'size_mb': 0}
            stats['sources'][source]['count'] += 1
            stats['sources'][source]['size_mb'] += table['size_mb']
            
            if db not in stats['databases']:
                stats['databases'][db] = {'count': 0, 'size_mb': 0}
            stats['databases'][db]['count'] += 1
            stats['databases'][db]['size_mb'] += table['size_mb']
        
        return stats
