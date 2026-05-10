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

# Sidebar — width=2
sidebar = dbc.Col([
    html.H6("CDISC Data", className="mb-2", style={'fontSize': '12px'}),

    dbc.Card([
        dbc.CardBody([
            html.P("ADSL", className="text-primary mb-1", style={'fontSize': '11px', 'fontWeight': 'bold'}),
            html.P([
                html.Strong("Rows: ", style={'fontSize': '10px'}), html.Span(f"{len(ADSL_DATA):,}", style={'fontSize': '10px'}),
                html.Br(),
                html.Strong("Vars: ", style={'fontSize': '10px'}), html.Span(f"{len(ADSL_DATA.columns):,}", style={'fontSize': '10px'})
            ], className="mb-0")
        ], style={'padding': '6px'})
    ], className="mb-1"),

    dbc.Card([
        dbc.CardBody([
            html.P("ADRS", className="text-primary mb-1", style={'fontSize': '11px', 'fontWeight': 'bold'}),
            html.P([
                html.Strong("Rows: ", style={'fontSize': '10px'}), html.Span(f"{len(ADRS_DATA):,}", style={'fontSize': '10px'}),
                html.Br(),
                html.Strong("Vars: ", style={'fontSize': '10px'}), html.Span(f"{len(ADRS_DATA.columns):,}", style={'fontSize': '10px'})
            ], className="mb-0")
        ], style={'padding': '6px'})
    ], className="mb-2"),

    html.Hr(style={'margin': '6px 0'}),

    # ── Filter box: ADSL ─────────────────────────────
    dbc.Card([
        dbc.CardBody([
            html.P("Filter ADSL", className="text-secondary mb-1",
                   style={'fontSize': '10px', 'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='adsl-filter-var',
                options=[{'label': c, 'value': c} for c in ADSL_DATA.columns],
                placeholder="Select variable...",
                clearable=True,
                style={'fontSize': '10px'}
            ),
            html.Div(id='adsl-filter-values', className="mt-1")
        ], style={'padding': '6px'})
    ], className="mb-1"),

    # ── Filter box: ADRS ─────────────────────────────
    dbc.Card([
        dbc.CardBody([
            html.P("Filter ADRS", className="text-secondary mb-1",
                   style={'fontSize': '10px', 'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='adrs-filter-var',
                options=[{'label': c, 'value': c} for c in ADRS_DATA.columns],
                placeholder="Select variable...",
                clearable=True,
                style={'fontSize': '10px'}
            ),
            html.Div(id='adrs-filter-values', className="mt-1")
        ], style={'padding': '6px'})
    ], className="mb-2"),

    html.Div(id='dataset-status-sidebar')

], width=2, style={
    'backgroundColor': '#F5F5F5',
    'padding': '10px',
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

    # Global spinner — visible whenever any long operation is running
    dcc.Loading(
        id="global-spinner",
        type="circle",
        color="#0d6efd",
        fullscreen=True,
        style={"backgroundColor": "rgba(255,255,255,0.6)"},
        children=html.Div(id="spinner-trigger", style={"display": "none"})
    ),

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
                        dcc.Dropdown(id='y-variable-dropdown', placeholder="Select subject ID...", className="mb-2", style={'fontSize': '12px'})
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

                html.Label("Overlay Marker (Optional):", style={'fontSize': '12px', 'marginTop': '2px'}),
                dcc.Dropdown(
                    id='overlay-marker-dropdown',
                    placeholder="Select overlay variable (scatter on X-axis timepoints)...",
                    multi=False,
                    clearable=True,
                    className="mb-1",
                    style={'fontSize': '12px'}
                ),
                html.P(
                    "Character string variable — plotted as scatter markers at X-axis timepoints, aligned to Y-axis subjects.",
                    style={'fontSize': '11px', 'color': '#6c757d', 'marginBottom': '10px'}
                ),

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
                    ], width=10),
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
     Output('overlay-marker-dropdown', 'options'),
     Output('dataset-status-sidebar', 'children')],
    Input('customized-data-store', 'data')
)
def update_variable_choices(customized_data):
    """Update dropdown options based on customized data.
    Y-axis is restricted to SUBJID / USUBJID (subject identifier columns only).
    """
    if customized_data is None or len(customized_data) == 0:
        empty = []
        status = html.P("No data available", style={'color': 'red', 'marginTop': '10px', 'fontSize': '9px'})
        return empty, empty, empty, empty, empty, status

    df = pd.DataFrame(customized_data)
    all_options = [{'label': col, 'value': col} for col in df.columns]

    # Y-axis: ONLY SUBJID or USUBJID — no fallback, must be a subject identifier
    subj_cols = [c for c in df.columns if c in ('SUBJID', 'USUBJID')]
    y_options = [{'label': c, 'value': c} for c in subj_cols]
    # If neither present the dropdown will be empty — user sees no valid choice
    # and cannot proceed, which is the correct behaviour

    # Overlay: character/object columns make sense as scatter category variable
    # (exclude numeric-only cols but keep all for flexibility)
    overlay_options = [{'label': col, 'value': col} for col in df.columns]

    return y_options, all_options, all_options, all_options, overlay_options, html.Div()

