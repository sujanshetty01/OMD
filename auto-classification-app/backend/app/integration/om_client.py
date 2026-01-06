from metadata.ingestion.ometa.ometa_api import OpenMetadata
import os
from metadata.generated.schema.entity.data.table import Table, Column, DataType
from metadata.generated.schema.entity.data.database import Database
from metadata.generated.schema.entity.data.databaseSchema import DatabaseSchema
from metadata.generated.schema.entity.services.databaseService import DatabaseService, DatabaseServiceType
from metadata.generated.schema.api.data.createTable import CreateTableRequest
from metadata.generated.schema.api.data.createDatabase import CreateDatabaseRequest
from metadata.generated.schema.api.data.createDatabaseSchema import CreateDatabaseSchemaRequest
from metadata.generated.schema.api.services.createDatabaseService import CreateDatabaseServiceRequest
from metadata.generated.schema.type.tagLabel import TagLabel, TagSource, LabelType, State
from metadata.generated.schema.type.entityReference import EntityReference

from metadata.ingestion.ometa.auth_provider import OpenMetadataAuthenticationProvider

from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import OpenMetadataConnection, AuthProvider
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import OpenMetadataJWTClientConfig

class OMClient:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OMClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'metadata'):
            # Prioritize environment variables for Cloud/External config
            self.host_port = os.getenv("OPENMETADATA_HOST", "http://localhost:8585/api")
            self.jwt_token = os.getenv("OPENMETADATA_TOKEN", "eyJhbGciOiJSUzI1NiIsImtpZCI6IkdiMzg5YS05Zjc2LWdkanMtYTkyai0wMjQyYms5NDM1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImluZ2VzdGlvbi1ib3QiLCJyb2xlcyI6WyJJbmdlc3Rpb25Cb3RSb2xlIl0sImVtYWlsIjoiaW5nZXN0aW9uLWJvdEBvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJ1c2VybmFtZSI6ImluZ2VzdGlvbi1ib3QiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJpbmdlc3Rpb24tYm90IiwiaWF0IjoxNzY3MzczMTc1LCJleHAiOm51bGx9.THFNp0ilQU29GCQCaQcExjDzPTnp7nyAtws9d0--aU9jgmBrsM_ffK9N5j0fFHJ8UakrsXShgisjxe4xMm8aQiliMR23k_H5pX3YwRxHvfWELAsg2GMj6DmiWQo_Ov1fnwTVg_CkAft6PzENwzpy2tmkz-19xx5sN5OUwb-Vp3XVzzG2PHktl1Qq3GIN_G8qOdGXv2RIHrMzXtqx2h5_UVRnz-9KgzCGZ5IqVnyjed3dMq8MWQO61JAx7A8pabbmHQ4jr996-aS3GSrtwH_61Og1yr4nKfRcCIYqaVrubDMQ9FvF0VEACDQDoXDLBnNhjhxKiLeANbXMv3dxIzyjhw")
            
            self.config = OpenMetadataConnection(
                hostPort=self.host_port,
                authProvider=AuthProvider.openmetadata,
                securityConfig=OpenMetadataJWTClientConfig(
                    jwtToken=self.jwt_token
                )
            )
            self.metadata = OpenMetadata(self.config)
            self.service_name = "local_files"
            self.db_name = "uploads"
            self.schema_name = "default"

    def ensure_structure(self):
        """Lazy init: Only run once per application life"""
        if OMClient._initialized:
            return
        
        print("DEBUG: Initializing OpenMetadata structure (One-time setup)...")
        try:
            # 1. Create Service
            service_req = CreateDatabaseServiceRequest(
                name=self.service_name,
                serviceType=DatabaseServiceType.CustomDatabase,
                connection={"config": {"type": "CustomDatabase"}}
            )
            self.metadata.create_or_update(service_req)
            
            # 2. Create Database
            db_req = CreateDatabaseRequest(
                name=self.db_name,
                service=self.service_name
            )
            self.metadata.create_or_update(db_req)
            
            # 3. Create Schema
            schema_req = CreateDatabaseSchemaRequest(
                name=self.schema_name,
                database=f"{self.service_name}.{self.db_name}"
            )
            self.metadata.create_or_update(schema_req)
            OMClient._initialized = True
        except Exception as e:
            print(f"Error initializing OM structure: {e}")

    def ingest_dataset_with_all_metadata(self, file_name, columns_with_tags):
        """
        ONE CALL to rule them all. Creates table with all columns and tags at once.
        columns_with_tags: List of {name, datatype, tags: [{tag_fqn, label_type}]}
        """
        self.ensure_structure()
        table_name = file_name.replace(".", "_").replace("-", "_")
        
        om_columns = []
        for col in columns_with_tags:
            dtype = DataType.STRING
            c_type = str(col["datatype"]).lower()
            if "int" in c_type: dtype = DataType.INT
            elif "float" in c_type: dtype = DataType.FLOAT
            elif "bool" in c_type: dtype = DataType.BOOLEAN
            
            tag_labels = []
            for t in col.get("tags", []):
                tag_labels.append(TagLabel(
                    tagFQN=t["tag_fqn"],
                    source=TagSource.Classification,
                    labelType=t["label_type"],
                    state=State.Confirmed
                ))

            om_columns.append(Column(
                name=col["name"],
                dataType=dtype,
                description=f"Imported from {file_name}",
                tags=tag_labels if tag_labels else None
            ))
            
        table_req = CreateTableRequest(
            name=table_name,
            databaseSchema=f"{self.service_name}.{self.db_name}.{self.schema_name}",
            columns=om_columns
        )
        
        return self.metadata.create_or_update(table_req)

    def ingest_dataset_as_table(self, file_name, columns_profile):
        """
        Creates a Table entity in OM.
        columns_profile: List of dicts {name, datatype} from profiler
        """
        table_name = file_name.replace(".", "_").replace("-", "_")
        
        # Map pandas types to OM types (Simplified)
        om_columns = []
        for col in columns_profile:
            dtype = DataType.STRING
            c_type = str(col["datatype"]).lower()
            if "int" in c_type: dtype = DataType.INT
            elif "float" in c_type: dtype = DataType.FLOAT
            elif "bool" in c_type: dtype = DataType.BOOLEAN
            
            om_columns.append(Column(
                name=col["name"],
                dataType=dtype,
                description=f"Imported from {file_name}"
            ))
            
        table_req = CreateTableRequest(
            name=table_name,
            databaseSchema=f"{self.service_name}.{self.db_name}.{self.schema_name}",
            columns=om_columns
        )
        
        table_entity = self.metadata.create_or_update(table_req)
        return table_entity

    def _clean_str(self, val):
        """Helper to clean Pydantic string representations like root='Name' or root=UUID(...)"""
        s = str(val)
        if s.startswith("root="):
            s = s[5:]
        
        if s.startswith("UUID('") and s.endswith("')"):
            return s[6:-2]
            
        if s.startswith("'") and s.endswith("'"):
            return s[1:-1]
            
        return s

    def list_datasets(self):
        """
        Fetches tables from OpenMetadata to serve as 'datasets'
        """
        try:
            # Search for tables in all services to support S3 imports
            tables = self.metadata.list_entities(entity=Table, fields=["columns", "tags"])
            datasets = []
            for t in tables.entities:
                # Handle Pydantic v1 vs v2 / OM version differences
                t_id = getattr(t.id, '__root__', t.id)
                t_name = getattr(t.name, '__root__', t.name)
                t_updated = getattr(t.updatedAt, '__root__', t.updatedAt) if hasattr(t, "updatedAt") else None

                clean_id = self._clean_str(t_id)
                # Known broken dataset that causes 404/500 errors due to missing schema relationship
                if clean_id == "6d2e5fb0-b5b5-4ef8-a5a5-a2d799d17724":
                    continue

                datasets.append({
                    "id": clean_id,
                    "name": self._clean_str(t_name),
                    "created_at": t_updated,
                    "row_count": 0,
                    "columns": []
                })
            return datasets
        except Exception as e:
            print(f"Error listing datasets from OM: {e}")
            return []

    def list_all_tables(self, fields=["columns", "tags", "sampleData"]):
        """
        Fetches ALL tables from ALL services (Postgres, MySQL, etc.)
        """
        try:
            return self.metadata.list_entities(entity=Table, fields=fields).entities
        except Exception as e:
            print(f"Error listing all tables: {e}")
            return []

    def get_dataset(self, table_fqn_or_id):
        """
        Fetches a single table and maps it to our frontend schema
        """
        try:
            table = self.metadata.get_by_name(entity=Table, fqn=table_fqn_or_id, fields=["columns", "tags"])
            if not table:
                # Fallback to get by ID
                table = self.metadata.get_by_id(entity=Table, entity_id=table_fqn_or_id, fields=["columns", "tags"])
            
            if not table: return None

            columns = []
            for col in table.columns:
                col_name = getattr(col.name, '__root__', col.name)
                tags = []
                if col.tags:
                    for t in col.tags:
                        tag_fqn = getattr(t.tagFQN, '__root__', t.tagFQN)
                        tags.append({
                            "tag_fqn": self._clean_str(tag_fqn),
                            "confidence": 1.0, 
                            "source": t.source.value if t.source else "UNKNOWN",
                            "is_auto_applied": t.labelType.value == "Automated" if t.labelType else True,
                            "id": 0, "column_id": 0
                        })
                
                columns.append({
                    "name": self._clean_str(col_name),
                    "datatype": col.dataType.value,
                    "sample_values": "[]", 
                    "id": 0, "dataset_id": 0,
                    "tags": tags
                })

            t_id = getattr(table.id, '__root__', table.id)
            t_name = getattr(table.name, '__root__', table.name)
            t_updated = getattr(table.updatedAt, '__root__', table.updatedAt) if hasattr(table, "updatedAt") else None

            return {
                "id": self._clean_str(t_id),
                "name": self._clean_str(t_name),
                "created_at": t_updated,
                "row_count": 0,
                "columns": columns
            }
        except Exception as e:
            print(f"Error getting dataset from OM: {e}")
            return None

    def apply_column_tags(self, table_fqn, column_name, tags_to_apply):
        """
        tags_to_apply: List of dicts {tag_fqn, label_type}
        """
        try:
            table = self.metadata.get_by_name(entity=Table, fqn=table_fqn, fields=["columns", "tags"])
            if not table:
                table = self.metadata.get_by_id(entity=Table, entity_id=table_fqn, fields=["columns", "tags"])
            
            if not table: return

            updated = False
            for col in table.columns:
                if col.name.__root__ == column_name:
                    if not col.tags: col.tags = []
                    
                    existing_fqns = {t.tagFQN.__root__ for t in col.tags}
                    
                    for tag_info in tags_to_apply:
                        if tag_info["tag_fqn"] not in existing_fqns:
                            col.tags.append(TagLabel(
                                tagFQN=tag_info["tag_fqn"],
                                source=TagSource.Classification,
                                labelType=tag_info["label_type"],
                                state=State.Confirmed
                            ))
                            updated = True
            
            if updated:
                self.metadata.create_or_update(table)
        except Exception as e:
            print(f"Failed to push tags to {column_name}: {e}")
