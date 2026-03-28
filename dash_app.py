"""
Swimmer Plot Generator - Dash Application
==========================================
A web application for generating oncology swimmer plots with data validation,
customization, and code generation capabilities.

Follows the same workflow as the Shiny app.
"""

import dash
from dash import dcc, html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import json
from datetime import datetime
import os
import webbrowser
import subprocess
import sys

# Check for API key
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("\n" + "="*60)
    print("ERROR: ANTHROPIC_API_KEY environment variable not set!")
    print("="*60)
    print("\nPlease set your Claude API key:")
    print("  On Linux/Mac:   export ANTHROPIC_API_KEY='your-key-here'")
    print("  On Windows:     set ANTHROPIC_API_KEY=your-key-here")
    print("\nExiting...")
    print("="*60 + "\n")
    sys.exit(1)

# Import data utilities and code generator
from data_utils import load_adsl, load_adrs
from code_generator import SwimmerPlotGenerator

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Swimmer Plot Generator"

# Create output directories
os.makedirs('outputs/validation_reports', exist_ok=True)
os.makedirs('outputs/graphs', exist_ok=True)
os.makedirs('outputs/code', exist_ok=True)

# Load CDISC datasets on startup
print("\n" + "="*60)
print("Loading CDISC datasets...")
print("="*60)
ADSL_DATA = load_adsl()
ADRS_DATA = load_adrs()

if ADSL_DATA is None or ADRS_DATA is None:
    print("\n" + "="*60)
    print("ERROR: Could not load ADSL or ADRS datasets!")
    print("="*60)
    print("\nPlease ensure these files exist in the root directory:")
    print("  - ADSL.csv")
    print("  - ADRS_ONCO.csv")
    print("\nExiting...")
    print("="*60 + "\n")
    sys.exit(1)

print(f"Datasets loaded successfully!")
print("="*60 + "\n")

# Initialize AI generator
generator = SwimmerPlotGenerator()

# =============================================================================
# LAYOUT COMPONENTS
# =============================================================================

# Header
header = dbc.Navbar(
    dbc.Container([
        html.H2("Clinical Trials Swimmer Plot Generator", className="text-white mb-0"),
    ]),
    color="primary",
    dark=True,
    className="mb-3"
)

# Sidebar
sidebar = dbc.Col([
    html.H6("CDISC Data", className="mb-2", style={'fontSize': '13px'}),

    dbc.Card([
        dbc.CardBody([
            html.P("ADSL Dataset", className="text-primary mb-1", style={'fontSize': '12px', 'fontWeight': 'bold'}),
            html.P([
                html.Strong("Rows: ", style={'fontSize': '11px'}), html.Span(f"{len(ADSL_DATA):,}", style={'fontSize': '11px'}),
                html.Br(),
                html.Strong("Variables: ", style={'fontSize': '11px'}), html.Span(f"{len(ADSL_DATA.columns):,}", style={'fontSize': '11px'})
            ], className="mb-0", style={'fontSize': '11px'})
        ], style={'padding': '8px'})
    ], className="mb-2"),

    dbc.Card([
        dbc.CardBody([
            html.P("ADRS Dataset", className="text-primary mb-1", style={'fontSize': '12px', 'fontWeight': 'bold'}),
            html.P([
                html.Strong("Rows: ", style={'fontSize': '11px'}), html.Span(f"{len(ADRS_DATA):,}", style={'fontSize': '11px'}),
                html.Br(),
                html.Strong("Variables: ", style={'fontSize': '11px'}), html.Span(f"{len(ADRS_DATA.columns):,}", style={'fontSize': '11px'})
            ], className="mb-0", style={'fontSize': '11px'})
        ], style={'padding': '8px'})
    ], className="mb-2"),

    html.Div(id='dataset-status-sidebar')

], width=3, style={
    'backgroundColor': '#F5F5F5',
    'padding': '15px',
    'minHeight': '100vh'
})

