"""
Data Validator Module
Validates variables, data types, and customization separation.
"""

import pandas as pd


class DataValidator:

    # ── Individual checks ──────────────────────────────────────────────────────

    def validate_variables_specified(self, x_var, y_var, hbar_var):
        missing = [label for label, v in [("X-axis (linear)", x_var), ("Y-axis (categorical)", y_var), ("HBAR duration", hbar_var)] if not v]
        return not missing, missing

    def validate_variables_in_data(self, sample_data, x_var, y_var, hbar_var):
        if sample_data is None or sample_data.empty:
            return False, ["No data"]
        missing = [f"{name} ('{v}')" for name, v in {"X-axis": x_var, "Y-axis": y_var, "HBAR": hbar_var}.items()
                   if v not in sample_data.columns]
        return not missing, missing

    def validate_x_axis_numeric(self, sample_data, x_var):
        col = sample_data[x_var]
        if pd.api.types.is_datetime64_any_dtype(col):
            return True, "datetime"
        if pd.api.types.is_numeric_dtype(col):
            return True, "numeric"
        sample = col.dropna().iloc[:5]
        try:
            pd.to_datetime(sample, errors='raise')
            return True, "date_string"
        except (ValueError, TypeError):
            pass
        try:
            pd.to_numeric(sample, errors='raise')
            return True, "numeric_string"
        except (ValueError, TypeError):
            return False, "non_linear"

    def validate_hbar_numeric(self, sample_data, hbar_var):
        col = sample_data[hbar_var]
        if pd.api.types.is_datetime64_any_dtype(col):
            return True, "datetime"
        try:
            pd.to_numeric(col, errors='raise')
            return True, "numeric"
        except (ValueError, TypeError):
            return False, "non_numeric"

    def validate_graph_customization(self, graph_customization):
        """Reject graph customization requests that contain data-level instructions."""
        if not graph_customization or not graph_customization.strip():
            return {"valid": True, "issues": []}
        data_terms = [
            'filter subjects', 'exclude subjects', 'remove subjects',
            'calculate new', 'derive new', 'create new column',
            'group by treatment', 'subset by', 'select only',
        ]
        issues = [t for t in data_terms if t in graph_customization.lower()]
        return {"valid": not issues, "issues": issues}

    # ── Combined validation ────────────────────────────────────────────────────

    def validate_all(self, sample_data, x_var, y_var, hbar_var, data_customization=None, graph_customization=None):
        errors, warnings = [], []

        # Variables specified?
        ok, missing = self.validate_variables_specified(x_var, y_var, hbar_var)
        if not ok:
            return {"valid": False, "errors": [f"Missing required variables: {', '.join(missing)}"], "warnings": []}

        # Variables exist in data?
        ok, missing = self.validate_variables_in_data(sample_data, x_var, y_var, hbar_var)
        if not ok:
            return {"valid": False, "errors": [f"Variables not found in dataset: {', '.join(missing)}"], "warnings": []}

        # X-axis numeric/linear?
        ok, x_type = self.validate_x_axis_numeric(sample_data, x_var)
        if not ok:
            errors.append(f"X-axis '{x_var}' must be numeric or date (linear values).")
        elif x_type in ("date_string", "numeric_string"):
            warnings.append(f"X-axis '{x_var}' will be converted ({x_type}).")

        # HBAR numeric?
        ok, hbar_type = self.validate_hbar_numeric(sample_data, hbar_var)
        if not ok:
            errors.append(f"HBAR '{hbar_var}' must be numeric for duration calculation.")
        elif hbar_type == "datetime":
            warnings.append(f"HBAR '{hbar_var}' is datetime — will convert to days.")

        # Customization cross-contamination checks
        if data_customization:
            from data_customizer import DataCustomizer
            r = DataCustomizer().validate_data_customization(data_customization)
            if not r["valid"]:
                errors.append(f"Data customization contains graph elements: {r['issues']}")

        if graph_customization:
            r = self.validate_graph_customization(graph_customization)
            if not r["valid"]:
                errors.append(f"Graph customization contains data elements: {r['issues']}")

        return {"valid": not errors, "errors": errors, "warnings": warnings}
