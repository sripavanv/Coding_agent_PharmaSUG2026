"""
Graph Generator Module
Generates, debugs, and executes Python swimmer plot code via AI.
"""

import io
import contextlib
import traceback
import pandas as pd
import numpy as np

MODEL = "claude-sonnet-4-6"

# Shared swimmer plot invariants injected into every prompt
_SWIMMER_INVARIANTS = """
═══════════════════════════════════════════════════════════════════
FUNDAMENTAL SWIMMER PLOT STRUCTURE — NEVER VIOLATE
═══════════════════════════════════════════════════════════════════
1. Y-AXIS: {y_var} column — categorical subject IDs, one tick per subject.
   NEVER use numeric indices. NEVER remove subjects.

2. HBAR (Horizontal Bars):
   go.Bar(orientation='h', y=data['{y_var}'], x=data['{hbar_var}'])
   ONE bar per subject — MANDATORY. Cannot be removed.

3. X-AXIS: {x_var} column — numeric/linear time scale. NEVER categorical.

4. OVERLAYS (optional):
   go.Scatter traces on top of HBARs.
   y MUST reference {y_var} column values — NEVER numeric indices or y_pos variables.
   DO NOT create subject_positions dicts or computed Y mappings.
"""


class GraphGenerator:
    def __init__(self, claude_client=None, ai_enabled=False):
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled

    # ── Code generation ────────────────────────────────────────────────────────

    def generate_with_ai(self, x_var, y_var, hbar_var, graph_customization, processed_data, derivation_context=None):
        """Generate swimmer plot code with AI focusing on graph customizations."""
        invariants = _SWIMMER_INVARIANTS.format(y_var=y_var, x_var=x_var, hbar_var=hbar_var)

        # Build derivation context section (handover from data step)
        deriv_section = ""
        if derivation_context and derivation_context.get('derivation_code'):
            dc = derivation_context
            vars_list = "\n".join(
                f"  • {v}: {dc['formulas'].get(v, '')}"
                for v in dc.get('derived_variables', [])
            )
            deriv_section = f"""
DATA PREPARATION CONTEXT (already applied — do not re-apply):
```python
{dc['derivation_code'][:500]}...
```
Derived variables:
{vars_list}
Original → processed: {dc.get('original_shape', '?')} → {processed_data.shape[0]} rows
"""

        data_info = {
            'columns': list(processed_data.columns),
            'shape':   processed_data.shape,
            'sample_values': {
                col: list(processed_data[col].dropna().unique()[:3])
                for col in processed_data.columns[:8]
            },
        }

        prompt = f"""Generate Python code for a Clinical Trials Oncology swimmer plot.

{invariants}

═══════════════════════════════════════════════════════════════════
DATASET CONTEXT
═══════════════════════════════════════════════════════════════════
{deriv_section}
DataFrame name: recist_data — DO NOT filter, subset, or transform it.
- Shape: {data_info['shape']}
- Columns: {data_info['columns']}
- Sample values: {data_info['sample_values']}

VARIABLE MAPPING:
- Y-axis (categorical): {y_var}
- X-axis (linear):      {x_var}
- HBAR (duration):      {hbar_var}

═══════════════════════════════════════════════════════════════════
SWIMMER PLOT TERMINOLOGY
═══════════════════════════════════════════════════════════════════
HBAR = go.Bar(orientation='h') traces — one per unique {y_var} value.
  "for Hbar" instructions → modify go.Bar traces (color, border, hover, text).
  Inline bar labels: use text= and textposition= directly in go.Bar().
  DO NOT use fig.add_annotation() loops for bar end labels.

OVERLAYS = go.Scatter(mode='markers') traces on top of HBARs.
  "overlay EOS" → x=data['EOS'] (the variable IS the X position).
  "overlay [VARIABLE]" where variable is a timepoint → x=data['VARIABLE'].
  "overlay categorical assessments" → x=data['{x_var}'].
  Always filter to non-null: data[data['VAR'].notna()].

═══════════════════════════════════════════════════════════════════
USER'S GRAPH CUSTOMIZATION REQUEST
═══════════════════════════════════════════════════════════════════
{graph_customization if graph_customization else "Standard clinical trial swimmer plot design."}

INSTRUCTION RULES:
1. If numbered list — implement EVERY item, skip none.
2. Ambiguous terms → refer to terminology section above.
3. If asked to "derive and overlay" — derive inline as a separate variable, then add a go.Scatter trace.

═══════════════════════════════════════════════════════════════════
CODE REQUIREMENTS
═══════════════════════════════════════════════════════════════════
- import plotly.graph_objects as go
- fig = go.Figure()
- go.Bar(orientation='h') for HBARs with inline text labels (text=, textposition=)
- go.Scatter(mode='markers') for overlays
- y references MUST use {y_var} column values — never numeric indices
- fig.update_layout() for title, axis labels, legend, height
- fig.update_xaxes() / fig.update_yaxes() for axis settings
- End with: fig.show()
- Clear variable names, section comments, handle missing data (dropna/notna)

Generate clean, executable Python code:"""

        return self._call_ai(prompt, max_tokens=6000, temperature=0.15)

    # ── Debugging ──────────────────────────────────────────────────────────────

    def debug_code(self, failed_code, error_message, sample_data, x_var, y_var, hbar_var):
        """Ask AI to fix broken swimmer plot code."""
        if not self.ai_enabled:
            return "# Error: AI debugging not available", ["AI required"], "error"

        invariants = _SWIMMER_INVARIANTS.format(y_var=y_var, x_var=x_var, hbar_var=hbar_var)

        prompt = f"""Debug this failed Clinical Trials swimmer plot code.

{invariants}

FAILED CODE:
```python
{failed_code}
```

ERROR: {error_message}

DATASET: recist_data | Key vars: Y={y_var}, X={x_var}, HBAR={hbar_var}

COMMON FIXES:
- TimedeltaArray: use .dt.days or .dt.total_seconds()/(24*3600)
- Column errors: verify exact column names in recist_data
- Data types: pd.to_numeric(errors='coerce')
- Y-axis: must use {y_var} column values, not numeric indices

End fixed code with: fig.show()

Generate ONLY the corrected Python code:"""

        code = self._call_ai(prompt, max_tokens=3500, temperature=0.1)
        return code, ["AI-debugged — ready for re-execution"], "debug"

    # ── Execution ──────────────────────────────────────────────────────────────

    def execute_code_safely(self, code_content, processed_data):
        """Execute swimmer plot code in an isolated namespace and return Plotly HTML."""
        try:
            import plotly.graph_objects as go
            import plotly.express as px
        except ImportError:
            return {
                'success': False,
                'error': 'Plotly not available. Install with: pip install plotly',
                'plotly_html': None, 'debug_available': self.ai_enabled,
            }

        exec_globals = {
            'pd': pd, 'np': np, 'go': go, 'px': px, 'print': print,
            'recist_data': processed_data.copy() if processed_data is not None else pd.DataFrame(),
        }
        result = {'success': False, 'error': '', 'plotly_html': None, 'debug_available': self.ai_enabled}

        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(code_content, exec_globals)

            for val in exec_globals.values():
                if hasattr(val, 'to_html') and hasattr(val, 'data'):
                    result['plotly_html'] = val.to_html(include_plotlyjs='cdn')
                    break
            result['success'] = True
            print("✅ Swimmer plot executed successfully.")

        except Exception as e:
            result['error'] = f"{e}\n{traceback.format_exc()}"
            print(f"⚠ Execution error: {e}")

        return result

    # ── Persistence ────────────────────────────────────────────────────────────

    def save_code(self, code_content):
        import os
        os.makedirs("./saved_code", exist_ok=True)
        i = 1
        while os.path.exists(f"./saved_code/swimmer_plot_{i}.py"):
            i += 1
        path = f"./saved_code/swimmer_plot_{i}.py"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'"""\nClinical Trials Swimmer Plot\nGenerated: {pd.Timestamp.now()}\n"""\n\n{code_content}')
        return f"Saved as swimmer_plot_{i}.py"

    # ── Internal ───────────────────────────────────────────────────────────────

    def _call_ai(self, prompt, max_tokens=4000, temperature=0.1):
        msg = self.claude_client.messages.create(
            model=MODEL, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._clean_code(msg.content[0].text.strip())

    def _clean_code(self, text):
        """Strip markdown fences; remove fig.show() for Shiny/Dash compatibility."""
        if '```python' in text:
            s = text.find('```python') + 9
            e = text.find('```', s)
            if e > s:
                text = text[s:e].strip()
        elif '```' in text:
            s = text.find('```') + 3
            e = text.find('```', s)
            if e > s:
                text = text[s:e].strip()
        return text.replace('fig.show()', '# fig.show() removed for Shiny integration').strip()