# Main Panel
main_panel = dbc.Col([
    # Stores for state management
    dcc.Store(id='original-data-store', storage_type='memory', data=ADRS_DATA.to_dict('records')),
    dcc.Store(id='customized-data-store', storage_type='memory', data=ADRS_DATA.to_dict('records')),
    dcc.Store(id='generated-code-store', storage_type='memory'),
    dcc.Store(id='validation-report-store', storage_type='memory'),
    dcc.Store(id='execution-result-store', storage_type='memory'),
    dcc.Store(id='conversation-history-store', storage_type='memory', data=[]),
    dcc.Store(id='converted-code-store', storage_type='memory'),

    # Main content area with tabs
    dcc.Tabs(id='main-tabs', value='data-tab', children=[
        dcc.Tab(label='Data Preparation', value='data-tab', children=[
            html.Div([
                html.H6("Step 1: Data Customization (Optional)", className="mb-2 mt-2", style={'fontSize': '13px'}),

                dcc.Textarea(
                    id='data-customization-textarea',
                    placeholder="Optional data transformations",
                    style={'width': '100%', 'height': '50px', 'fontSize': '12px'},
                    className="form-control mb-2"
                ),

                dbc.Row([
                    dbc.Col([
                        dbc.Button("Apply", id='apply-customization-btn', color="primary", size="sm", className="w-100", style={'fontSize': '12px'})
                    ], width=6),
                    dbc.Col([
                        dbc.Button("Reset", id='reset-data-btn', color="primary", size="sm", className="w-100", style={'fontSize': '12px'})
                    ], width=6)
                ], className="mb-2"),

                html.Div(id='customization-status', style={'fontSize': '11px'}),

                html.Hr(),

                html.P("Dataset Preview:", className="mb-2", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                html.Div(id='dataset-preview-table'),

                html.Hr(),

                html.H6("Step 2: Swimmer Plot Variables", className="mb-2", style={'fontSize': '13px'}),

                dbc.Row([
                    dbc.Col([
                        html.Label("Y-axis (Subjects):", style={'fontSize': '12px'}),
                        dcc.Dropdown(id='y-variable-dropdown', placeholder="Select subject...", className="mb-2", style={'fontSize': '12px'})
                    ], width=4),
                    dbc.Col([
                        html.Label("X-axis (Time):", style={'fontSize': '12px'}),
                        dcc.Dropdown(id='x-variable-dropdown', placeholder="Select time...", className="mb-2", style={'fontSize': '12px'})
                    ], width=4),
                    dbc.Col([
                        html.Label("HBAR Duration:", style={'fontSize': '12px'}),
                        dcc.Dropdown(id='hbar-variable-dropdown', placeholder="Select duration...", className="mb-2", style={'fontSize': '12px'})
                    ], width=4)
                ]),

                html.Label("Additional Variables to Keep:", style={'fontSize': '12px', 'marginTop': '5px'}),
                dcc.Dropdown(
                    id='keep-variables-dropdown',
                    placeholder="Select additional variables for unique dataset",
                    multi=True,
                    className="mb-2",
                    style={'fontSize': '12px'}
                ),
                html.P("These variables will be included in the unique dataset passed to the graph",
                       style={'fontSize': '11px', 'color': '#6c757d', 'marginBottom': '10px'}),

                dbc.Button("Generate Validation Report", id='generate-validation-btn', color="primary", size="sm", className="w-100 mb-2", style={'fontSize': '12px'}),

                html.Div(id='validation-report-display'),

                html.Hr(),

                html.H6("Step 3: Graph Customization (Optional)", className="mb-2", style={'fontSize': '13px'}),
                dcc.Textarea(
                    id='graph-customization-textarea',
                    placeholder="Visual styling (optional)",
                    style={'width': '100%', 'height': '50px', 'fontSize': '12px'},
                    className="form-control mb-2"
                ),

                dbc.Button("Generate Swimmer Plot", id='generate-code-btn', color="primary", size="sm", className="w-100", disabled=True, style={'fontSize': '12px'}),

            ], style={'padding': '20px'})
        ]),

        dcc.Tab(label='Generated Code', value='code-tab', children=[
            html.Div([
                html.H6("Generated Code", className="mt-2 mb-2", style={'fontSize': '13px'}),
                html.Div(id='code-display', style={'fontSize': '11px'}),
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Run Code", id='execute-code-btn', color="primary", size="sm", className="w-100", style={'fontSize': '12px'})
                    ], width=3),
                    dbc.Col([
                        dbc.Button("Save Code", id='save-code-btn', color="primary", size="sm", className="w-100", style={'fontSize': '12px'})
                    ], width=3),
                    dbc.Col([
                        html.Div(id='debug-button-container')
                    ], width=3)
                ])
            ], style={'padding': '15px'})
        ]),

        dcc.Tab(label='Swimmer Plot Results', value='results-tab', children=[
            html.Div([
                html.H6("Execution Results", className="mt-2 mb-2", style={'fontSize': '13px'}),
                html.Div(id='execution-status', style={'fontSize': '11px'}),
                html.Hr(),
                html.P("Generated Swimmer Plot:", className="mb-2", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                html.Div(id='swimmer-plot-display')
            ], style={'padding': '15px'})
        ]),

        dcc.Tab(label='Interactive Customization', value='dialogue-tab', children=[
            html.Div([
                html.H6("AI Dialogue for Plot Customization", className="mt-2 mb-2", style={'fontSize': '13px'}),
                html.Div(id='conversation-status', className="mt-2 mb-2", style={'fontSize': '11px'}),

                html.Div(id='dialogue-history', style={
                    'height': '300px',
                    'overflowY': 'auto',
                    'border': '1px solid #dee2e6',
                    'borderRadius': '8px',
                    'padding': '10px',
                    'background': '#fafafa',
                    'marginBottom': '10px',
                    'fontSize': '11px'
                }),

                dbc.Row([
                    dbc.Col([
                        dcc.Textarea(
                            id='dialogue-input',
                            placeholder="Tell me how to customize your plot...",
                            style={'width': '100%', 'height': '60px', 'fontSize': '12px'},
                            className="form-control"
                        )
                    ], width=9),
                    dbc.Col([
                        dbc.Button("Send Request", id='send-dialogue-btn', color="primary", size="sm", className="w-100 mb-2", style={'fontSize': '12px'}),
                        dbc.Button("Clear History", id='clear-dialogue-btn', color="primary", size="sm", className="w-100", style={'fontSize': '12px'})
                    ], width=3)
                ])
            ], style={'padding': '15px'})
        ]),

        dcc.Tab(label='Code Conversion', value='conversion-tab', children=[
            html.Div([
                html.H6("Convert Python Code to R or SAS", className="mt-2 mb-2", style={'fontSize': '13px'}),
                html.P("Convert to R (ggplot2/plotly) or SAS (GTL).", style={'fontSize': '11px'}),

                dbc.Row([
                    dbc.Col([
                        dbc.RadioItems(
                            id='conversion-language',
                            options=[
                                {'label': 'R (using ggplot2 + plotly)', 'value': 'R'},
                                {'label': 'SAS (using GTL - Graph Template Language)', 'value': 'SAS'}
                            ],
                            value='R',
                            className="mb-2",
                            style={'fontSize': '12px'}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Button("Convert Code", id='convert-code-btn', color="primary", size="sm", className="w-100 mb-2", style={'fontSize': '12px'}),
                        dbc.Button("Save Converted Code", id='save-converted-code-btn', color="primary", size="sm", className="w-100", style={'fontSize': '12px'})
                    ], width=6)
                ]),

                html.Div(id='conversion-status', className="mt-2 mb-2", style={'fontSize': '11px'}),
                html.Div(id='converted-code-display', style={'fontSize': '11px'}),
                html.Div(id='conversion-notes', className="mt-2", style={'fontSize': '11px'})
            ], style={'padding': '15px'})
        ])
    ])
], width=9)