# Apply data customization
@callback(
    [Output('customized-data-store', 'data'),
     Output('customization-status', 'children'),
     Output('dataset-preview-table', 'children'),
     Output('spinner-trigger', 'children', allow_duplicate=True)],
    Input('apply-customization-btn', 'n_clicks'),
    [State('data-customization-textarea', 'value'),
     State('original-data-store', 'data')],
    prevent_initial_call=True
)
def apply_customization(n_clicks, customization_text, original_data):
    """Apply dataset customization using AI.
    Runs on full ADRS + ADSL with no column filtering.
    ALL columns (original + merged + derived) are returned so the
    user can see and select derived columns in Step 2 dropdowns.
    Column selection and drop_duplicates happen in generate_validation_report.
    """
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    original_df = pd.DataFrame(original_data)

    if not customization_text or not customization_text.strip():
        return original_data, dbc.Alert("No customization applied - using original dataset", color="info"), dash.no_update, dash.no_update

    if not generator.ai_enabled:
        return original_data, dbc.Alert("AI not available. Please set ANTHROPIC_API_KEY environment variable.", color="danger"), dash.no_update, dash.no_update

    try:
        processed_df = generator.data_customizer.apply_data_customizations(
            sample_data=original_df,
            data_customization=customization_text,
            x_var='',
            y_var='',
            hbar_var='',
            adsl_data=ADSL_DATA,
        )

        if processed_df is not None and len(processed_df) > 0:
            status = dbc.Alert([
                html.I(className="bi bi-check-circle-fill me-2"),
                f"Customization applied! Dataset: {len(original_df)} → {len(processed_df)} rows, {len(processed_df.columns)} columns. Now select your plot variables in Step 2."
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
                html.P(f"Showing 10 of {len(processed_df)} rows — includes all original, merged, and derived columns.",
                       style={'fontSize': '11px', 'color': '#6c757d', 'marginTop': '5px'})
            ])

            return processed_df.to_dict('records'), status, table_preview, dash.no_update
        else:
            return original_data, dbc.Alert("Customization failed or resulted in empty dataset. Using original data.", color="warning"), dash.no_update, dash.no_update

    except Exception as e:
        return original_data, dbc.Alert(f"Customization error: {str(e)}", color="danger"), dash.no_update, dash.no_update

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

    # Hard guard — Y must be a recognised subject identifier
    if y_var not in ('SUBJID', 'USUBJID'):
        return dbc.Alert(
            f"Y-axis must be SUBJID or USUBJID — '{y_var}' is not a valid subject identifier.",
            color="danger"
        ), None, True, dash.no_update

    df = pd.DataFrame(customized_data)

    # Create the keep columns list (required + additional selected by user)
    keep_columns = [y_var, x_var, hbar_var]
    if keep_vars:
        keep_columns.extend(keep_vars)
    keep_columns = list(dict.fromkeys(keep_columns))

    # Also retain any derived columns that exist in df but were not in the
    # original ADRS schema — these were created by the data customizer and
    # must survive so the user can see and select them in the dropdowns.
    original_adrs_cols = set(ADRS_DATA.columns)
    derived_cols = [c for c in df.columns
                    if c not in original_adrs_cols and c not in keep_columns]
    final_columns = keep_columns + derived_cols

    # Perform unique operation on the dataset
    original_len = len(df)
    unique_df = df[final_columns].drop_duplicates()
    unique_len = len(unique_df)

    print(f"Dataset after unique: {original_len} -> {unique_len} rows, keeping columns: {keep_columns}")

    # ── Run data_validator standards checks against the processed data ──────────
    validation = generator.data_validator.validate_all(
        unique_df, x_var, y_var, hbar_var
    )
    has_errors   = not validation["valid"]
    errors       = validation["errors"]
    warnings     = validation["warnings"]

    # ── Get derivation metadata from customizer ────────────────────────────────
    report = generator.get_validation_report(x_var, y_var, hbar_var, unique_df)

    # ── Build combined validation report display ───────────────────────────────

    # Section 1 — data summary
    data_summary = html.Div([
        html.Strong("Data Summary:", style={'fontSize': '12px'}),
        html.P(f"Original Records: {original_len:,} → Unique Records: {unique_len:,}", style={'fontSize': '11px'}),
        html.P(f"Unique Subjects: {unique_df[y_var].nunique() if y_var in unique_df.columns else 'N/A'}", style={'fontSize': '11px'}),
        html.P(f"Columns in plot dataset: {', '.join(final_columns)}", style={'fontSize': '11px'})
    ], className="mb-2")

    # Section 2 — variable selections
    var_summary = html.Div([
        html.Strong("Variables Selected for Plot:", style={'fontSize': '12px'}),
        html.Ul([
            html.Li(f"Y-axis (Subjects): {y_var}", style={'fontSize': '11px'}),
            html.Li(f"X-axis (Time): {x_var}", style={'fontSize': '11px'}),
            html.Li(f"HBAR (Duration): {hbar_var}", style={'fontSize': '11px'})
        ])
    ], className="mb-2")

    # Section 3 — standards checks (errors + warnings)
    if errors:
        error_block = html.Div([
            html.Strong("❌ Standards Violations — must fix before generating:", style={'fontSize': '12px', 'color': '#dc3545'}),
            html.Ul([html.Li(e, style={'fontSize': '11px', 'color': '#dc3545'}) for e in errors])
        ], className="mb-2")
    else:
        error_block = html.Div(
            "✅ All standards checks passed.",
            style={'fontSize': '11px', 'color': '#198754', 'marginBottom': '8px'}
        )

    if warnings:
        warning_block = html.Div([
            html.Strong("⚠ Warnings (can still generate):", style={'fontSize': '12px', 'color': '#856404'}),
            html.Ul([html.Li(w, style={'fontSize': '11px', 'color': '#856404'}) for w in warnings])
        ], className="mb-2")
    else:
        warning_block = html.Div()

    # Section 4 — approve/edit buttons
    # Approve is disabled if there are standards errors
    action_row = dbc.Row([
        dbc.Col([
            dbc.Button(
                "Approve & Continue",
                id='approve-variables-btn',
                color="success" if not has_errors else "secondary",
                size="sm",
                className="w-100",
                disabled=has_errors,
                style={'fontSize': '12px'}
            )
        ], width=6),
        dbc.Col([
            dbc.Button("Edit Variables", id='edit-variables-btn', color="secondary", size="sm", className="w-100", style={'fontSize': '12px'})
        ], width=6)
    ])

    header_color = "danger" if has_errors else ("warning" if warnings else "success")
    header_text  = (
        "Validation Report — Fix errors before continuing" if has_errors
        else ("Validation Report — Warnings present, review before continuing" if warnings
              else "Validation Report — All checks passed")
    )

    report_display = dbc.Card([
        dbc.CardBody([
            html.H6(header_text, className=f"text-{header_color} mb-2", style={'fontSize': '13px'}),
            data_summary,
            var_summary,
            error_block,
            warning_block,
            action_row
        ], style={'padding': '10px'})
    ], color="light", className="mb-2")

    # Enable Generate button only if no standards errors
    return report_display, report, has_errors, unique_df.to_dict('records')

