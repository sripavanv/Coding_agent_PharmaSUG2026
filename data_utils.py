"""
Data Utils — CDISC dataset loader.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path("C:/Users/sripa/Desktop/python_test/code_agent")

_FILE_MAP = {
    "ADSL":  "ADSL.csv",
    "ADRS":  "ADRS_ONCO.csv",
    "ADTTE": "ADTTE_ONCO.csv",
    "ADTR":  "ADTR_ONCO.csv",
}


def load_cdisc_data(dataset_name: str) -> pd.DataFrame | None:
    """Load a named CDISC dataset; returns None on failure."""
    filename = _FILE_MAP.get(dataset_name)
    if not filename:
        raise ValueError(f"Unknown dataset '{dataset_name}'. Available: {list(_FILE_MAP)}")

    path = BASE_DIR / filename
    if not path.exists():
        print(f"❌ File not found: {path}")
        return None

    try:
        df = pd.read_csv(path, encoding='utf-8')
        if df.empty:
            print(f"⚠ {dataset_name} is empty.")
            return None
        print(f"✅ {dataset_name}: {df.shape[0]} rows × {df.shape[1]} columns")
        return df
    except Exception as e:
        print(f"❌ Error loading {dataset_name}: {e}")
        return None


def get_cdisc_datasets() -> dict:
    return {
        'ADSL':  {'description': 'Subject-level data (baseline characteristics)', 'file': 'ADSL.csv'},
        'ADRS':  {'description': 'Response data (tumor assessments over time)',    'file': 'ADRS_ONCO.csv'},
        'ADTTE': {'description': 'Time-to-event data (survival, progression)',     'file': 'ADTTE_ONCO.csv'},
        'ADTR':  {'description': 'Tumor response data (target lesions)',           'file': 'ADTR_ONCO.csv'},
    }



# Convenience loaders
def load_adsl():  return load_cdisc_data("ADSL")
def load_adrs():  return load_cdisc_data("ADRS")
def load_adtte(): return load_cdisc_data("ADTTE")
def load_adtr():  return load_cdisc_data("ADTR")
