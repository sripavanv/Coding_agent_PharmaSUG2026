"""
Code Converter Module
Converts Python swimmer plot code to R (ggplot2/plotly) or SAS (GTL).
"""

import os
import pandas as pd

from utils import clean_code, call_ai, next_save_path, MODEL


class CodeConverter:
    def __init__(self, claude_client=None, ai_enabled=False):
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled

    def convert_code_to_language(self, python_code, target_language, plot_context=None):
        """Convert Python swimmer plot code to R or SAS."""
        if not self.ai_enabled:
            return "# Error: AI not available for code conversion", "error", []
        if not python_code or not python_code.strip():
            return "# Error: No Python code available for conversion", "error", []
        if target_language not in ("R", "SAS"):
            return f"# Error: Unsupported language '{target_language}'", "error", []

        print(f"\n=== CODE CONVERSION TO {target_language} ===")

        context_str = ""
        if plot_context:
            context_str = (
                f"\nPLOT CONTEXT:\n"
                f"- X={plot_context.get('x_var')}, Y={plot_context.get('y_var')}, "
                f"HBAR={plot_context.get('hbar_var')}, shape={plot_context.get('processed_data_shape')}\n"
            )

        if target_language == "R":
            converted_code, notes = self._convert_to_r(python_code, context_str)
        else:
            converted_code, notes = self._convert_to_sas(python_code, context_str)

        print(f"✅ Converted to {target_language}: {len(converted_code)} characters")
        return converted_code, "success", notes

    def save_converted_code(self, code_content, language):
        """Save converted code with the appropriate file extension."""
        ext_map = {"R": "R", "SAS": "sas"}
        ext = ext_map.get(language, "txt")
        prefix = f"swimmer_plot_{language.lower()}"
        path = next_save_path(prefix, ext)

        if language == "SAS":
            header = f"/*\nClinical Trials Swimmer Plot — SAS\nGenerated: {pd.Timestamp.now()}\nConverted from Python\n*/\n\n"
        else:
            header = f"# Clinical Trials Swimmer Plot — {language}\n# Generated: {pd.Timestamp.now()}\n# Converted from Python\n\n"

        with open(path, 'w', encoding='utf-8') as f:
            f.write(header + code_content)

        return f"Saved as {os.path.basename(path)}"

    # ── Private converters ─────────────────────────────────────────────────────

    def _convert_to_r(self, python_code, context_str):
        prompt = f"""Convert this Python swimmer plot to R using plotly (NOT ggplot2).
{context_str}
PYTHON CODE:
```python
{python_code}
```

R REQUIREMENTS:
1. Data frame name: recist_data
2. library() calls at top: plotly, dplyr
3. Use plotly directly with plot_ly() - do NOT use ggplot2 or ggplotly()
4. Use add_trace() with type='bar' for horizontal duration bars (orientation='h')
5. Use add_trace() with type='scattergl' and mode='markers' for overlay markers (WebGL for performance)
6. Use layout() to configure axes, titles, and styling
7. Preserve same colors, titles, and layout as the Python version
8. pandas → dplyr; .dt.days → as.numeric(difftime(...))

IMPORTANT: Use scattergl (not scatter) for all scatter plots to enable WebGL rendering for better performance.

Generate clean, executable R code:"""

        notes = [
            "R version uses plotly directly (not ggplot2).",
            "Required: install.packages(c('plotly','dplyr'))",
            "Data frame assumed to be named 'recist_data'.",
            "Scatter plots use WebGL (scattergl) for better performance."
        ]
        return self._call_ai(prompt), notes

    def _convert_to_sas(self, python_code, context_str):
        prompt = f"""Convert this Python swimmer plot to SAS using GTL (Graph Template Language).
{context_str}
PYTHON CODE:
```python
{python_code}
```

SAS GTL REQUIREMENTS:
1. Dataset name: RECIST_DATA
2. Structure:
   PROC TEMPLATE; DEFINE STATGRAPH swimmer_plot;
     BEGINGRAPH;
     LAYOUT OVERLAY / XAXISOPTS=(...) YAXISOPTS=(...);
       BARCHARTPARM for horizontal duration bars;
       SCATTERPLOT for overlay markers;
     ENDLAYOUT;
     ENDGRAPH;
   END; RUN;
   PROC SGRENDER DATA=RECIST_DATA TEMPLATE=swimmer_plot; RUN;
3. Preserve same colors, titles, and layout as the Python version
4. SAS 9.4+ with ODS Graphics enabled
5. Use DISCRETEATTRMAP for group coloring

Generate clean, executable SAS GTL code:"""

        notes = [
            "SAS version uses GTL (PROC TEMPLATE + PROC SGRENDER).",
            "Dataset assumed to be named RECIST_DATA.",
            "Requires SAS 9.4+ with ODS Graphics enabled.",
        ]
        return self._call_ai(prompt), notes

    def _call_ai(self, prompt):
        return call_ai(self.claude_client, prompt, max_tokens=4500, temperature=0.1)
