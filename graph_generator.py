"""
Graph Generator Module
Generates, debugs, and executes Python swimmer plot code via AI.
"""

import io
import os
import contextlib
import traceback
import pandas as pd
import numpy as np

from utils import clean_code, call_ai, next_save_path, MODEL

# Shared swimmer plot invariants injected into every prompt
_SWIMMER_INVARIANTS = """
═══════════════════════════════════════════════════════════════════
FUNDAMENTAL SWIMMER PLOT STRUCTURE — NEVER VIOLATE
═══════════════════════════════════════════════════════════════════
1. Y-AXIS: {y_var} column — categorical subject IDs, one tick per subject.
   NEVER use numeric indices. NEVER remove subjects.

2. HBAR (Horizontal Bars):
   go.Bar(orientation='h', y=hbar_data['{y_var}'], x=hbar_data['{hbar_var}'])
   ONE bar per subject — MANDATORY. Cannot be removed.
   hbar_data = plot_data.drop_duplicates(subset=['{y_var}'])

3. X-AXIS: {x_var} column — numeric/linear time scale. NEVER categorical.

4. OVERLAYS (optional):
   go.Scatter traces on top of HBARs using plot_data (ALL rows).
   y MUST reference {y_var} column values — NEVER numeric indices or y_pos variables.
   X position MUST be a numeric/day column — NEVER a categorical string column.
   DO NOT create subject_positions dicts or computed Y mappings.
"""

# Parameterized starter skeleton injected into every generation prompt.
# The AI must begin its code with this exactly — only customizations are added below it.
_STARTER_SKELETON = """
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ── SORT: longest bars at top ──────────────────────────────────
plot_data = recist_data.sort_values('{hbar_var}', ascending=True).copy()

# ── INITIALISE FIGURE ──────────────────────────────────────────
fig = go.Figure()

# ── HBAR TRACE — ONE BAR PER SUBJECT (MANDATORY) ──────────────
# Deduplicate to one row per subject for bars only
hbar_data = plot_data.drop_duplicates(subset=['{y_var}'])

fig.add_trace(
    go.Bar(
        orientation='h',
        name='Treatment Duration',
        y=hbar_data['{y_var}'],        # categorical Y — NEVER numeric indices
        x=hbar_data['{hbar_var}'],     # bar length = duration
        text=hbar_data['{hbar_var}'].astype(str) + 'd',
        textposition='outside',
        marker=dict(color='#aec7e8', line=dict(color='#1f77b4', width=1.2)),
        showlegend=True,
    )
)

# ── OVERLAYS go here — use plot_data (ALL rows) for scatter markers ──
# go.Scatter traces MUST use y=plot_data['{y_var}'] — NEVER numeric indices
# X position MUST be a numeric/day column — NEVER a categorical string column
# ─────────────────────────────────────────────────────────────────────
"""


class GraphGenerator:
    def __init__(self, claude_client=None, ai_enabled=False):
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled

    # ── Code generation ────────────────────────────────────────────────────────

    def generate_with_ai(self, x_var, y_var, hbar_var, graph_customization, processed_data, derivation_context=None):
        """Generate swimmer plot code with AI focusing on graph customizations."""
        invariants = _SWIMMER_INVARIANTS.format(y_var=y_var, x_var=x_var, hbar_var=hbar_var)

        # Parameterize skeleton with actual variable names
        skeleton = _STARTER_SKELETON.format(y_var=y_var, x_var=x_var, hbar_var=hbar_var)

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

DATA STRUCTURE NOTE:
- recist_data has {processed_data.shape[0]} rows and {processed_data[y_var].nunique()} unique subjects
- Average rows per subject: {processed_data.shape[0] / max(processed_data[y_var].nunique(), 1):.1f}
- hbar_data (for go.Bar): drop_duplicates on {y_var} → one row per subject
- plot_data (for go.Scatter overlays): ALL rows — one marker per assessment

═══════════════════════════════════════════════════════════════════
SWIMMER PLOT TERMINOLOGY
═══════════════════════════════════════════════════════════════════
HBAR = go.Bar(orientation='h') traces — uses hbar_data (one row per subject).
  "for Hbar" instructions → modify go.Bar traces (color, border, hover, text).
  Inline bar labels: use text= and textposition= directly in go.Bar().
  DO NOT use fig.add_annotation() loops for bar end labels.

OVERLAYS = go.Scatter(mode='markers') traces — uses plot_data (all rows).
  "overlay EOS" → x=plot_data['EOS'] (the variable IS the numeric X position).
  "overlay [VARIABLE]" where variable is a timepoint → x=plot_data['VARIABLE'].
  "overlay categorical assessments" → color/symbol by category, x=plot_data['{x_var}'].
  CRITICAL: X position of overlays MUST be numeric (same axis as HBARs).
  NEVER set x= to a categorical string column — use it for color/symbol grouping only.
  Always filter to non-null: plot_data[plot_data['VAR'].notna()].

═══════════════════════════════════════════════════════════════════
YOUR CODE MUST START WITH THIS SKELETON — DO NOT MODIFY IT
ONLY ADD: overlay traces, layout, axis settings below the skeleton
═══════════════════════════════════════════════════════════════════
```python
{skeleton}
```

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
- Start with the skeleton above verbatim (imports already included)
- go.Scatter(mode='markers') for overlays, using plot_data (ALL rows)
- y references MUST use {y_var} column values — never numeric indices
- fig.update_layout() for title, axis labels, legend, height
- fig.update_xaxes(type='linear') — ALWAYS linear
- fig.update_yaxes(type='category') — ALWAYS category
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
- hbar_data must be drop_duplicates(subset=['{y_var}']) from plot_data
- Overlay x= must be a numeric column, never a categorical string column

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
        path = next_save_path('swimmer_plot', 'py')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'"""\nClinical Trials Swimmer Plot\nGenerated: {pd.Timestamp.now()}\n"""\n\n{code_content}')
        return f"Saved as {os.path.basename(path)}"

    # ── Internal ───────────────────────────────────────────────────────────────

    def _call_ai(self, prompt, max_tokens=4000, temperature=0.1):
        return call_ai(self.claude_client, prompt, max_tokens=max_tokens, temperature=temperature)
