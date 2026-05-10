"""
Data Customizer Module
Handles all dataset-level customizations:
- LEFT JOIN ADSL onto ADRS for subject-level variables
- Deriving new variables
- Filtering and transformations
Returns the FULL enriched dataset — column selection and dedup happen
downstream in dash_app.generate_validation_report.
"""

import io
import sys
import pandas as pd
import numpy as np

MODEL = "claude-sonnet-4-6"


class DataCustomizer:
    def __init__(self, claude_client=None, ai_enabled=False):
        self.claude_client = claude_client
        self.ai_enabled    = ai_enabled
        self.derivation_context = {
            'derivation_code':   '',
            'derived_variables': [],
            'user_request':      '',
            'formulas':          {},
            'original_shape':    None,
            'processed_shape':   None,
        }

    # ── Validation ─────────────────────────────────────────────────────────────

    def validate_data_customization(self, data_customization):
        """Validate that data customization doesn't contain graph elements - LENIENT VERSION"""
        if not data_customization or not data_customization.strip():
            return {"valid": True, "issues": []}
        graph_terms = [
            'plotly title', 'chart title', 'plot title', 'figure title',
            'axis label font', 'legend font', 'text font',
            'plot background', 'chart background', 'figure background',
            'plot layout', 'chart layout', 'figure layout',
            'hover tooltip', 'plot annotation',
        ]
        issues = [t for t in graph_terms if t in data_customization.lower()]
        return {"valid": not issues, "issues": issues}

    # ── Main entry point ───────────────────────────────────────────────────────

    def apply_data_customizations(self, sample_data, data_customization,
                                   x_var, y_var, hbar_var,
                                   adsl_data=None):
        """Apply data customizations using AI — returns FULL enriched dataset.

        Column selection and drop_duplicates are NOT done here.
        They happen in generate_validation_report after the user picks columns.

        Parameters
        ----------
        sample_data        : ADRS DataFrame (base dataset, many rows per subject)
        data_customization : natural language instructions from the user
        x_var, y_var, hbar_var : plot variable selections (used in prompt context)
        adsl_data          : ADSL DataFrame for left-join merging (optional)
        """
        self.derivation_context['original_shape'] = sample_data.shape
        self.derivation_context['user_request']   = data_customization

        if not data_customization or not data_customization.strip():
            self.derivation_context['processed_shape'] = sample_data.shape
            return sample_data

        if not self.ai_enabled:
            return sample_data

        data_validation = self.validate_data_customization(data_customization)
        if not data_validation["valid"]:
            print(f"⚠ Data validation failed: {data_validation['issues']}")
            return sample_data

        # ── Dataset context for the prompt ─────────────────────────────────────
        adrs_cols = list(sample_data.columns)
        adsl_cols = list(adsl_data.columns) if adsl_data is not None else []

        data_info = {
            'adrs_columns':  adrs_cols,
            'adrs_shape':    sample_data.shape,
            'adsl_columns':  adsl_cols,
            'adsl_shape':    adsl_data.shape if adsl_data is not None else (0, 0),
            'sample_values': {col: list(sample_data[col].dropna().unique()[:3])
                              for col in sample_data.columns[:8]},
        }

        # Join key is always USUBJID (standard CDISC subject identifier)
        join_key = 'USUBJID'

        # ── Starter skeleton ───────────────────────────────────────────────────
        # Always LEFT JOINs ADSL onto ADRS by USUBJID.
        # Brings ALL ADSL columns so the AI can use any of them.
        # Column selection and dedup happen downstream in generate_validation_report.
        starter_code = (
            f"# ── STARTER SKELETON (modify Step 3 only) ──────────────────────\n"
            f"# Step 1: LEFT JOIN ADSL onto full ADRS by USUBJID\n"
            f"# Deduplicate ADSL to one row per USUBJID before merging\n"
            f"adsl_deduped = adsl_data.drop_duplicates(subset=['USUBJID'])\n"
            f"working = recist_data.merge(adsl_deduped, on='USUBJID', how='left')\n\n"
            f"# Step 2: apply user customizations here\n"
            f"# Derive new variables, filter rows, calculate dates, etc.\n"
            f"# ALL columns (ADRS + ADSL + derived) are kept — user selects in Step 2 of the UI.\n\n"
            f"# Step 3: output — this line MUST remain exactly as-is\n"
            f"processed_data = working\n"
        )

        # ── PROMPT ─────────────────────────────────────────────────────────────
        data_prompt = f"""Apply data customizations to a CDISC clinical trial dataset.

SECTION 1: DATASET CONTEXT
ADRS (recist_data) — base dataset, many rows per subject:
- Shape: {data_info['adrs_shape']}
- Columns: {data_info['adrs_columns']}
- Sample values: {data_info['sample_values']}

ADSL (adsl_data) — subject-level, ONE row per subject:
- Shape: {data_info['adsl_shape']}
- Columns: {data_info['adsl_columns']}

KEY VARIABLES FOR CONTEXT:
- Join key (ADSL ← ADRS): USUBJID (always)
- Y-axis (subjects): {y_var if y_var else 'not yet selected'}
- X-axis (time): {x_var if x_var else 'not yet selected'}
- HBAR (duration): {hbar_var if hbar_var else 'not yet selected'}

SECTION 2: USER'S CUSTOMIZATION REQUEST
{data_customization}

SECTION 3: DATA PREPARATION WORKFLOW
Follow this strict workflow:

1. VARIABLE EXISTENCE CHECK:
   - BEFORE using any variable, check it exists in recist_data columns
   - If missing: STOP and print error listing missing variables

2. COLLECT ALL VARIABLES FIRST:
   - Identify ALL variables mentioned in user's request
   - This includes any variables mentioned in the user request and any overlay/derived variables

3. VARIABLE LOCATION AND MERGE:
   - ADRS is the MAIN DRIVER dataset (recist_data is ADRS)
   - For variables NOT in recist_data, check if they exist in ADSL (adsl_data)
   - If variable not in ADRS or ADSL: STOP and report missing variable
   - Merge strategy: LEFT JOIN adsl_data onto recist_data on USUBJID (always)
   - Deduplicate ADSL to ONE row per USUBJID BEFORE merging
   - Select ONLY the needed ADSL columns before merging (never merge all columns)
   - Row count after merge MUST equal recist_data row count

4. DERIVE NEW VARIABLES (if requested):
   - Execute derivation formulas on the working DataFrame
   - Print: "DERIVED: var_name = formula_description" for each new variable

5. OUTPUT:
   - Return ALL columns (original ADRS + any merged ADSL cols + all derived cols)
   - Do NOT drop any columns — the user will select columns in the UI after this step
   - Final line MUST be: processed_data = working

6. VALIDATE:
   - Print final shape and first 10 rows

SECTION 4: CODE GENERATION REQUIREMENTS
1. DataFrame names: recist_data (ADRS input), adsl_data (ADSL input) → processed_data (output)
2. Data transformations ONLY — no visualization, no column dropping
3. Use pandas: merge(), groupby(), fillna(), dropna(), etc.
4. Handle datetime with .dt.days for date differences
5. Print "DERIVED: var = formula" for each derived variable
6. Add comments explaining each step
7. BEFORE final line:
   print("\\n=== FINAL DATASET AFTER CUSTOMIZATION ===")
   print(f"Shape: {{processed_data.shape}}")
   print(f"Columns: {{list(processed_data.columns)}}")
   print(processed_data.head(10))
8. Final line MUST be: processed_data = working

STARTER CODE — your output MUST follow this structure:
```python
{starter_code}
```

CRITICAL RULES:
- ADRS is base, LEFT JOIN from ADSL (never reverse)
- Join key is always {y_var}
- Deduplicate ADSL to one row per {y_var} before merging
- Select only needed ADSL columns — never merge all ADSL columns
- Row count must NOT increase after merge
- Keep ALL columns in output — do NOT drop anything
- For date differences: use .dt.days; add 1 when Day 1 = reference date

Generate clean Python code:"""

        try:
            message = self.claude_client.messages.create(
                model=MODEL, max_tokens=3000, temperature=0.1,
                messages=[{"role": "user", "content": data_prompt}],
            )
            data_transform_code = self._clean_code(message.content[0].text.strip())
            self.derivation_context['derivation_code'] = data_transform_code

            return self._execute_and_capture(
                data_transform_code, sample_data, adsl_data,
                x_var, y_var, hbar_var, data_customization
            )

        except Exception as e:
            print(f"⚠ Data customization failed: {e}")
            return sample_data

    # ── Execution ──────────────────────────────────────────────────────────────

    def _execute_and_capture(self, code, sample_data, adsl_data,
                              x_var, y_var, hbar_var, original_request):
        """Execute transformation code, capture DERIVED: output, retry once on failure."""
        exec_globals = {
            'pd': pd, 'np': np,
            'recist_data': sample_data.copy(),
            'adsl_data':   adsl_data.copy() if adsl_data is not None else pd.DataFrame(),
            'print': print,
        }

        captured   = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            exec(code, exec_globals)
        except Exception as err:
            sys.stdout = old_stdout
            print(f"⚠ Execution failed: {err} — attempting AI fix...")
            return self._retry_with_debug(
                code, str(err), sample_data, adsl_data,
                original_request, x_var, y_var, hbar_var
            )
        finally:
            sys.stdout = old_stdout

        # Parse DERIVED: lines from captured stdout
        for line in captured.getvalue().splitlines():
            if line.startswith('DERIVED:'):
                parts = line.replace('DERIVED:', '').strip().split('=', 1)
                if len(parts) == 2:
                    var_name, formula = parts[0].strip(), parts[1].strip()
                    self.derivation_context['derived_variables'].append(var_name)
                    self.derivation_context['formulas'][var_name] = formula

        processed = exec_globals.get('processed_data')
        if processed is None:
            print("⚠ Code did not produce 'processed_data' — using original.")
            return sample_data

        # Only validate columns that were actually specified (empty strings are skipped)
        required = [c for c in [y_var, x_var, hbar_var] if c]
        missing = [c for c in required if c not in processed.columns]
        if missing:
            print(f"⚠ Required columns missing after processing: {missing} — using original.")
            return sample_data

        self.derivation_context['processed_shape'] = processed.shape
        print(f"✅ Data customization applied: {sample_data.shape} → {processed.shape}")
        return processed

    def _retry_with_debug(self, failed_code, error_msg, sample_data, adsl_data,
                           original_request, x_var, y_var, hbar_var):
        """Ask AI to fix failed code once using the original debug prompt, then give up."""
        data_info = {
            'columns':       list(sample_data.columns),
            'shape':         sample_data.shape,
            'sample_values': {col: list(sample_data[col].dropna().unique()[:3])
                              for col in sample_data.columns[:8]},
        }

        # ── ORIGINAL DEBUG PROMPT — UNCHANGED ──────────────────────────────────
        debug_prompt = f"""Fix this failed data customization code for CDISC clinical trial data:

FAILED DATA TRANSFORMATION CODE:
```python
{failed_code}
```

ERROR MESSAGE:
{error_msg}

ORIGINAL USER REQUEST:
{original_request}

DATASET CONTEXT:
- Columns: {data_info['columns']}
- Shape: {data_info['shape']}
- Sample values: {data_info['sample_values']}
- Key variables: Y={y_var}, X={x_var}, HBAR={hbar_var}

MERGE RULES (if merge is involved):
- LEFT JOIN adsl_data onto recist_data on USUBJID (always, never reverse)
- Deduplicate ADSL to one row per USUBJID before merging
- Select only needed ADSL columns before merging
- Row count must not increase after merge

COMMON FIXES FOR DATETIME/TIMEDELTA ERRORS:
- Use .dt.days instead of integer arithmetic on timedelta
- Use pd.to_timedelta() for time-based operations
- Convert datetime to numeric: (date_col - date_col.min()).dt.days
- Use .dt.total_seconds() / (24*3600) for days conversion

REQUIREMENTS:
1. Fix the specific error mentioned above
2. DataFrame names: recist_data (ADRS input), adsl_data (ADSL input) → processed_data (output)
3. Apply only data transformations, no visualization
4. Preserve required columns: {y_var}, {x_var}, {hbar_var}
5. Keep ALL columns in output — do NOT drop columns
6. Handle datetime columns properly

Generate ONLY the corrected Python code:"""

        try:
            message = self.claude_client.messages.create(
                model=MODEL, max_tokens=3000, temperature=0.1,
                messages=[{"role": "user", "content": debug_prompt}],
            )
            fixed_code = self._clean_code(message.content[0].text.strip())

            exec_globals = {
                'pd': pd, 'np': np,
                'recist_data': sample_data.copy(),
                'adsl_data':   adsl_data.copy() if adsl_data is not None else pd.DataFrame(),
                'print': print,
            }
            exec(fixed_code, exec_globals)
            processed = exec_globals.get('processed_data')
            if processed is not None:
                print(f"✅ AI fix applied: {sample_data.shape} → {processed.shape}")
                return processed
        except Exception as e:
            print(f"⚠ AI fix also failed: {e}")

        print("Returning original data.")
        return sample_data

    # ── Reporting ──────────────────────────────────────────────────────────────

    def get_validation_report(self, x_var, y_var, hbar_var, processed_data):
        """Generate validation report for user approval"""
        dc = self.derivation_context
        return {
            'original_shape':    dc.get('original_shape', 'N/A'),
            'processed_shape':   dc.get('processed_shape',
                                        processed_data.shape if processed_data is not None else None),
            'user_request':      dc.get('user_request', 'No customization'),
            'derivation_code':   dc.get('derivation_code', ''),
            'derived_variables': dc.get('derived_variables', []),
            'formulas':          dc.get('formulas', {}),
            'data_snapshot': {
                'first_5': processed_data.head(5).to_dict() if processed_data is not None else {},
                'columns': list(processed_data.columns) if processed_data is not None else [],
                'dtypes':  {col: str(dtype) for col, dtype in processed_data.dtypes.items()}
                           if processed_data is not None else {},
            },
            'variables_for_plot': {'y_axis': y_var, 'x_axis': x_var, 'hbar': hbar_var},
        }

    def filter_data_to_plot_variables(self, data, required_vars, additional_vars=None):
        """Filter dataset to keep only variables needed for plotting"""
        if data is None:
            return None
        keep = set(required_vars)
        if isinstance(additional_vars, str):
            keep.add(additional_vars)
        elif isinstance(additional_vars, (list, tuple)):
            keep.update(additional_vars)
        cols = list(keep.intersection(data.columns))
        if not cols:
            print("⚠ No matching columns found for filtering.")
            return data
        filtered = data[cols].copy()
        print(f"Filtered: {len(data.columns)} → {len(filtered.columns)} columns kept: {cols}")
        return filtered

    def _clean_code(self, generated_code):
        """Simple code cleaning"""
        if '```python' in generated_code:
            start = generated_code.find('```python') + 9
            end   = generated_code.find('```', start)
            if end > start:
                return generated_code[start:end].strip()
        elif '```' in generated_code:
            start = generated_code.find('```') + 3
            end   = generated_code.find('```', start)
            if end > start:
                return generated_code[start:end].strip()
        return generated_code.strip()
