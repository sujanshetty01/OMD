import os
import time
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.ingestion.ometa.auth_provider import OpenMetadataAuthenticationProvider
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import OpenMetadataConnection, AuthProvider
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import OpenMetadataJWTClientConfig
from metadata.generated.schema.entity.data.table import Table, Column, DataType, TableData
from metadata.generated.schema.entity.data.database import Database
from metadata.generated.schema.entity.data.databaseSchema import DatabaseSchema
from metadata.generated.schema.entity.services.databaseService import DatabaseService
from metadata.generated.schema.api.data.createTable import CreateTableRequest
from metadata.generated.schema.api.data.createDatabase import CreateDatabaseRequest
from metadata.generated.schema.api.data.createDatabaseSchema import CreateDatabaseSchemaRequest

import psycopg2
import pymysql

# --- Configuration ---
OM_HOST = os.getenv("OPENMETADATA_HOST", "https://promptiq-in.free-1.getcollate.cloud/api")
OM_TOKEN = os.getenv("OPENMETADATA_TOKEN", "")

# Fallback load from .env
if not OM_TOKEN:
    try:
        with open("../.env") as f:
            for line in f:
                if "OPENMETADATA_TOKEN" in line:
                    OM_TOKEN = line.split("=", 1)[1].strip().strip('"')
    except: pass

print(f"Connecting to OpenMetadata: {OM_HOST}")

# --- Setup OM Client ---
config = OpenMetadataConnection(
    hostPort=OM_HOST,
    authProvider=AuthProvider.openmetadata,
    securityConfig=OpenMetadataJWTClientConfig(jwtToken=OM_TOKEN)
)
metadata = OpenMetadata(config)

def get_om_type(sql_type):
    sql_type = sql_type.lower()
    if "int" in sql_type: return DataType.INT
    if "char" in sql_type or "text" in sql_type: return DataType.STRING
    if "float" in sql_type or "decimal" in sql_type or "numeric" in sql_type: return DataType.DOUBLE
    if "date" in sql_type or "time" in sql_type: return DataType.TIMESTAMP
    return DataType.STRING

def push_table(service_name, db_name, schema_name, table_name, columns, rows):
    print(f"Pushing {table_name} to {service_name}...")
    
    # 1. Ensure Hierarchy (Best Effort - service might exist)
    # Database
    db_fqn = f"{service_name}.{db_name}"
    try:
        metadata.create_or_update(CreateDatabaseRequest(name=db_name, service=service_name))
    except Exception as e: print(f"  Note: DB creation skipped/failed ({e})")

    # Schema
    schema_fqn = f"{db_fqn}.{schema_name}"
    try:
        metadata.create_or_update(CreateDatabaseSchemaRequest(name=schema_name, database=db_fqn))
    except Exception as e: print(f"  Note: Schema creation skipped/failed ({e})")

    # 2. Create Table
    om_columns = []
    for col_name, col_type in columns:
        om_columns.append(Column(name=col_name, dataType=get_om_type(col_type)))
    
    table_req = CreateTableRequest(
        name=table_name,
        databaseSchema=schema_fqn,
        columns=om_columns
    )
    
    try:
        table_entity = metadata.create_or_update(table_req)
        print(f"  ✅ Table {table_name} created.")
        
        # 3. Push Sample Data
        if rows:
            # TableData expects columns list and rows list of lists
            # We need to ensure rows are serializable (dates to strings)
            clean_rows = []
            for row in rows:
                clean_row = []
                for item in row:
                    if hasattr(item, 'isoformat'): clean_row.append(item.isoformat())
                    else: clean_row.append(str(item))
                clean_rows.append(clean_row)
            
            table_entity.sampleData = TableData(columns=[c[0] for c in columns], rows=clean_rows)
            metadata.create_or_update(table_entity)
            print(f"  ✅ Uploaded {len(rows)} sample rows.")
            
    except Exception as e:
        print(f"  ❌ Failed to push table {table_name}: {e}")

# --- Postgres ---
try:
    print("\n--- Processing Postgres ---")
    conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password="password", database="customers_db")
    cur = conn.cursor()
    
    # Customers
    cur.execute("SELECT * FROM customers")
    rows = cur.fetchall()
    cols = [(desc[0], "string") for desc in cur.description] # generic type for now
    push_table("Local_Postgres_DB", "customers_db", "public", "customers", cols, rows)
    
    # Orders
    cur.execute("SELECT * FROM orders")
    rows = cur.fetchall()
    cols = [(desc[0], "string") for desc in cur.description] 
    push_table("Local_Postgres_DB", "customers_db", "public", "orders", cols, rows)
    
    conn.close()
except Exception as e:
    print(f"Postgres Error: {e}")

# --- MySQL ---
try:
    print("\n--- Processing MySQL ---")
    conn = pymysql.connect(host="localhost", port=3306, user="admin", password="password", database="products_db")
    cur = conn.cursor()
    
    # Products
    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()
    cols = [(desc[0], "string") for desc in cur.description]
    push_table("Local_MySQL_Inventory", "products_db", "default", "products", cols, rows)

    # Inventory
    cur.execute("SELECT * FROM inventory")
    rows = cur.fetchall()
    cols = [(desc[0], "string") for desc in cur.description]
    push_table("Local_MySQL_Inventory", "products_db", "default", "inventory", cols, rows)

    conn.close()
except Exception as e:
    print(f"MySQL Error: {e}")
