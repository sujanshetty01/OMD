import os
import psycopg2
import pymysql
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.ingestion.ometa.auth_provider import OpenMetadataAuthenticationProvider
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import OpenMetadataConnection, AuthProvider
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import OpenMetadataJWTClientConfig
from metadata.generated.schema.entity.data.table import Table, TableData

# Configuration
OM_HOST = os.getenv("OPENMETADATA_HOST", "https://promptiq-in.free-1.getcollate.cloud/api")
OM_TOKEN = os.getenv("OPENMETADATA_TOKEN", "")

# Load .env if token missing
if not OM_TOKEN:
    try:
        with open("../.env") as f:
            for line in f:
                if "OPENMETADATA_TOKEN" in line:
                    OM_TOKEN = line.split("=", 1)[1].strip().strip('"')
    except: pass

print(f"Connecting to OM: {OM_HOST}")

# Setup Client
config = OpenMetadataConnection(
    hostPort=OM_HOST,
    authProvider=AuthProvider.openmetadata,
    securityConfig=OpenMetadataJWTClientConfig(jwtToken=OM_TOKEN)
)
metadata = OpenMetadata(config)

from metadata.generated.schema.api.data.createTable import CreateTableRequest
from metadata.generated.schema.api.data.createDatabase import CreateDatabaseRequest
from metadata.generated.schema.api.data.createDatabaseSchema import CreateDatabaseSchemaRequest
from metadata.generated.schema.entity.data.table import Column, DataType

def get_om_type(sql_type):
    # Basic mapping
    t = str(sql_type).lower()  # sql_type might be an int code from cursor
    # Mapping psycopgp2 type codes is hard without helper, assume string for simplicity or try to guess?
    # Actually, let's just default to STRING for prototype if we don't have type info.
    # But wait, cursor.description in psycopg2 gives type_code.
    # To be safe, we'll map everything to STRING for the AI's purpose (text search) unless we know better.
    return DataType.STRING

def push_sample_to_om(service_name, db_name, schema_name, table_name, columns, rows):
    fqn = f"{service_name}.{db_name}.{schema_name}.{table_name}"
    print(f"Processing {fqn} with {len(rows)} rows...")
    
    # 1. Ensure DB/Schema exist
    try:
        metadata.create_or_update(CreateDatabaseRequest(name=db_name, service=service_name))
        metadata.create_or_update(CreateDatabaseSchemaRequest(name=schema_name, database=f"{service_name}.{db_name}"))
    except: pass

    try:
        # 2. Create Table
        cols_om = [Column(name=c, dataType=DataType.STRING) for c in columns]
        create_req = CreateTableRequest(
            name=table_name,
            databaseSchema=f"{service_name}.{db_name}.{schema_name}",
            columns=cols_om
        )
        table = metadata.create_or_update(create_req)
        
        # 3. Push Sample Data via REST
        if table:
            # Format rows
            clean_rows = []
            for row in rows:
                clean_rows.append([str(c) for c in row])
            
            sample_data = {"columns": columns, "rows": clean_rows}
            
            # Use the underlying client to make the PUT request
            # Path: /v1/tables/{id}/sampleData
            path = f"/tables/{table.id.root}/sampleData"
            # root might be needed or not depending on pydantic version
            t_id = getattr(table.id, 'root', table.id)
            path = f"/tables/{t_id}/sampleData"
            
            metadata.client.put(path, data=sample_data)
            print(f"  ✅ Created table and pushed {len(rows)} sample rows to {fqn}.")
            
    except Exception as e:
        print(f"  ❌ Error processing {fqn}: {e}")

# --- Postgres ---
try:
    print("\n[Postgres] Reading data...")
    conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password="password", database="customers_db")
    cur = conn.cursor()
    
    # Customers
    cur.execute("SELECT * FROM customers LIMIT 50")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    push_sample_to_om("Local_Postgres_DB", "customers_db", "public", "customers", cols, rows)
    
    # Orders
    cur.execute("SELECT * FROM orders LIMIT 50")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    push_sample_to_om("Local_Postgres_DB", "customers_db", "public", "orders", cols, rows)
    
    conn.close()
except Exception as e:
    print(f"Postgres Connection Error: {e}")

# --- MySQL ---
try:
    print("\n[MySQL] Reading data...")
    conn = pymysql.connect(host="localhost", port=3306, user="admin", password="password", database="products_db")
    cur = conn.cursor()
    
    # Products
    cur.execute("SELECT * FROM products LIMIT 50")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    # MySQL usually uses 'default' schema name in some OMD versions, or db name repeated?
    # We will use 'default' for simplicity matching generic connectors
    push_sample_to_om("Local_MySQL_Inventory", "products_db", "default", "products", cols, rows)

    # Inventory
    cur.execute("SELECT * FROM inventory LIMIT 50")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    push_sample_to_om("Local_MySQL_Inventory", "products_db", "default", "inventory", cols, rows)

    conn.close()
except Exception as e:
    print(f"MySQL Connection Error: {e}")
