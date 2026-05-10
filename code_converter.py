"""
Code Converter Module
Converts Python swimmer plot code to R (ggplot2/plotly) or SAS (GTL).
"""

import os
import pandas as pd

MODEL = "claude-sonnet-4-6"


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

        os.makedirs("./saved_code", exist_ok=True)
        i = 1
        while os.path.exists(f"./saved_code/swimmer_plot_{language.lower()}_{i}.{ext}"):
            i += 1
        path = f"./saved_code/swimmer_plot_{language.lower()}_{i}.{ext}"

        if language == "SAS":
            header = f"/*\nClinical Trials Swimmer Plot — SAS\nGenerated: {pd.Timestamp.now()}\nConverted from Python\n*/\n\n"
        else:
            header = f"# Clinical Trials Swimmer Plot — {language}\n# Generated: {pd.Timestamp.now()}\n# Converted from Python\n\n"

        with open(path, 'w', encoding='utf-8') as f:
            f.write(header + code_content)

        return f"Saved as swimmer_plot_{language.lower()}_{i}.{ext}"

    # ── Private converters ─────────────────────────────────────────────────────

    def _convert_to_r(self, python_code, context_str):
        prompt = f"""Convert this Python swimmer plot to R using ggplot2 and plotly.
{context_str}
PYTHON CODE:
```python
{python_code}
```

R REQUIREMENTS:
1. Data frame name: recist_data
2. library() calls at top: ggplot2, plotly, dplyr, scales
3. geom_col() + coord_flip() for horizontal duration bars
4. geom_point() for overlay markers
5. ggplotly() for interactivity
6. Preserve same colors, titles, and layout as the Python version
7. pandas → dplyr; .dt.days → as.numeric(difftime(...))

Generate clean, executable R code:"""

        notes = [
            "R version uses ggplot2 (static) and plotly (interactive).",
            "Required: install.packages(c('ggplot2','plotly','dplyr','scales'))",
            "Data frame assumed to be named 'recist_data'.",
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
        msg = self.claude_client.messages.create(
            model=MODEL, max_tokens=4500, temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._clean_code(msg.content[0].text.strip())

    def _clean_code(self, text):
        for fence in ('```r', '```sas', '```python', '```'):
            if fence in text.lower():
                s = text.lower().find(fence) + len(fence)
                e = text.find('```', s)
                if e > s:
                    return text[s:e].strip()
        return text.strip()
