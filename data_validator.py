"""
Data Validator Module
Handles validation of:
- Variables specified by user (X, Y, HBAR)
- Variable existence in data (ADRS or after merge with ADSL)
- Data types: X is numeric, Y is categorical, HBAR is numeric
- Merge conditions (SUBJID-based left joins)
"""

import pandas as pd


class DataValidator:
    def __init__(self):
        """Initialize data validator"""
        pass

    def validate_variables_specified(self, x_var, y_var, hbar_var):
        """Check if variables are specified by user"""
        missing = []
        if not x_var:
            missing.append("X-axis (linear)")
        if not y_var:
            missing.append("Y-axis (categorical)")
        if not hbar_var:
            missing.append("HBAR duration")

        if missing:
            print(f"⚠ Missing required variables: {missing}")
            return False, missing

        print("✓ All required variables specified")
        return True, []

    def validate_variables_in_data(self, sample_data, x_var, y_var, hbar_var):
        """Check if the variable mentioned are in data"""
        if sample_data is None or sample_data.empty:
            print("⚠ No data available")
            return False, ["No data"]

        available_cols = list(sample_data.columns)

        # Define the variables to check with descriptive names
        variables_to_check = {
            "X-axis": x_var,
            "Y-axis": y_var,
            "HBAR": hbar_var
        }

        # Check each variable
        for var_name, var_value in variables_to_check.items():
            if var_value not in available_cols:
                print(f"⚠ {var_name} variable '{var_value}' not found in dataset")
                return False, [f"Invalid {var_name}"]

        print("✓ All required variables found in dataset")
        return True, []

    def validate_x_axis_numeric(self, sample_data, x_var):
        """X-axis must be linear (numeric or date) - CHECK ONLY, DON'T CONVERT"""
        try:
            if pd.api.types.is_datetime64_any_dtype(sample_data[x_var]):
                print(f"✓ X-axis '{x_var}' is datetime")
                return True, "datetime"
            elif pd.api.types.is_numeric_dtype(sample_data[x_var]):
                print(f"✓ X-axis '{x_var}' is numeric")
                return True, "numeric"
            else:
                # Check if it's date strings (like "2014-01-01") or numeric strings
                test_sample = sample_data[x_var].dropna().iloc[:5]  # Test first 5 non-null values

                # Try to parse as dates first
                try:
                    pd.to_datetime(test_sample, errors='raise')
                    print(f"✓ X-axis '{x_var}' contains date strings (e.g., '2014-01-01')")
                    return True, "date_string"
                except (ValueError, TypeError):
                    # If not dates, try numeric
                    try:
                        pd.to_numeric(test_sample, errors='raise')
                        print(f"✓ X-axis '{x_var}' appears to be convertible to numeric")
                        return True, "numeric_string"
                    except (ValueError, TypeError):
                        print(f"⚠ X-axis variable '{x_var}' is not numeric or date")
                        return False, "non_linear"

        except (ValueError, TypeError, KeyError):
            print(f"⚠ Error checking X-axis variable '{x_var}'")
            return False, "error"

    def validate_hbar_numeric(self, sample_data, hbar_var):
        """HBAR must be numeric for duration calculation"""
        try:
            if pd.api.types.is_datetime64_any_dtype(sample_data[hbar_var]):
                print(f"⚠ HBAR '{hbar_var}' is datetime - will convert to numeric days")
                return True, "datetime"
            else:
                pd.to_numeric(sample_data[hbar_var], errors='raise')
                print(f"✓ HBAR '{hbar_var}' is numeric")
                return True, "numeric"
        except (ValueError, TypeError):
            print(f"⚠ HBAR variable '{hbar_var}' is not numeric")
            return False, "non_numeric"

    def validate_graph_customization(self, graph_customization):
        """Validate that graph customization doesn't contain data elements - LENIENT VERSION"""
        if not graph_customization or not graph_customization.strip():
            return {"valid": True, "issues": []}

        # Data-related terms that shouldn't be in graph customization - REDUCED LIST
        data_terms = [
            'filter subjects', 'exclude subjects', 'remove subjects',
            'calculate new', 'derive new', 'create new column',
            'group by treatment', 'subset by', 'select only'
        ]

        text_lower = graph_customization.lower()
        found_issues = []

        for term in data_terms:
            if term in text_lower:
                found_issues.append(term)

        return {
            "valid": len(found_issues) == 0,
            "issues": found_issues
        }

    def validate_all(self, sample_data, x_var, y_var, hbar_var, data_customization=None, graph_customization=None):
        """Run all validations and return comprehensive result"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # 1. Check if variables are specified
        vars_specified, missing = self.validate_variables_specified(x_var, y_var, hbar_var)
        if not vars_specified:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Missing required variables: {', '.join(missing)}")
            return validation_result  # Early exit if variables not specified

        # 2. Check if variables exist in data
        vars_in_data, issues = self.validate_variables_in_data(sample_data, x_var, y_var, hbar_var)
        if not vars_in_data:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Variables not found in dataset: {', '.join(issues)}")
            return validation_result  # Early exit if variables don't exist

        # 3. Validate X-axis is numeric/linear
        x_valid, x_type = self.validate_x_axis_numeric(sample_data, x_var)
        if not x_valid:
            validation_result["valid"] = False
            validation_result["errors"].append(f"X-axis variable '{x_var}' must be numeric or date (linear values)")
        elif x_type in ["date_string", "numeric_string"]:
            validation_result["warnings"].append(f"X-axis '{x_var}' will be converted to {x_type}")

        # 4. Validate HBAR is numeric
        hbar_valid, hbar_type = self.validate_hbar_numeric(sample_data, hbar_var)
        if not hbar_valid:
            validation_result["valid"] = False
            validation_result["errors"].append(f"HBAR variable '{hbar_var}' must be numeric for duration calculation")
        elif hbar_type == "datetime":
            validation_result["warnings"].append(f"HBAR '{hbar_var}' is datetime - will convert to numeric days")

        # 5. Validate customization separation (if provided)
        if data_customization:
            from data_customizer import DataCustomizer
            customizer = DataCustomizer()
            data_val = customizer.validate_data_customization(data_customization)
            if not data_val["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Data customization contains graph elements: {data_val['issues']}")

        if graph_customization:
            graph_val = self.validate_graph_customization(graph_customization)
            if not graph_val["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Graph customization contains data elements: {graph_val['issues']}")

        return validation_result
