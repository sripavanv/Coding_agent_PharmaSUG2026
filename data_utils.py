import pandas as pd
import os
from pathlib import Path

# CDISC datasets directory
BASE_DIR = Path("C:/Users/sripa/Desktop/python_test/code_agent")

def load_cdisc_data(dataset_name):
    """Load CDISC dataset for swimmer plots"""
    file_mapping = {
        "ADSL": "ADSL.csv",
        "ADRS": "ADRS_ONCO.csv", 
        "ADTTE": "ADTTE_ONCO.csv",
        "ADTR": "ADTR_ONCO.csv"
    }
    
    if dataset_name not in file_mapping:
        raise ValueError(f"Unknown CDISC dataset: {dataset_name}")
    
    file_path = BASE_DIR / file_mapping[dataset_name]
    print(f"Loading CDISC {dataset_name} from: {file_path}")
    
    try:
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return None
        
        df = pd.read_csv(file_path, encoding='utf-8')
        
        if df.empty:
            print(f"Warning: {dataset_name} file is empty")
            return None
            
        print(f"✅ Loaded {dataset_name}: {len(df)} rows × {len(df.columns)} columns")
        return df
        
        
    except Exception as e:
        print(f"❌ Error loading {dataset_name}: {str(e)}")
        return None


def get_cdisc_datasets():
    """Return available CDISC datasets for swimmer plots"""
    return {
        'ADSL': {
            'description': 'Subject-level data (baseline characteristics)',
            'file': 'ADSL.csv'
        },
        'ADRS': {
            'description': 'Response data (tumor assessments over time)',
            'file': 'ADRS_ONCO.csv'
        },
        'ADTTE': {
            'description': 'Time-to-event data (survival, progression)',
            'file': 'ADTTE_ONCO.csv'
        },
        'ADTR': {
            'description': 'Tumor response data (target lesions)',
            'file': 'ADTR_ONCO.csv'
        }
    }

def check_cdisc_availability():
    """Check which CDISC files are available"""
    datasets = get_cdisc_datasets()
    availability = {}
    
    for dataset_name, info in datasets.items():
        file_path = BASE_DIR / info['file']
        try:
            if file_path.exists():
                # Quick test read
                test_df = pd.read_csv(file_path, nrows=1)
                availability[dataset_name] = not test_df.empty
            else:
                availability[dataset_name] = False
        except:
            availability[dataset_name] = False
            
        status = "✅ Available" if availability[dataset_name] else "❌ Not available"
        print(f"{dataset_name}: {status}")
    
    return availability

# Simplified loader functions
def load_adsl():
    return load_cdisc_data("ADSL")

def load_adrs():
    return load_cdisc_data("ADRS") 

def load_adtte():
    return load_cdisc_data("ADTTE")

def load_adtr():
    return load_cdisc_data("ADTR")