# App Layout
app.layout = dbc.Container([
    header,
    dbc.Row([sidebar, main_panel])
], fluid=True)

# =============================================================================
# CALLBACKS
# =============================================================================

# Update variable dropdowns when customized data changes
@callback(
    [Output('y-variable-dropdown', 'options'),
     Output('x-variable-dropdown', 'options'),
     Output('hbar-variable-dropdown', 'options'),
     Output('keep-variables-dropdown', 'options'),
     Output('dataset-status-sidebar', 'children')],
    Input('customized-data-store', 'data')
)
def update_variable_choices(customized_data):
    """Update dropdown options based on customized data"""
    if customized_data is None or len(customized_data) == 0:
        empty_options = []
        status = html.P("No data available", style={'color': 'red', 'marginTop': '10px', 'fontSize': '9px'})
        return empty_options, empty_options, empty_options, empty_options, status

    df = pd.DataFrame(customized_data)
    options = [{'label': col, 'value': col} for col in df.columns]

    # No status display needed
    status = html.Div()

    return options, options, options, options, status

# Apply data customization
@callback(
    [Output('customized-data-store', 'data'),
     Output('customization-status', 'children'),
     Output('dataset-preview-table', 'children')],
    Input('apply-customization-btn', 'n_clicks'),
    [State('data-customization-textarea', 'value'),
     State('original-data-store', 'data')],
    prevent_initial_call=True
)
def apply_customization(n_clicks, customization_text, original_data):
    """Apply dataset customization using AI"""
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update

    original_df = pd.DataFrame(original_data)

    if not customization_text or not customization_text.strip():
        return original_data, dbc.Alert("No customization applied - using original dataset", color="info"), dash.no_update

    if not generator.ai_enabled:
        return original_data, dbc.Alert("AI not available. Please set ANTHROPIC_API_KEY environment variable.", color="danger"), dash.no_update

    try:
        # Use the same function from Shiny app
        processed_df = apply_dataset_customization(original_df, customization_text)

        if processed_df is not None and len(processed_df) > 0:
            status = dbc.Alert([
                html.I(className="bi bi-check-circle-fill me-2"),
                f"Customization applied successfully! Dataset: {len(original_df)} → {len(processed_df)} rows, {len(processed_df.columns)} columns"
            ], color="success")

            # Create table preview with pagination - 10 rows per page, all columns
            table_preview = html.Div([
                html.P(f"Shape: {len(processed_df)} rows × {len(processed_df.columns)} columns",
                       style={'fontSize': '11px', 'marginBottom': '5px'}),
                dbc.Table.from_dataframe(
                    processed_df.head(10),
                    striped=True,
                    bordered=True,
                    hover=True,
                    size='sm',
                    style={'fontSize': '10px', 'overflowX': 'auto'}
                ),
                html.P(f"Showing 10 of {len(processed_df)} rows. Scroll horizontally to see all {len(processed_df.columns)} columns.",
                       style={'fontSize': '11px', 'color': '#6c757d', 'marginTop': '5px'})
            ])

            return processed_df.to_dict('records'), status, table_preview
        else:
            return original_data, dbc.Alert("Customization failed or resulted in empty dataset. Using original data.", color="warning"), dash.no_update

    except Exception as e:
        return original_data, dbc.Alert(f"Customization error: {str(e)}", color="danger"), dash.no_update

