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

def run_profiler_cli(config_dict, filename):
    # write config to yaml
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        yaml.dump(config_dict, f)
    
    print(f"\n[Running Profiler] Config: {filename}")
    # Run the metadata CLI with 'profile' command
    cmd = ["./venv/bin/metadata", "profile", "-c", filename]
    
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

# --- 1. PostgreSQL Profiler Configuration ---
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
                "type": "Profiler",
                "processSampleData": True,
                "profileSample": 100.0,
                "includeTables": True,
                "includeViews": True,
                "markDeletedTables": True,
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

# --- 2. MySQL Profiler Configuration ---
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
                "type": "Profiler",
                "processSampleData": True,
                "profileSample": 100.0,
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
    run_profiler_cli(postgres_config, "temp_configs/postgres_profile.yaml")
    print("-" * 50)
    # Only run MySQL if desired, failure handled gracefully by return code print
    run_profiler_cli(mysql_config, "temp_configs/mysql_profile.yaml")
