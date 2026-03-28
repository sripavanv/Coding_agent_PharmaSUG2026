"""
Code Converter Module
Converts Python swimmer plot code to R or SAS
Handles language-specific syntax and plotting libraries
"""

import pandas as pd
import os


class CodeConverter:
    def __init__(self, claude_client=None, ai_enabled=False):
        """Initialize code converter with AI client"""
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled

    def convert_code_to_language(self, python_code, target_language, plot_context=None):
        """Convert Python swimmer plot code to R or SAS"""

        if not self.ai_enabled:
            return "# Error: AI not available for code conversion", "error", []

        if not python_code or not python_code.strip():
            return "# Error: No Python code available for conversion", "error", []

        if target_language not in ["R", "SAS"]:
            return f"# Error: Unsupported target language: {target_language}", "error", []

        print(f"\n=== CODE CONVERSION TO {target_language} ===")
        print(f"Converting {len(python_code)} characters of Python code...")

        try:
            if target_language == "R":
                converted_code = self._convert_to_r(python_code, plot_context)
                notes = [
                    "R version uses ggplot2 for static plots and plotly for interactive plots",
                    "Required packages: ggplot2, plotly, dplyr, scales",
                    "Data frame assumed to be named 'recist_data'",
                    "Install packages: install.packages(c('ggplot2', 'plotly', 'dplyr', 'scales'))"
                ]
            else:  # SAS
                converted_code = self._convert_to_sas(python_code, plot_context)
                notes = [
                    "SAS version uses GTL (Graph Template Language) for swimmer plots",
                    "Creates PROC TEMPLATE to define the graph layout",
                    "Uses PROC SGRENDER to render the defined template",
                    "Dataset assumed to be named RECIST_DATA",
                    "Supports SAS 9.4+ with ODS Graphics enabled"
                ]

            print(f"✅ Successfully converted to {target_language}")
            return converted_code, "success", notes

        except Exception as e:
            error_msg = f"Code conversion to {target_language} failed: {str(e)}"
            print(error_msg)
            return f"# Error: {error_msg}", "error", []

    def _convert_to_r(self, python_code, plot_context):
        """Convert Python swimmer plot code to R using ggplot2 and plotly"""

        context_info = ""
        if plot_context:
            context_info = f"""
PLOT CONTEXT:
- X-axis variable: {plot_context.get('x_var', 'Unknown')}
- Y-axis variable: {plot_context.get('y_var', 'Unknown')}
- HBAR variable: {plot_context.get('hbar_var', 'Unknown')}
- Data shape: {plot_context.get('processed_data_shape', 'Unknown')}
"""

        prompt = f"""Convert this Python swimmer plot code to R using ggplot2 and plotly:

{context_info}

PYTHON CODE TO CONVERT:
```python
{python_code}
```

REQUIREMENTS FOR R CONVERSION:
1. Use R syntax and ggplot2/plotly libraries
2. Data frame name: recist_data (R naming convention)
3. Create equivalent swimmer plot with horizontal bars + scatter points
4. Maintain the same visual customizations (colors, titles, layouts)
5. Use geom_col() for horizontal bars and geom_point() for scatter markers
6. Convert to interactive plotly if the Python version uses plotly
7. Handle any datetime conversions using lubridate or base R
8. Include library() calls at the top

R SWIMMER PLOT STRUCTURE:
- library(ggplot2, plotly, dplyr, scales)
- Use recist_data data frame
- geom_col() with coord_flip() for horizontal duration bars
- geom_point() for assessment timepoints
- Equivalent styling: theme(), scale_color_manual(), labs()
- ggplotly() for interactivity if needed

CONVERSION NOTES:
- Python pandas → R dplyr equivalents
- Python .dt.days → R as.numeric(difftime())
- Plotly Python fig.update_layout() → R ggplotly() %>% layout()
- Python string formatting → R paste() or glue()

Generate clean, executable R code with proper swimmer plot structure:"""

        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4500,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            r_code = self._clean_code(message.content[0].text.strip())
            print(f"Generated {len(r_code)} characters of R code")

            return r_code

        except Exception as e:
            return f"# Error converting to R: {str(e)}"

    def _convert_to_sas(self, python_code, plot_context):
        """Convert Python swimmer plot code to SAS using GTL (Graph Template Language)"""

        context_info = ""
        if plot_context:
            context_info = f"""
PLOT CONTEXT:
- X-axis variable: {plot_context.get('x_var', 'Unknown')}
- Y-axis variable: {plot_context.get('y_var', 'Unknown')}
- HBAR variable: {plot_context.get('hbar_var', 'Unknown')}
- Data shape: {plot_context.get('processed_data_shape', 'Unknown')}
"""

        prompt = f"""Convert this Python swimmer plot code to SAS using GTL (Graph Template Language):

{context_info}

PYTHON CODE TO CONVERT:
```python
{python_code}
```

REQUIREMENTS FOR SAS GTL CONVERSION:
1. Use SAS GTL (Graph Template Language) for maximum flexibility
2. Create a PROC TEMPLATE to define the swimmer plot layout
3. Use PROC SGRENDER to render the template with data
4. Dataset name: RECIST_DATA (SAS naming convention)
5. Create equivalent swimmer plot with horizontal bars + scatter points
6. Maintain the same visual customizations (colors, titles, layouts)
7. Handle any datetime processing with SAS date functions
8. Include proper title, axis labels, and legend options

SAS GTL SWIMMER PLOT STRUCTURE:
- PROC TEMPLATE; DEFINE STATGRAPH swimmer_plot;
  - BEGINGRAPH / DESIGNWIDTH=800px DESIGNHEIGHT=600px;
  - LAYOUT OVERLAY / XAXISOPTS=(...) YAXISOPTS=(...);
    - BARCHARTPARM for horizontal duration bars
    - SCATTERPLOT for assessment timepoints
    - ENTRY statements for title and footnotes
  - ENDLAYOUT;
  - ENDGRAPH;
- END; RUN;
- PROC SGRENDER DATA=RECIST_DATA TEMPLATE=swimmer_plot;
- RUN;

CONVERSION NOTES:
- Python pandas operations → SAS DATA steps
- Python .dt.days → SAS DATDIF() or similar functions
- Plotly styling → GTL STYLEATTRS, DISCRETEATTRMAP, and appearance options
- Python string operations → SAS string functions
- Group coloring → GTL GROUP= with DISCRETEATTRMAP
- Interactive features → Use ODS destinations like HTML5 with drill-down
- GTL provides pixel-perfect control over layout and styling

Generate clean, executable SAS GTL code with PROC TEMPLATE definition and PROC SGRENDER execution:"""

        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4500,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            sas_code = self._clean_code(message.content[0].text.strip())
            print(f"Generated {len(sas_code)} characters of SAS code")

            return sas_code

        except Exception as e:
            return f"/* Error converting to SAS: {str(e)} */"

    def save_converted_code(self, code_content, language):
        """Save converted code with appropriate file extension"""
        try:
            os.makedirs("./saved_code", exist_ok=True)

            # Set file extension based on language
            if language == "R":
                ext = "R"
                comment_style = "#"
            elif language == "SAS":
                ext = "sas"
                comment_style = "/*"
            else:
                ext = "txt"
                comment_style = "#"

            counter = 1
            while os.path.exists(f"./saved_code/swimmer_plot_{language.lower()}_{counter}.{ext}"):
                counter += 1

            filename = f"./saved_code/swimmer_plot_{language.lower()}_{counter}.{ext}"

            # Create appropriate header comment
            if language == "SAS":
                header = f"""/*
Clinical Trials Swimmer Plot - {language} Version
Generated: {pd.Timestamp.now()}
Converted from Python code
*/

"""
            else:
                header = f"""{comment_style} Clinical Trials Swimmer Plot - {language} Version
{comment_style} Generated: {pd.Timestamp.now()}
{comment_style} Converted from Python code

"""

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(header + code_content)

            return f"Saved as swimmer_plot_{language.lower()}_{counter}.{ext}"

        except Exception as e:
            return f"Save failed: {str(e)}"

    def _clean_code(self, generated_code):
        """Simple code cleaning"""
        # Remove markdown code blocks
        if '```r' in generated_code.lower():
            start = generated_code.lower().find('```r') + 4
            end = generated_code.find('```', start)
            if end > start:
                return generated_code[start:end].strip()
        elif '```sas' in generated_code.lower():
            start = generated_code.lower().find('```sas') + 6
            end = generated_code.find('```', start)
            if end > start:
                return generated_code[start:end].strip()
        elif '```' in generated_code:
            start = generated_code.find('```') + 3
            end = generated_code.find('```', start)
            if end > start:
                return generated_code[start:end].strip()

        return generated_code.strip()