# Reset to original data
@callback(
    [Output('customized-data-store', 'data', allow_duplicate=True),
     Output('data-customization-textarea', 'value'),
     Output('customization-status', 'children', allow_duplicate=True),
     Output('dataset-preview-table', 'children', allow_duplicate=True)],
    Input('reset-data-btn', 'n_clicks'),
    State('original-data-store', 'data'),
    prevent_initial_call=True
)
def reset_to_original(n_clicks, original_data):
    """Reset to original dataset"""
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    return original_data, "", dbc.Alert("Reset to original dataset", color="info"), html.Div()

# Generate validation report
@callback(
    [Output('validation-report-display', 'children'),
     Output('validation-report-store', 'data'),
     Output('generate-code-btn', 'disabled'),
     Output('customized-data-store', 'data', allow_duplicate=True)],
    Input('generate-validation-btn', 'n_clicks'),
    [State('customized-data-store', 'data'),
     State('y-variable-dropdown', 'value'),
     State('x-variable-dropdown', 'value'),
     State('hbar-variable-dropdown', 'value'),
     State('keep-variables-dropdown', 'value')],
    prevent_initial_call=True
)
def generate_validation_report(n_clicks, customized_data, y_var, x_var, hbar_var, keep_vars):
    """Generate validation report for user review and perform unique operation"""
    if n_clicks is None or not all([y_var, x_var, hbar_var]):
        return html.Div("Please select all required variables first", style={'color': 'orange', 'fontSize': '10px'}), None, True, dash.no_update

    df = pd.DataFrame(customized_data)

    # Create the keep columns list (required + additional)
    keep_columns = [y_var, x_var, hbar_var]
    if keep_vars:
        keep_columns.extend(keep_vars)
    # Remove duplicates while preserving order
    keep_columns = list(dict.fromkeys(keep_columns))

    # Perform unique operation on the dataset
    original_len = len(df)
    unique_df = df[keep_columns].drop_duplicates()
    unique_len = len(unique_df)

    print(f"Dataset after unique: {original_len} -> {unique_len} rows, keeping columns: {keep_columns}")

    # Get validation report from generator
    report = generator.get_validation_report(x_var, y_var, hbar_var, unique_df)

    # Build validation report display
    report_display = dbc.Card([
        dbc.CardBody([
            html.H6("Validation Report - Please Review", className="text-warning mb-2", style={'fontSize': '13px'}),

            html.Div([
                html.Strong("Data Summary:", style={'fontSize': '12px'}),
                html.P(f"Original Records: {original_len:,} → Unique Records: {unique_len:,}", style={'fontSize': '11px'}),
                html.P(f"Unique Subjects: {unique_df[y_var].nunique() if y_var in unique_df.columns else 'N/A'}", style={'fontSize': '11px'}),
                html.P(f"Kept Columns: {', '.join(keep_columns)}", style={'fontSize': '11px'})
            ], className="mb-2"),

            html.Div([
                html.Strong("Variables Selected for Plot:", style={'fontSize': '12px'}),
                html.Ul([
                    html.Li(f"Y-axis (Subjects): {y_var}", style={'fontSize': '11px'}),
                    html.Li(f"X-axis (Time): {x_var}", style={'fontSize': '11px'}),
                    html.Li(f"HBAR (Duration): {hbar_var}", style={'fontSize': '11px'})
                ], style={'fontSize': '11px'})
            ], className="mb-2"),

            dbc.Row([
                dbc.Col([
                    dbc.Button("Approve & Continue", id='approve-variables-btn', color="success", size="sm", className="w-100", style={'fontSize': '12px'})
                ], width=6),
                dbc.Col([
                    dbc.Button("Edit Variables", id='edit-variables-btn', color="secondary", size="sm", className="w-100", style={'fontSize': '12px'})
                ], width=6)
            ])
        ], style={'padding': '10px'})
    ], color="light", className="mb-2")

    # Return the unique dataset to replace customized data
    return report_display, report, True, unique_df.to_dict('records')

