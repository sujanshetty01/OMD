import pandas as pd
import json
import yaml
import pdfplumber

def profile_dataset(file_path: str):
    """
    Reads a file and returns profile info:
    - row_count
    - columns: [{name, type, samples, null_count}]
    """
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.json'):
        df = pd.read_json(file_path)
    elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path)
    elif file_path.endswith('.parquet'):
        df = pd.read_parquet(file_path)
    elif file_path.endswith('.xml'):
        df = pd.read_xml(file_path)
    elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        # Attempt to normalize. If list of dicts -> simple. If dict -> maybe normalize.
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try to find the "main" list
            found_list = False
            for k, v in data.items():
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    df = pd.DataFrame(v)
                    found_list = True
                    break
            if not found_list:
                df = pd.json_normalize(data)
    elif file_path.endswith('.pdf'):
         with pdfplumber.open(file_path) as pdf:
             # Heuristic: Extract first found table
             tables = []
             for page in pdf.pages:
                 extracted = page.extract_table()
                 if extracted:
                     tables.append(pd.DataFrame(extracted[1:], columns=extracted[0]))
                     
             if not tables:
                 raise ValueError("No tables found in PDF")
             
             # Concatenate all tables with same schema? Or just take first.
             # For MVP, assume one main table or take first.
             df = tables[0]
    else:
        raise ValueError("Unsupported file type")
    
    full_df = df # Consistent naming with previous valid logic
    
    row_count = len(full_df)
    
    columns_profile = []
    # ... rest of the function (omitted for brevity in replace_file_content but I will return both)
    # Actually I need the full function to ensure I don't break the profile dictionary
    for col in full_df.columns:
        series = full_df[col]
        datatype = str(series.dtype)
        sample_list = series.dropna().head(5).tolist()
        str_samples = [str(s) for s in sample_list]
        
        columns_profile.append({
            "name": col,
            "datatype": datatype,
            "sample_values": json.dumps(str_samples),
            "series": series
        })
    
    return {
        "row_count": row_count,
        "columns": columns_profile
    }, full_df
