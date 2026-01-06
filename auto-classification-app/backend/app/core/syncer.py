import pandas as pd
from app.integration.om_client import OMClient
from app.integration.vector_client import VectorClient
from app.core.data_lake_syncer import DataLakeSyncer
import psycopg2
import pymysql

def parse_fqn(fqn):
    """
    Parse FQN to extract source type, database, and table name
    Example: Local_Postgres_DB.customers_db.public.customers
    Returns: {'type': 'postgres', 'database': 'customers_db', 'schema': 'public', 'table': 'customers'}
    """
    parts = fqn.split('.')
    
    # Determine source type from service name
    service_name = parts[0] if len(parts) > 0 else ''
    source_type = 'unknown'
    
    if 'Postgres' in service_name:
        source_type = 'postgres'
    elif 'MySQL' in service_name or 'Inventory' in service_name:
        source_type = 'mysql'
    elif 'SAP' in service_name:
        source_type = 'sap'
    elif 'BigQuery' in service_name:
        source_type = 'bigquery'
    
    return {
        'type': source_type,
        'database': parts[1] if len(parts) > 1 else 'unknown',
        'schema': parts[2] if len(parts) > 2 else 'default',
        'table': parts[3] if len(parts) > 3 else parts[-1]
    }

def _clean_str(val):
    """Helper to clean Pydantic string representations like root='Name' or root=UUID(...)"""
    s = str(val)
    if s.startswith("root="):
        s = s[5:]
    
    if s.startswith("UUID('") and s.endswith("')"):
        return s[6:-2]
        
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
        
    return s

def fallback_fetch_data(fqn):
    """
    Directly fetches data from local DBs if OM doesn't have it.
    Mapping based on FQN.
    """
    rows = []
    cols = []
    
    try:
        # Postgres
        if "customers_db" in fqn:
            conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password="password", database="customers_db")
            cur = conn.cursor()
            path_parts = fqn.split('.')
            table_name = path_parts[-1]
            
            # Simple sanitization
            if table_name in ["customers", "orders"]:
                cur.execute(f"SELECT * FROM {table_name} LIMIT 50")
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
            conn.close()
            
        # MySQL
        elif "products_db" in fqn:
            conn = pymysql.connect(host="localhost", port=3306, user="admin", password="password", database="products_db")
            cur = conn.cursor()
            path_parts = fqn.split('.')
            table_name = path_parts[-1]
            if table_name in ["products", "inventory"]:
                cur.execute(f"SELECT * FROM {table_name} LIMIT 50")
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
            conn.close()
            
    except Exception as e:
        print(f"[Syncer] Fallback fetch failed for {fqn}: {e}")
        
    return cols, rows

def sync_om_to_vectordb():
    """
    Enhanced sync: Connects to OpenMetadata, discovers all tables,
    stores them in MinIO Data Lake, and indexes them into VectorDB for AI search.
    """
    print("[Syncer] Starting enhanced synchronization: OM → MinIO Data Lake → VectorDB...")
    
    om_client = OMClient()
    vector_client = VectorClient()
    lake_syncer = DataLakeSyncer()
    
    # 1. Fetch all tables from OpenMetadata
    tables = om_client.list_all_tables(fields=["columns", "tags", "sampleData"])
    
    print(f"[Syncer] Found {len(tables)} tables in OpenMetadata.")
    
    indexed_count = 0
    lake_stored_count = 0
    
    for table in tables:
        # Pydantic v1 vs v2 safety
        table_name = getattr(table.name, '__root__', table.name)
        fqn = getattr(table.fullyQualifiedName, '__root__', table.fullyQualifiedName)
        
        # Clean Pydantic strings
        table_name = _clean_str(table_name)
        fqn = _clean_str(fqn)
        
        # Skip internal system tables if needed, but for now we index everything
        print(f"[Syncer] Processing: {fqn}...")
        
        # 2. Check for Sample Data
        columns = []
        rows = []
        
        if hasattr(table, 'sampleData') and table.sampleData:
            sample_data = table.sampleData
            columns = sample_data.columns
            rows = sample_data.rows
        
        # Fallback if empty and it's a known source
        if not rows and ("customers_db" in fqn or "products_db" in fqn):
            print(f"[Syncer]   - No OM sample data for {fqn}. Attempting direct fallback fetch...")
            columns, rows = fallback_fetch_data(fqn)
            
        if rows:
            print(f"[Syncer]   - Found {len(rows)} sample rows.")
            
            # Convert to DataFrame
            df_data = []
            for r in rows:
                df_data.append(list(r))
                
            df = pd.DataFrame(df_data, columns=columns if columns else None)
            
            # 3. STORE IN MINIO DATA LAKE (NEW!)
            source_info = parse_fqn(fqn)
            lake_result = lake_syncer.sync_source_to_lake(
                source_type=source_info['type'],
                database=source_info['database'],
                table_name=source_info['table'],
                df=df
            )
            
            if lake_result:
                lake_stored_count += 1
            
            # 4. Index into ChromaDB for AI
            # Collect tags for better search context
            all_tags = set()
            
            # Table tags
            if hasattr(table, 'tags') and table.tags:
                for t in table.tags:
                    fqn = getattr(t.tagFQN, '__root__', t.tagFQN)
                    all_tags.add(fqn)
            
            # Column tags
            if hasattr(table, 'columns') and table.columns:
                for col in table.columns:
                    if hasattr(col, 'tags') and col.tags:
                        for t in col.tags:
                            fqn = getattr(t.tagFQN, '__root__', t.tagFQN)
                            all_tags.add(fqn)

            num_docs = vector_client.index_dataset(fqn, df, list(all_tags))
            print(f"[Syncer]   - Successfully indexed {num_docs} documents in VectorDB (Tags: {list(all_tags)}).")
            indexed_count += 1
        else:
            print("[Syncer]   - Sample data is empty (0 rows). Skipping.")
    
    # Get Data Lake statistics
    lake_stats = lake_syncer.get_lake_stats()
    
    print(f"\n[Syncer] ═══════════════════════════════════════════════════")
    print(f"[Syncer] Synchronization Complete!")
    print(f"[Syncer] ───────────────────────────────────────────────────")
    print(f"[Syncer] 📊 Tables Scanned: {len(tables)}")
    print(f"[Syncer] 🗄️  Data Lake Stored: {lake_stored_count} tables")
    print(f"[Syncer] 🔍 VectorDB Indexed: {indexed_count} datasets")
    print(f"[Syncer] ───────────────────────────────────────────────────")
    print(f"[Syncer] 💾 Data Lake Stats:")
    print(f"[Syncer]    Total Tables: {lake_stats['total_tables']}")
    print(f"[Syncer]    Total Size: {lake_stats['total_size_mb']:.2f} MB ({lake_stats['total_size_gb']:.4f} GB)")
    print(f"[Syncer]    By Source: {lake_stats['sources']}")
    print(f"[Syncer] ═══════════════════════════════════════════════════\n")
    
    return {
        "status": "success", 
        "indexed_count": indexed_count,
        "lake_stored_count": lake_stored_count,
        "total_scanned": len(tables),
        "lake_stats": lake_stats
    }