# Handle approval
@callback(
    [Output('validation-report-display', 'children', allow_duplicate=True),
     Output('generate-code-btn', 'disabled', allow_duplicate=True)],
    Input('approve-variables-btn', 'n_clicks'),
    prevent_initial_call=True
)
def approve_variables(n_clicks):
    """User approves validation report"""
    if n_clicks is None:
        return dash.no_update, dash.no_update

    return dbc.Alert("Variables approved! Ready to generate code.", color="success"), False

# Handle edit
@callback(
    Output('validation-report-display', 'children', allow_duplicate=True),
    Input('edit-variables-btn', 'n_clicks'),
    prevent_initial_call=True
)
def edit_variables(n_clicks):
    """User wants to edit variables"""
    if n_clicks is None:
        return dash.no_update

    return html.Div("Please adjust your variable selections above", style={'color': 'blue'})

# Generate code
@callback(
    [Output('generated-code-store', 'data'),
     Output('code-display', 'children'),
     Output('main-tabs', 'value')],
    Input('generate-code-btn', 'n_clicks'),
    [State('customized-data-store', 'data'),
     State('y-variable-dropdown', 'value'),
     State('x-variable-dropdown', 'value'),
     State('hbar-variable-dropdown', 'value'),
     State('graph-customization-textarea', 'value')],
    prevent_initial_call=True
)
def generate_code(n_clicks, customized_data, y_var, x_var, hbar_var, graph_customization):
    """Generate swimmer plot code"""
    if n_clicks is None or not all([y_var, x_var, hbar_var]):
        return dash.no_update, dash.no_update, dash.no_update

    df = pd.DataFrame(customized_data)

    try:
        # Generate code (data is already customized, so pass empty data_customization)
        code, info, status = generator.generate_swimmer_code(
            x_var, y_var, hbar_var,
            data_customization="",  # Empty since data is already customized
            graph_customization=graph_customization or "",
            sample_data=df
        )

        code_display = html.Div([
            html.H6("Generated Swimmer Plot Code:"),
            html.Pre(code, style={
                'backgroundColor': '#F5F5F5',
                'padding': '15px',
                'borderRadius': '5px',
                'maxHeight': '500px',
                'overflowY': 'auto'
            })
        ])

        return code, code_display, 'code-tab'

    except Exception as e:
        error_display = dbc.Alert(f"Code generation error: {str(e)}", color="danger")
        return None, error_display, 'code-tab'

# Execute code
@callback(
    [Output('execution-result-store', 'data'),
     Output('execution-status', 'children'),
     Output('swimmer-plot-display', 'children'),
     Output('main-tabs', 'value', allow_duplicate=True)],
    Input('execute-code-btn', 'n_clicks'),
    [State('generated-code-store', 'data'),
     State('customized-data-store', 'data')],
    prevent_initial_call=True
)
def execute_code(n_clicks, code, customized_data):
    """Execute the generated code"""
    if n_clicks is None or not code:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    df = pd.DataFrame(customized_data)

    # Execute code using generator's method
    result = generator.execute_code_safely(code, df)

    if result['success']:
        status = dbc.Alert("Execution successful", color="success")
        plot_display = html.Iframe(srcDoc=result.get('plotly_html', ''), style={'width': '100%', 'height': '800px', 'border': 'none'})
        return result, status, plot_display, 'results-tab'
    else:
        status = dbc.Alert([
            html.Strong("Execution failed:"),
            html.Pre(result.get('error', 'Unknown error'), style={'marginTop': '10px'})
        ], color="danger")
        return result, status, html.Div("Fix code errors and try again", style={'color': 'red'}), 'results-tab'