# Handle approval — button already enabled by validate step if no errors
# This callback just gives visual confirmation
@callback(
    Output('validation-report-display', 'children', allow_duplicate=True),
    Input('approve-variables-btn', 'n_clicks'),
    prevent_initial_call=True
)
def approve_variables(n_clicks):
    """User confirms approval"""
    if n_clicks is None:
        return dash.no_update
    return dbc.Alert("✅ Approved — Generate Swimmer Plot is ready.", color="success")

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
     Output('main-tabs', 'value'),
     Output('spinner-trigger', 'children', allow_duplicate=True)],
    Input('generate-code-btn', 'n_clicks'),
    [State('customized-data-store', 'data'),
     State('y-variable-dropdown', 'value'),
     State('x-variable-dropdown', 'value'),
     State('hbar-variable-dropdown', 'value'),
     State('graph-customization-textarea', 'value'),
     State('overlay-marker-dropdown', 'value')],
    prevent_initial_call=True
)
def generate_code(n_clicks, customized_data, y_var, x_var, hbar_var, graph_customization, overlay_marker):
    """Generate swimmer plot code"""
    if n_clicks is None or not all([y_var, x_var, hbar_var]):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    df = pd.DataFrame(customized_data)

    # Append overlay instruction to graph customization if selected
    graph_custom_full = graph_customization or ""
    if overlay_marker:
        overlay_instruction = (
            f"\nOverlay the variable '{overlay_marker}' as scatter markers. "
            f"Use x=data['{overlay_marker}'] for X-position and y=data['{y_var}'] for Y-position. "
            f"Show one marker per row where '{overlay_marker}' is not null. "
            f"Color/symbol by unique values of '{overlay_marker}'."
        )
        graph_custom_full = graph_custom_full + overlay_instruction

    try:
        # Generate code (data is already customized, so pass empty data_customization)
        code, info, status = generator.generate_swimmer_code(
            x_var, y_var, hbar_var,
            data_customization="",  # Empty since data is already customized
            graph_customization=graph_custom_full,
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

        return code, code_display, 'code-tab', dash.no_update

    except Exception as e:
        error_display = dbc.Alert(f"Code generation error: {str(e)}", color="danger")
        return None, error_display, 'code-tab', dash.no_update

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


# ── Sidebar filter: show unique values for ADSL variable ────────────────────
@callback(
    Output('adsl-filter-values', 'children'),
    Input('adsl-filter-var', 'value'),
    prevent_initial_call=True
)
def show_adsl_filter_values(var):
    """Show unique values for selected ADSL variable"""
    if not var:
        return html.Div()
    vals = sorted(ADSL_DATA[var].dropna().unique().tolist())
    return html.Div([
        html.P(f"{len(vals)} unique values:", style={'fontSize': '9px', 'color': '#6c757d', 'marginBottom': '2px'}),
        html.Div(
            ", ".join(str(v) for v in vals[:30]) + ("..." if len(vals) > 30 else ""),
            style={'fontSize': '9px', 'color': '#333', 'wordBreak': 'break-word',
                   'background': '#fff', 'border': '1px solid #dee2e6',
                   'borderRadius': '3px', 'padding': '3px'}
        )
    ])

# ── Sidebar filter: show unique values for ADRS variable ────────────────────
@callback(
    Output('adrs-filter-values', 'children'),
    Input('adrs-filter-var', 'value'),
    prevent_initial_call=True
)
def show_adrs_filter_values(var):
    """Show unique values for selected ADRS variable"""
    if not var:
        return html.Div()
    vals = sorted(ADRS_DATA[var].dropna().unique().tolist())
    return html.Div([
        html.P(f"{len(vals)} unique values:", style={'fontSize': '9px', 'color': '#6c757d', 'marginBottom': '2px'}),
        html.Div(
            ", ".join(str(v) for v in vals[:30]) + ("..." if len(vals) > 30 else ""),
            style={'fontSize': '9px', 'color': '#333', 'wordBreak': 'break-word',
                   'background': '#fff', 'border': '1px solid #dee2e6',
                   'borderRadius': '3px', 'padding': '3px'}
        )
    ])

# =============================================================================
# RUN APP
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=8050, use_reloader=False)
