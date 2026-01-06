import os
import yaml
import sys
import subprocess
import glob

# Load Environment Variables from .env manually if needed
if not os.getenv("OPENMETADATA_HOST"):
    try:
        with open("../.env") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
    except Exception:
        pass

OM_HOST = os.getenv("OPENMETADATA_HOST", "https://promptiq-in.free-1.getcollate.cloud/api")
OM_TOKEN = os.getenv("OPENMETADATA_TOKEN", "")

if not OM_TOKEN:
    print("ERROR: OPENMETADATA_TOKEN not found.")
    sys.exit(1)

print(f"Target OpenMetadata: {OM_HOST}")
print(f"Token (first 10 chars): {OM_TOKEN[:10]}...")

def run_ingestion_cli(config_dict, filename):
    # write config to yaml
    with open(filename, 'w') as f:
        yaml.dump(config_dict, f)
    
    print(f"\n[Running Ingestion] Config: {filename}")
    # Run the metadata CLI
    cmd = ["./venv/bin/metadata", "ingest", "-c", filename]
    
    # Run and stream output
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Stream line by line
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(line.strip())
            
    if process.returncode == 0:
        print("✅ Success!")
    else:
        print("❌ Failed!")

# --- 1. PostgreSQL Configuration ---
postgres_config = {
    "source": {
        "type": "postgres",
        "serviceName": "Local_Postgres_DB",
        "serviceConnection": {
            "config": {
                "type": "Postgres",
                "hostPort": "localhost:5432",
                "username": "postgres",
                "authType": {
                    "password": "password"
                },
                "database": "customers_db",
                "scheme": "postgresql+psycopg2"
            }
        },
        "sourceConfig": {
            "config": {
                "type": "DatabaseMetadata",
                "markDeletedTables": True,
                "includeTables": True,
                "includeViews": True,
            }
        }
    },
    "sink": {
        "type": "metadata-rest",
        "config": {}
    },
    "workflowConfig": {
        "openMetadataServerConfig": {
            "hostPort": OM_HOST,
            "authProvider": "openmetadata",
            "securityConfig": {
                "jwtToken": OM_TOKEN
            }
        }
    }
}

# --- 2. MySQL Configuration ---
mysql_config = {
    "source": {
        "type": "mysql",
        "serviceName": "Local_MySQL_Inventory",
        "serviceConnection": {
            "config": {
                "type": "Mysql",
                "hostPort": "localhost:3306",
                "username": "admin",
                "authType": {
                    "password": "password"
                },
                "databaseSchema": "products_db",
                "scheme": "mysql+pymysql"
            }
        },
        "sourceConfig": {
            "config": {
                "type": "DatabaseMetadata",
                "markDeletedTables": True,
                "includeTables": True,
            }
        }
    },
    "sink": {
        "type": "metadata-rest",
        "config": {}
    },
    "workflowConfig": {
        "openMetadataServerConfig": {
            "hostPort": OM_HOST,
            "authProvider": "openmetadata",
            "securityConfig": {
                "jwtToken": OM_TOKEN
            }
        }
    }
}

if __name__ == "__main__":
    os.makedirs("temp_configs", exist_ok=True)
    run_ingestion_cli(postgres_config, "temp_configs/postgres.yaml")
    run_ingestion_cli(mysql_config, "temp_configs/mysql.yaml")