# Helper function for dataset customization (same as Shiny)
def apply_dataset_customization(data, customization_instructions):
    """Apply dataset-level customization using AI"""

    if not generator.ai_enabled:
        print("AI not available for dataset customization")
        return data

    print(f"Applying dataset customization with AI...")

    data_info = {
        'columns': list(data.columns),
        'shape': data.shape,
        'sample_values': {col: list(data[col].dropna().unique()[:3]) for col in data.columns[:8]}
    }

    prompt = f"""Apply dataset customizations to CDISC clinical trial data.

CURRENT DATASET: ADRS
- Columns: {data_info['columns']}
- Shape: {data_info['shape']}
- Sample values: {data_info['sample_values']}

CUSTOMIZATION INSTRUCTIONS:
{customization_instructions}

REQUIREMENTS:
1. Generate Python code that transforms the dataset
2. DataFrame name: cdisc_data (input) → customized_data (output)
3. Apply data transformations: filtering, merging, calculations, grouping, selections
4. If merging with ADSL, assume it's available as adsl_data
5. Handle missing data appropriately
6. Preserve key identifier columns (SUBJID, USUBJID)
7. End with: customized_data = [your final dataframe]

IMPORTANT: The final line MUST be: customized_data = [your_dataframe_variable_name]

Generate clean Python code for dataset transformation:"""

    try:
        message = generator.claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3500,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )

        customization_code = generator._clean_code(message.content[0].text.strip())
        print(f"Generated dataset customization code: {len(customization_code)} characters")

        # Execute dataset customization
        import numpy as np
        exec_globals = {
            'pd': pd, 'np': np,
            'cdisc_data': data.copy(),
            'adsl_data': ADSL_DATA.copy(),  # Make ADSL available for merging
            'print': print,
        }

        print("Executing dataset customization code...")
        exec(customization_code, exec_globals)

        if 'customized_data' in exec_globals:
            result = exec_globals['customized_data']
            print(f"Dataset customization successful: {len(data)} → {len(result)} rows")
            return result
        else:
            print("Dataset customization code did not produce 'customized_data' variable")
            return data

    except Exception as e:
        print(f"Dataset customization failed: {e}")
        return data

# Show debug button when execution fails
@callback(
    Output('debug-button-container', 'children'),
    Input('execution-result-store', 'data')
)
def show_debug_button(execution_result):
    """Show AI Debug button when code execution fails"""
    if execution_result and not execution_result.get('success') and generator.ai_enabled:
        return dbc.Button("AI Debug", id='debug-code-btn', color="danger", className="w-100")
    return html.Div()

# Debug code with AI
@callback(
    [Output('generated-code-store', 'data', allow_duplicate=True),
     Output('code-display', 'children', allow_duplicate=True),
     Output('execution-result-store', 'data', allow_duplicate=True)],
    Input('debug-code-btn', 'n_clicks'),
    [State('generated-code-store', 'data'),
     State('execution-result-store', 'data'),
     State('customized-data-store', 'data'),
     State('y-variable-dropdown', 'value'),
     State('x-variable-dropdown', 'value'),
     State('hbar-variable-dropdown', 'value')],
    prevent_initial_call=True
)
def debug_code(n_clicks, failed_code, execution_result, customized_data, y_var, x_var, hbar_var):
    """Debug failed code using AI"""
    if n_clicks is None or not failed_code or not execution_result:
        return dash.no_update, dash.no_update, dash.no_update

    if execution_result.get('success'):
        return dash.no_update, dash.no_update, dash.no_update

    error_msg = execution_result.get('error', 'Unknown error')
    df = pd.DataFrame(customized_data)

    print("Debugging code with AI...")

    try:
        # Use generator's debug method
        debugged_code, info, status = generator.debug_code(
            failed_code, error_msg, df, x_var, y_var, hbar_var
        )

        # Update code display
        code_display = html.Div([
            dbc.Alert("Code debugged by AI. Please try running again.", color="info", className="mb-3"),
            html.H6("Debugged Swimmer Plot Code:"),
            html.Pre(debugged_code, style={
                'backgroundColor': '#F5F5F5',
                'padding': '15px',
                'borderRadius': '5px',
                'maxHeight': '500px',
                'overflowY': 'auto'
            })
        ])

        # Clear execution result so user can try again
        return debugged_code, code_display, None

    except Exception as e:
        error_display = dbc.Alert(f"Debug error: {str(e)}", color="danger")
        return dash.no_update, error_display, dash.no_update

