"""
Graph Generator Module
Generates Python code for swimmer plots using processed data
Handles:
- AI-based code generation
- Graph customization application
- Code execution
"""

import pandas as pd
import numpy as np
import io
import contextlib
import traceback


class GraphGenerator:
    def __init__(self, claude_client=None, ai_enabled=False):
        """Initialize graph generator with AI client"""
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled

    def generate_with_ai(self, x_var, y_var, hbar_var, graph_customization, processed_data, derivation_context=None):
        """Generate swimmer plot code with AI focusing on graph customizations only - FIXED VERSION"""

        data_info = {
            'columns': list(processed_data.columns),
            'shape': processed_data.shape,
            'sample_values': {col: list(processed_data[col].dropna().unique()[:3]) for col in processed_data.columns[:8]}
        }

        # CRITICAL FIX: Save the processed data to the execution environment
        print(f"Processed data shape for graph generation: {processed_data.shape}")

        # Build derivation context section
        derivation_context_str = ""
        if derivation_context and derivation_context.get('derivation_code'):
            derivation_context_str = f"""
DATA PREPARATION CONTEXT:
The dataset 'recist_data' was created using this derivation code:
```python
{derivation_context['derivation_code'][:500]}...
```

Derived Variables:
{chr(10).join([f"• {var}: {derivation_context['formulas'].get(var, 'formula not captured')}" for var in derivation_context.get('derived_variables', [])])}

Original data: {derivation_context.get('original_shape', 'N/A')} rows
Processed data: {processed_data.shape[0]} rows (THIS is what you're plotting)
"""

        prompt = f"""Generate Python code for a Clinical Trials Oncology swimmer plot visualization.

═══════════════════════════════════════════════════════════════════
SECTION 0: FUNDAMENTAL SWIMMER PLOT DEFINITION - NEVER VIOLATE
═══════════════════════════════════════════════════════════════════
A SWIMMER PLOT ALWAYS HAS THIS CORE STRUCTURE:

1. Y-AXIS: Categorical variable showing subjects/patients
   - Variable: {y_var}
   - ONE unique tick value for EACH unique {y_var} value
   - Example: If {y_var} has values ["001", "002", "003"], Y-axis shows 3 ticks
   - All subjects MUST be visible - never remove subjects

2. HORIZONTAL BARS (HBARs):
   - ONE bar per subject (per unique {y_var} value)
   - Variable: {hbar_var} determines bar LENGTH
   - Positioned horizontally at each subject's Y-tick
   - Created with: go.Bar(orientation='h', y={y_var}, x={hbar_var})
   - CANNOT be removed - this IS the swimmer plot

3. X-AXIS: Numeric/linear scale
   - Variable: {x_var}
   - Represents time/days/duration
   - Must remain numeric (never categorical)

4. OVERLAYS (optional):
   - Scatter markers plotted ON TOP of HBARs
   - Can have multiple markers per subject
   - Added with: go.Scatter() traces
   - ⚠️ CRITICAL ALIGNMENT: ALL traces MUST use y=data['{y_var}'] for Y-axis
   - This applies to: go.Bar(), go.Scatter(), go.Line(), any plotly trace type
   - NEVER use numeric indices (0, 1, 2...) or computed positions (y_pos, subject_positions[subject]) for Y-coordinates
   - Both HBARs and overlays must reference the '{y_var}' column values directly
   - DO NOT create subject_positions dictionary or use y_pos variables
   - ALL plot requests (bars, markers, lines, annotations) use '{y_var}' for Y-axis

WHEN MODIFYING: You can change colors, styling, annotations, overlays
BUT NEVER: Remove HBARs, remove subjects, change axis types, use custom Y-position mappings

═══════════════════════════════════════════════════════════════════
SECTION 1: CRITICAL CONTEXT - UNDERSTAND THE DATA
═══════════════════════════════════════════════════════════════════
{derivation_context_str}

CURRENT DATASET TO PLOT:
- DataFrame name: 'recist_data'
- Shape: {processed_data.shape[0]} rows × {processed_data.shape[1]} columns
- Columns: {data_info['columns']}
- Sample values: {data_info['sample_values']}

CRITICAL: This data is FINAL - DO NOT filter, subset, or transform it further!

═══════════════════════════════════════════════════════════════════
SECTION 2: SWIMMER PLOT TERMINOLOGY - LEARN THE VOCABULARY
═══════════════════════════════════════════════════════════════════
HBAR (Horizontal Bars):
• "HBAR" refers to go.Bar(orientation='h') traces showing duration
• Column: {hbar_var} determines the LENGTH/WIDTH of each bar
• Count: ONE horizontal bar for EACH unique {y_var} value
• Example: If 50 subjects, there are 50 horizontal bars

When user says "for Hbar" they mean:
• "remove hover for Hbar" → set hoverinfo='skip' on go.Bar traces
• "add border to Hbar" → set line=dict(color='black', width=1) on go.Bar
• "change Hbar color" → set marker_color on go.Bar
• "annotate at end of bar" → use inline annotations with text and textposition parameters in the go.Bar() call
  - CRITICAL: Do NOT use separate fig.add_annotation() loops
  - Use text=data['{hbar_var}'] and textposition='outside' directly in go.Bar()

Overlay Variables:
• Variables plotted as go.Scatter() markers ON TOP of HBARs
• Multiple markers per subject are OK (one per assessment)
• Positioned at specific X-axis timepoints

Y-Axis Layout:
• Shows all unique {y_var} values (one per subject)
• Example: Subject IDs like "001", "002", "003"
• Each subject gets one row/tick on Y-axis

═══════════════════════════════════════════════════════════════════
SECTION 3: PLOT VARIABLE MAPPING
═══════════════════════════════════════════════════════════════════
Y-axis (Categorical): {y_var} - subject identifiers
X-axis (Linear): {x_var} - time/days/dates
HBAR (Duration): {hbar_var} - treatment duration per subject

═══════════════════════════════════════════════════════════════════
SECTION 4: USER'S GRAPH CUSTOMIZATION REQUEST
═══════════════════════════════════════════════════════════════════
{graph_customization if graph_customization else "Use standard Clinical Trials swimmer plot design with clean styling"}

INSTRUCTION PARSING RULES:
1. If user provides numbered list, implement EVERY item (do not skip any)
2. Go through each instruction step-by-step
3. For ambiguous terms, refer to SECTION 2 terminology
4. If user says "overlay [VARIABLE_NAME]":
   - If VARIABLE_NAME is a numeric/timepoint variable (like EOS, PROGRESSION_DAY, DEATH_DAY), use x=data['VARIABLE_NAME']
   - The variable name itself indicates the X-position
   - Example: "overlay EOS" means x=eos_subset['EOS'], NOT x=eos_subset['{x_var}']
5. If unclear, use standard clinical trial styling

═══════════════════════════════════════════════════════════════════
SECTION 5: CODE GENERATION GUIDELINES
═══════════════════════════════════════════════════════════════════

REQUIREMENTS:
1. Use Plotly Graph Objects (import plotly.graph_objects as go)
2. Create fig = go.Figure()
3. Use recist_data as the DataFrame (already prepared and filtered)

HBAR IMPLEMENTATION REQUIREMENTS:
• Use go.Bar(orientation='h') for horizontal bars
• Y-axis: Use {y_var} column values directly (actual subject IDs)
• X-axis: Use {hbar_var} column values (bar length)
• ONE bar per unique subject (aggregate if needed with groupby)
• MUST include inline text annotations showing HBAR value at end of bar
  - Use 'text' parameter with HBAR values
  - Use 'textposition' parameter to position at bar end
  - DO NOT use separate fig.add_annotation() loops
• Y-axis values must be actual {y_var} column values (NOT numeric indices)

OVERLAY IMPLEMENTATION REQUIREMENTS:
• Use go.Scatter(mode='markers') for overlay points
• Y-axis: Use same {y_var} column values as HBAR (for alignment)
• X-axis: Use the overlay variable itself if it represents a timepoint/numeric value
  - If overlaying variable EOS (end of study day), use x=data['EOS']
  - If overlaying variable PROGRESSION_DAY, use x=data['PROGRESSION_DAY']
  - If overlaying categorical assessments at timepoints, use x=data['{x_var}']
• Multiple points per subject are allowed
• Apply colors/symbols based on categories if needed
• Filter to non-null values: data[data['OVERLAY_VAR'].notna()]

CRITICAL ALIGNMENT RULE:
• All traces (HBAR and overlays) MUST use y={y_var} column values
• NEVER use numeric indices (0, 1, 2...) for Y-axis
• NEVER create custom Y-position mappings or dictionaries
• This ensures automatic alignment between bars and overlay points

LAYOUT REQUIREMENTS:
• Set appropriate title
• Label X-axis and Y-axis
• Configure legend
• Adjust height based on number of subjects
• Use fig.update_layout() for layout settings
• Use fig.update_xaxes() and fig.update_yaxes() (plural) for axis settings
• End with fig.show()

CODE QUALITY:
• Use clear variable names
• Add comments for each section
• Group related traces together
• Handle missing data appropriately

OVERLAY DERIVED DATA POINTS (ADVANCED):
If user requests to derive and overlay NEW data points:
- Create derived data in a SEPARATE variable (e.g., derived_events = ...)
- Calculate the derived metric/timepoint from existing recist_data columns
- Add as a NEW go.Scatter() trace on top of existing plot
- DO NOT modify the base horizontal bars or existing traces
- Examples of derivable overlays:
  * "Show progression events as red diamonds" → derive from progression date column
  * "Mark 50% duration point as vertical line" → calculate {hbar_var} * 0.5
  * "Overlay adverse events as yellow triangles" → use AE date columns
  * "Add median survival line" → calculate median from duration data
- Pattern: fig.add_trace(go.Scatter(x=derived_x, y=derived_y, mode='markers', marker=dict(...)))
- Keep original plot structure intact, only ADD new visual layers

IMPORTANT REMINDERS:
- Use recist_data directly - it has already been filtered to {processed_data.shape[0]} rows
- Do NOT add any filtering like recist_data[recist_data['column'] > value]
- Do NOT subset or modify recist_data in any way
- Apply only visual styling: colors, titles, fonts, layouts
- The data transformations have already been applied

Generate clean, executable Python code for visualization only:"""

        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=6000,  # Increased from 4000 to handle complex multi-part instructions
                temperature=0.15,  # Slightly increased from 0.1 for better reasoning with complex instructions
                messages=[{"role": "user", "content": prompt}]
            )

            generated_code = self._clean_code(message.content[0].text.strip())

            print(f"Generated graph code for {processed_data.shape[0]} rows of data")
            return generated_code

        except Exception as e:
            return f"# Error: AI generation failed: {str(e)}"

    def debug_code(self, failed_code, error_message, sample_data, x_var, y_var, hbar_var):
        """AI debugging with strict swimmer plot guardrails"""

        if not self.ai_enabled:
            return "# Error: AI debugging not available", ["AI required"], "error"

        debug_prompt = f"""Debug failed Clinical Trials swimmer plot code with STRICT requirements:

FAILED CODE:
```python
{failed_code}
```

ERROR: {error_message}

MANDATORY SWIMMER PLOT STRUCTURE:
1. Use Plotly Graph Objects (go.Figure) ONLY
2. Y-axis: {y_var} (categorical - subjects)
3. X-axis: {x_var} (numeric/datetime - time)
4. HBAR: {hbar_var} (duration for each {y_var})
5. DataFrame name: recist_data
6. End with: fig.show()

REQUIRED STRUCTURE (must include):
- fig = go.Figure()
- go.Bar(orientation='h') for horizontal duration bars
- go.Scatter() for assessment markers
- Proper datetime handling: .dt.days, .dt.total_seconds()/(24*3600)
- Handle missing data: dropna() or fillna()

COMMON FIXES:
- TimedeltaArray: use .dt.days
- Column errors: check exact column names
- Plotly syntax: correct go.Bar/go.Scatter parameters
- Data type errors: pd.to_numeric(errors='coerce')

Generate ONLY corrected Python swimmer plot code:"""

        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3500,
                temperature=0.1,
                messages=[{"role": "user", "content": debug_prompt}]
            )

            debugged_code = self._clean_code(message.content[0].text.strip())

            return debugged_code, ["AI-debugged with strict guardrails", "Ready for re-execution"], "debug"

        except Exception as e:
            return f"# Error: AI debugging failed: {str(e)}", ["Debug failed"], "error"

    def execute_code_safely(self, code_content, processed_data):
        """Execute swimmer plot code safely - FIXED TO USE PROCESSED DATA"""

        print(f"Executing code with processed data: {processed_data.shape if processed_data is not None else 'None'}")

        exec_globals = {
            'pd': pd, 'np': np,
            'recist_data': processed_data.copy() if processed_data is not None else pd.DataFrame(),
            'print': print,
        }

        # Add Plotly
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            exec_globals['go'] = go
            exec_globals['px'] = px
        except ImportError:
            return {
                'success': False,
                'error': 'Plotly not available - install with: pip install plotly',
                'plotly_html': None,
                'debug_available': self.ai_enabled
            }

        result = {'success': False, 'error': '', 'plotly_html': None, 'debug_available': self.ai_enabled}

        try:
            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exec(code_content, exec_globals)

            # Capture any print output from the executed code
            output = stdout_capture.getvalue()
            if output:
                print("Code execution output:", output)

            # Find Plotly figures
            for var_name, var_value in exec_globals.items():
                if hasattr(var_value, 'to_html') and hasattr(var_value, 'data'):
                    result['plotly_html'] = var_value.to_html(include_plotlyjs='cdn')
                    print(f"Found Plotly figure: {var_name}")
                    break

            result['success'] = True
            print("Swimmer plot generated successfully")

        except Exception as e:
            result['error'] = f"Error: {str(e)}\n{traceback.format_exc()}"
            print(f"Execution error: {str(e)}")

        return result

    def save_code(self, code_content):
        """Save generated swimmer plot code"""
        import os
        try:
            os.makedirs("./saved_code", exist_ok=True)
            counter = 1
            while os.path.exists(f"./saved_code/swimmer_plot_{counter}.py"):
                counter += 1

            filename = f"./saved_code/swimmer_plot_{counter}.py"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f'"""\nClinical Trials Swimmer Plot\nGenerated: {pd.Timestamp.now()}\n"""\n\n{code_content}')

            return f"Saved as swimmer_plot_{counter}.py"
        except Exception as e:
            return f"Save failed: {str(e)}"

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

        # Remove fig.show() statements to prevent external window opening
        generated_code = generated_code.replace('fig.show()', '# fig.show() removed for Shiny integration')

        return generated_code.strip()
