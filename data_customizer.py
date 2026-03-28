"""
Data Customizer Module
Handles dataset-level customizations including:
- Deriving new variables based on user specifications
- Merging with ADSL via left join by SUBJID
- Filtering and transformations
"""

import pandas as pd
import numpy as np
import io
import sys


class DataCustomizer:
    def __init__(self, claude_client=None, ai_enabled=False):
        """Initialize data customizer with AI client"""
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled

        # Derivation context tracking
        self.derivation_context = {
            'derivation_code': '',
            'derived_variables': [],
            'user_request': '',
            'formulas': {},
            'original_shape': None,
            'processed_shape': None
        }

    def validate_data_customization(self, data_customization):
        """Validate that data customization doesn't contain graph elements - LENIENT VERSION"""
        if not data_customization or not data_customization.strip():
            return {"valid": True, "issues": []}

        # Graph-related terms that shouldn't be in data customization - REDUCED LIST
        graph_terms = [
            'plotly title', 'chart title', 'plot title', 'figure title',
            'axis label font', 'legend font', 'text font',
            'plot background', 'chart background', 'figure background',
            'plot layout', 'chart layout', 'figure layout',
            'hover tooltip', 'plot annotation'
        ]

        text_lower = data_customization.lower()
        found_issues = []

        for term in graph_terms:
            if term in text_lower:
                found_issues.append(term)

        return {
            "valid": len(found_issues) == 0,
            "issues": found_issues
        }

    def apply_data_customizations(self, sample_data, data_customization, x_var, y_var, hbar_var):
        """Apply data customizations using AI to transform the dataset - ENHANCED with DERIVATION TRACKING"""

        print(f"=== DATA CUSTOMIZATION DEBUG ===")
        print(f"AI Enabled: {self.ai_enabled}")
        print(f"Data customization provided: {bool(data_customization and data_customization.strip())}")
        print(f"Data customization content: '{data_customization[:100]}...' " if data_customization else "None")

        # Store original shape for context
        self.derivation_context['original_shape'] = sample_data.shape
        self.derivation_context['user_request'] = data_customization

        if not data_customization or not data_customization.strip():
            print("⚠ No data customization provided - returning original data")
            self.derivation_context['processed_shape'] = sample_data.shape
            return sample_data

        if not self.ai_enabled:
            print("⚠ AI not enabled - returning original data")
            return sample_data

        # Enhanced validation debugging
        data_validation = self.validate_data_customization(data_customization)
        print(f"Data validation result: {data_validation}")

        if not data_validation["valid"]:
            print(f"⚠ Data validation failed: {data_validation['issues']}")
            return sample_data

        data_info = {
            'columns': list(sample_data.columns),
            'shape': sample_data.shape,
            'sample_values': {col: list(sample_data[col].dropna().unique()[:3]) for col in sample_data.columns[:8]}
        }

        print(f"Dataset info: {data_info['shape']} with columns: {data_info['columns'][:5]}...")

        data_prompt = f"""Apply data customizations to a CDISC clinical trial dataset.

SECTION 1: DATASET CONTEXT
- Columns: {data_info['columns']}
- Shape: {data_info['shape']}
- Sample values: {data_info['sample_values']}

KEY VARIABLES TO PRESERVE:
- Y-axis (subjects): {y_var}
- X-axis (time): {x_var}
- HBAR (duration): {hbar_var}

SECTION 2: USER'S CUSTOMIZATION REQUEST
{data_customization}

SECTION 3: DATA PREPARATION WORKFLOW
Follow this strict workflow:

1. VARIABLE EXISTENCE CHECK:
   - User may request: "derive abc using (B - A) + 1"
   - BEFORE deriving: Check if B and A exist in recist_data columns
   - If missing: STOP and print error message listing missing variables
   - If exists: Proceed with derivation

2. COLLECT ALL VARIABLES FIRST:
   - Identify ALL variables mentioned in user's request
   - Create a list of required variables
   - This includes: {y_var}, {x_var}, {hbar_var}, and any overlay variables

3. VARIABLE LOCATION AND MERGE:
   - ADRS is the MAIN DRIVER dataset (recist_data is ADRS)
   - Check which variables exist in recist_data
   - For variables NOT in recist_data, check if they exist in ADSL
   - If variable not in ADRS or ADSL: STOP and report missing variable
   - Merge strategy: LEFT JOIN from ADSL using {y_var} as join key
   - Only bring needed variables from ADSL (not all columns)

4. KEEP ONLY REQUIRED VARIABLES:
   - After merge and derivation, keep ONLY:
     * {y_var} (Y-axis subject variable)
     * {x_var} (X-axis time variable)
     * {hbar_var} (HBAR duration variable)
     * Any overlay variables mentioned by user
     * Any derived variables created
   - Drop ALL other columns
   - Use: processed_data = processed_data[[list_of_kept_variables]]

5. DERIVE NEW VARIABLES (if requested):
   - Execute derivation formulas
   - Add print statements documenting each derivation
   - Print format: "DERIVED: var_name = formula_description"

6. VALIDATE FINAL DATASET:
   - Confirm all required variables present
   - Ensure {y_var}, {x_var}, {hbar_var} still exist

SECTION 4: CODE GENERATION REQUIREMENTS
1. DataFrame name: recist_data (input) → processed_data (output)
2. Apply ONLY data transformations (no visualization)
3. Preserve required columns: {y_var}, {x_var}, {hbar_var}
4. Use pandas operations: merge(), groupby(), fillna(), dropna(), etc.
5. Handle datetime with .dt.days for date differences
6. Add print statements for derived variables: "DERIVED: var = formula"
7. Add comments explaining each step
8. BEFORE final line, display dataset:
   - print("\\n=== FINAL DATASET AFTER CUSTOMIZATION ===")
   - print(f"Shape: {{processed_data.shape}}")
   - print(f"Columns: {{list(processed_data.columns)}}")
   - print("\\nFirst 10 rows:")
   - print(processed_data.head(10))
9. Final line MUST be: processed_data = [your_final_dataframe]

CRITICAL RULES:
- Always check variable existence before using
- ADRS is base, LEFT JOIN from ADSL
- Join key is always {y_var} (subject identifier)
- Keep only mentioned variables, drop everything else
- For date differences: use .dt.days and add 1 for Day 1 = reference date

Generate clean Python code implementing the user's request:"""

        try:
            print("Sending request to Claude AI...")
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                temperature=0.1,
                messages=[{"role": "user", "content": data_prompt}]
            )

            data_transform_code = self._clean_code(message.content[0].text.strip())
            print(f"AI generated {len(data_transform_code)} characters of code")
            print(f"Generated code preview:\n{data_transform_code[:200]}...")

            # STORE derivation code for later handover
            self.derivation_context['derivation_code'] = data_transform_code

            # Execute data transformation with enhanced debugging
            exec_globals = {
                'pd': pd, 'np': np,
                'recist_data': sample_data.copy(),
                'print': print,  # Enable print statements in executed code
            }

            print("Executing data transformation code...")

            # Capture print output to extract derived variable info
            captured_output = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured_output

            try:
                exec(data_transform_code, exec_globals)
            finally:
                sys.stdout = old_stdout

            # Parse captured output for derived variables
            output_lines = captured_output.getvalue().split('\n')
            for line in output_lines:
                if line.startswith('DERIVED:'):
                    parts = line.replace('DERIVED:', '').strip().split('=', 1)
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        formula = parts[1].strip()
                        self.derivation_context['derived_variables'].append(var_name)
                        self.derivation_context['formulas'][var_name] = formula
                        print(f"Captured derived variable: {var_name} = {formula}")
                else:
                    print(line)  # Print non-DERIVED lines normally

            print(f"Available variables after execution: {list(exec_globals.keys())}")

            if 'processed_data' in exec_globals:
                processed = exec_globals['processed_data']
                print(f"Data customization applied successfully!")
                print(f"Original data: {len(sample_data)} rows × {len(sample_data.columns)} columns")
                print(f"Processed data: {len(processed)} rows × {len(processed.columns)} columns")

                # Store processed shape
                self.derivation_context['processed_shape'] = processed.shape

                # Verify required columns still exist
                missing_cols = []
                for col in [y_var, x_var, hbar_var]:
                    if col not in processed.columns:
                        missing_cols.append(col)

                if missing_cols:
                    print(f"Warning: Required columns missing after processing: {missing_cols}")
                    print("Returning original data to prevent errors")
                    return sample_data

                return processed
            else:
                print("⚠ No 'processed_data' variable found in executed code")
                print("Generated code did not create the required 'processed_data' variable")
                return sample_data

        except Exception as e:
            error_msg = str(e)
            print(f"⚠ Data customization execution failed: {error_msg}")
            print(f"Full error: {repr(e)}")

            # Enhanced debugging attempt
            try:
                print("Attempting to fix data customization with AI...")
                fixed_code = self._debug_data_customization(data_transform_code, error_msg, sample_data, data_customization, x_var, y_var, hbar_var)
                print(f"AI debugging generated {len(fixed_code)} characters of fixed code")

                # Try executing the fixed code
                exec_globals = {
                    'pd': pd, 'np': np,
                    'recist_data': sample_data.copy(),
                    'print': print,
                }

                print("Executing fixed code...")
                exec(fixed_code, exec_globals)

                if 'processed_data' in exec_globals:
                    processed = exec_globals['processed_data']
                    print(f"Fixed data customization applied: {len(sample_data)} → {len(processed)} rows")
                    return processed
                else:
                    print("⚠ Fixed code also didn't produce 'processed_data', using original data")
                    return sample_data

            except Exception as debug_error:
                print(f"⚠ Data customization debug also failed: {debug_error}")
                print("Returning original data")
                return sample_data

    def _debug_data_customization(self, failed_code, error_message, sample_data, data_customization, x_var, y_var, hbar_var):
        """Debug failed data customization code"""

        data_info = {
            'columns': list(sample_data.columns),
            'shape': sample_data.shape,  ##store dimension using shape function
            'sample_values': {col: list(sample_data[col].dropna().unique()[:3]) for col in sample_data.columns[:8]}
        }

        debug_prompt = f"""Fix this failed data customization code for CDISC clinical trial data:

FAILED DATA TRANSFORMATION CODE:
```python
{failed_code}
```

ERROR MESSAGE:
{error_message}

ORIGINAL USER REQUEST:
{data_customization}

DATASET CONTEXT:
- Columns: {data_info['columns']}
- Shape: {data_info['shape']}
- Sample values: {data_info['sample_values']}
- Key variables: Y={y_var}, X={x_var}, HBAR={hbar_var}

COMMON FIXES FOR DATETIME/TIMEDELTA ERRORS:
- Use .dt.days instead of integer arithmetic on timedelta
- Use pd.to_timedelta() for time-based operations
- Convert datetime to numeric: (date_col - date_col.min()).dt.days
- Use .dt.total_seconds() / (24*3600) for days conversion

REQUIREMENTS:
1. Fix the specific error mentioned above
2. DataFrame name: recist_data (input) → processed_data (output)
3. Apply only data transformations, no visualization
4. Preserve required columns: {y_var}, {x_var}, {hbar_var}
5. Handle datetime columns properly

Generate ONLY the corrected Python code:"""

        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                temperature=0.1,
                messages=[{"role": "user", "content": debug_prompt}]
            )

            return self._clean_code(message.content[0].text.strip())

        except Exception as e:
            print(f"AI data customization debug failed: {e}")
            # Return a simple passthrough if debugging fails
            return "processed_data = recist_data.copy()"

    def get_validation_report(self, x_var, y_var, hbar_var, processed_data):
        """Generate validation report for user approval"""
        report = {
            'original_shape': self.derivation_context.get('original_shape', 'N/A'),
            'processed_shape': self.derivation_context.get('processed_shape', processed_data.shape),
            'user_request': self.derivation_context.get('user_request', 'No customization'),
            'derivation_code': self.derivation_context.get('derivation_code', ''),
            'derived_variables': self.derivation_context.get('derived_variables', []),
            'formulas': self.derivation_context.get('formulas', {}),
            'data_snapshot': {
                'first_5': processed_data.head(5).to_dict() if processed_data is not None else {},
                'columns': list(processed_data.columns) if processed_data is not None else [],
                'dtypes': {col: str(dtype) for col, dtype in processed_data.dtypes.items()} if processed_data is not None else {}
            },
            'variables_for_plot': {
                'y_axis': y_var,
                'x_axis': x_var,
                'hbar': hbar_var
            }
        }
        return report

    def filter_data_to_plot_variables(self, data, required_vars, additional_vars=None):
        """Filter dataset to keep only variables needed for plotting"""
        if data is None:
            return None

        # Collect all variables to keep
        vars_to_keep = set(required_vars)

        if additional_vars:
            if isinstance(additional_vars, str):
                vars_to_keep.add(additional_vars)
            elif isinstance(additional_vars, (list, tuple)):
                vars_to_keep.update(additional_vars)

        # Filter to only existing columns
        available_cols = set(data.columns)
        cols_to_keep = list(vars_to_keep.intersection(available_cols))

        if not cols_to_keep:
            print("Warning: No matching columns found for filtering")
            return data

        filtered_data = data[cols_to_keep].copy()
        print(f"Filtered data from {len(data.columns)} to {len(filtered_data.columns)} columns")
        print(f"Kept columns: {cols_to_keep}")

        return filtered_data

    def _clean_code(self, generated_code):
        """Simple code cleaning"""
        # Remove markdown code blocks
        if '```python' in generated_code:
            start = generated_code.find('```python') + 9
            end = generated_code.find('```', start)
            if end > start:
                return generated_code[start:end].strip()
        elif '```' in generated_code:
            start = generated_code.find('```') + 3
            end = generated_code.find('```', start)
            if end > start:
                return generated_code[start:end].strip()

        return generated_code.strip()