# Save code
@callback(
    Output('customization-status', 'children', allow_duplicate=True),
    Input('save-code-btn', 'n_clicks'),
    State('generated-code-store', 'data'),
    prevent_initial_call=True
)
def save_code(n_clicks, code):
    """Save generated code to file"""
    if n_clicks is None or not code:
        return dash.no_update

    result = generator.save_code(code)
    return dbc.Alert(f"Code saved: {result}", color="success")

# Interactive dialogue - send message
@callback(
    [Output('conversation-history-store', 'data'),
     Output('dialogue-input', 'value'),
     Output('generated-code-store', 'data', allow_duplicate=True),
     Output('code-display', 'children', allow_duplicate=True),
     Output('execution-result-store', 'data', allow_duplicate=True)],
    Input('send-dialogue-btn', 'n_clicks'),
    [State('dialogue-input', 'value'),
     State('generated-code-store', 'data'),
     State('conversation-history-store', 'data')],
    prevent_initial_call=True
)
def send_dialogue(n_clicks, user_input, generated_code, conversation_history):
    """Handle interactive dialogue for plot customization"""
    if n_clicks is None or not user_input or not user_input.strip():
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if not generator.ai_enabled:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if not generated_code:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    try:
        print(f"Processing dialogue request: {user_input[:50]}...")

        # Use generator's interactive customization method
        customized_code, info, status = generator.customize_plot_interactively(user_input)

        # Get updated conversation history
        current_history = generator.get_conversation_history()

        # Update code display
        code_display = html.Div([
            dbc.Alert("Code customized by AI. You can run it or make further changes.", color="success", className="mb-3"),
            html.H6("Customized Swimmer Plot Code:"),
            html.Pre(customized_code, style={
                'backgroundColor': '#F5F5F5',
                'padding': '15px',
                'borderRadius': '5px',
                'maxHeight': '500px',
                'overflowY': 'auto'
            })
        ])

        # Clear input and update stores
        return current_history, "", customized_code, code_display, None

    except Exception as e:
        print(f"Dialogue error: {e}")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Clear dialogue history
@callback(
    Output('conversation-history-store', 'data', allow_duplicate=True),
    Input('clear-dialogue-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_dialogue(n_clicks):
    """Clear conversation history"""
    if n_clicks is None:
        return dash.no_update

    generator.clear_conversation_history()
    return []

# Display conversation status
@callback(
    Output('conversation-status', 'children'),
    [Input('conversation-history-store', 'data'),
     Input('generated-code-store', 'data')]
)
def update_conversation_status(conversation_history, generated_code):
    """Update conversation status message"""
    if not generated_code:
        return dbc.Alert("Generate a swimmer plot first before using interactive customization", color="warning")

    if not generator.ai_enabled:
        return dbc.Alert("AI not available - check ANTHROPIC_API_KEY environment variable", color="danger")

    if not conversation_history or len(conversation_history) == 0:
        return dbc.Alert("Ready for interactive customization! Describe how you'd like to modify your plot.", color="info")

    return dbc.Alert(f"Conversation active: {len(conversation_history)} messages | Plot ready for further customization", color="success")

# Display dialogue history
@callback(
    Output('dialogue-history', 'children'),
    Input('conversation-history-store', 'data')
)
def update_dialogue_history(conversation_history):
    """Display conversation history"""
    if not conversation_history or len(conversation_history) == 0:
        return html.Div(
            "No conversation yet. Start by describing how you'd like to customize your swimmer plot!",
            style={'textAlign': 'center', 'color': '#6c757d', 'padding': '40px', 'fontStyle': 'italic'}
        )

    messages = []
    for msg in conversation_history:
        if msg['type'] == 'user':
            messages.append(
                html.Div([
                    html.Div("You:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div(msg['content']),
                    html.Div(msg['timestamp'].strftime("%H:%M:%S") if isinstance(msg.get('timestamp'), datetime) else str(msg.get('timestamp', '')),
                             style={'fontSize': '10px', 'opacity': '0.7', 'marginTop': '5px'})
                ], style={
                    'background': 'linear-gradient(45deg, #667eea, #764ba2)',
                    'color': 'white',
                    'marginLeft': 'auto',
                    'textAlign': 'right',
                    'marginBottom': '15px',
                    'padding': '10px 15px',
                    'borderRadius': '10px',
                    'maxWidth': '85%'
                })
            )
        else:
            messages.append(
                html.Div([
                    html.Div("AI Assistant:", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div(msg['content']),
                    html.Div(msg['timestamp'].strftime("%H:%M:%S") if isinstance(msg.get('timestamp'), datetime) else str(msg.get('timestamp', '')),
                             style={'fontSize': '10px', 'opacity': '0.7', 'marginTop': '5px'})
                ], style={
                    'background': '#e9ecef',
                    'color': '#333',
                    'marginRight': 'auto',
                    'borderLeft': '3px solid #007bff',
                    'marginBottom': '15px',
                    'padding': '10px 15px',
                    'borderRadius': '10px',
                    'maxWidth': '85%'
                })
            )

    return html.Div(messages)

# Code conversion - convert code
@callback(
    [Output('converted-code-display', 'children'),
     Output('conversion-status', 'children'),
     Output('conversion-notes', 'children'),
     Output('converted-code-store', 'data')],
    Input('convert-code-btn', 'n_clicks'),
    [State('generated-code-store', 'data'),
     State('conversion-language', 'value')],
    prevent_initial_call=True
)
def convert_code(n_clicks, python_code, target_language):
    """Convert Python code to R or SAS"""
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if not python_code:
        return (
            html.Div(f"No {target_language} code generated yet.", style={'color': 'gray', 'fontStyle': 'italic', 'padding': '20px'}),
            dbc.Alert("No Python code available for conversion. Generate a swimmer plot first.", color="warning"),
            html.Div(),
            None
        )

    if not generator.ai_enabled:
        return (
            html.Div(f"AI not available", style={'color': 'gray', 'fontStyle': 'italic', 'padding': '20px'}),
            dbc.Alert("AI not available for code conversion. Check ANTHROPIC_API_KEY.", color="danger"),
            html.Div(),
            None
        )

    print(f"Converting Python code to {target_language}...")

    try:
        # Use generator's code conversion method
        converted, status, notes = generator.convert_code_to_language(python_code, target_language)

        if status == "success":
            code_display = html.Div([
                html.H6(f"Generated {target_language} Code:"),
                html.Pre(converted, style={
                    'backgroundColor': '#F5F5F5',
                    'padding': '15px',
                    'borderRadius': '5px',
                    'maxHeight': '500px',
                    'overflowY': 'auto',
                    'border': '1px solid #dee2e6'
                })
            ])

            status_alert = dbc.Alert(f"Successfully converted to {target_language}", color="success")

            # Display notes
            if notes:
                notes_list = html.Ul([html.Li(note) for note in notes])
                notes_display = html.Div([
                    html.Strong(f"{target_language} Conversion Notes:"),
                    notes_list
                ], style={'background': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px'})
            else:
                notes_display = html.Div()

            return code_display, status_alert, notes_display, converted

        else:
            code_display = html.Div([
                html.H6(f"Conversion Failed:"),
                html.Pre(converted, style={'color': 'red'})
            ])
            status_alert = dbc.Alert(f"Conversion to {target_language} failed", color="danger")
            return code_display, status_alert, html.Div(), None

    except Exception as e:
        error_msg = f"Conversion error: {str(e)}"
        return (
            html.Div(f"# Error: {error_msg}", style={'color': 'red', 'padding': '20px'}),
            dbc.Alert("Conversion failed due to unexpected error", color="danger"),
            html.Div(),
            None
        )

# Save converted code
@callback(
    Output('conversion-status', 'children', allow_duplicate=True),
    Input('save-converted-code-btn', 'n_clicks'),
    [State('converted-code-store', 'data'),
     State('conversion-language', 'value')],
    prevent_initial_call=True
)
def save_converted_code(n_clicks, converted_code, language):
    """Save converted code to file"""
    if n_clicks is None or not converted_code:
        return dash.no_update

    try:
        result = generator.save_converted_code(converted_code, language)
        return dbc.Alert(f"Code saved: {result}", color="success")
    except Exception as e:
        return dbc.Alert(f"Save error: {str(e)}", color="danger")

# =============================================================================
# RUN APP
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=8050)
