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
# ── Shared style tokens ───────────────────────────────────────────────────────
CARD_STYLE   = {'border': '1px solid #e0e4ea', 'borderRadius': '8px', 'backgroundColor': '#fff'}
SECTION_HEAD = {'fontSize': '11px', 'fontWeight': '600', 'color': '#374151',
                'textTransform': 'uppercase', 'letterSpacing': '0.06em', 'marginBottom': '10px'}
LABEL_STYLE  = {'fontSize': '12px', 'color': '#4b5563', 'marginBottom': '4px', 'display': 'block'}
HINT_STYLE   = {'fontSize': '11px', 'color': '#9ca3af', 'marginTop': '3px', 'marginBottom': '8px'}
STEP_BADGE   = lambda n, title: html.Div([
    html.Span(str(n), style={
        'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center',
        'width': '22px', 'height': '22px', 'borderRadius': '50%',
        'backgroundColor': '#2563eb', 'color': '#fff',
        'fontSize': '11px', 'fontWeight': '700', 'marginRight': '8px', 'flexShrink': '0'
    }),
    html.Span(title, style={'fontSize': '13px', 'fontWeight': '600', 'color': '#1e3a5f'})
], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '12px'})

# ── Custom CSS injected via index_string override ──────────────────────────────
app.index_string = """
<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
  body { background: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  .main-card { background:#fff; border:1px solid #e0e4ea; border-radius:10px; box-shadow:0 1px 4px rgba(0,0,0,.06); }

  /* Tab pill bar */
  .pill-tabs .tab-bar { display:flex; gap:6px; padding:8px 12px;
    background:#f8fafc; border-bottom:1px solid #e0e4ea; border-radius:10px 10px 0 0; flex-wrap:wrap; }
  .pill-tabs .tab-btn { padding:6px 16px; border-radius:20px; border:1px solid transparent;
    font-size:12px; font-weight:500; color:#6b7280; background:transparent; cursor:pointer;
    transition:all .15s; white-space:nowrap; }
  .pill-tabs .tab-btn:hover { background:#e9eef6; color:#2563eb; }
  .pill-tabs .tab-btn.active { background:#2563eb; color:#fff; border-color:#2563eb; }
  .pill-tabs .tab-content { padding:20px; }

  /* Step cards */
  .step-card { border:1px solid #e5e9f0; border-radius:8px; padding:16px; margin-bottom:14px; background:#fafbfd; }
  .step-card:last-child { margin-bottom:0; }

  /* Dataset info strip */
  .ds-strip { display:flex; gap:10px; flex-wrap:wrap; }
  .ds-chip { background:#f0f4ff; border:1px solid #c7d7f9; border-radius:6px;
    padding:6px 12px; font-size:11px; color:#1e40af; }
  .ds-chip strong { font-weight:600; }

  /* Sidebar info box */
  .info-box { background:#f8fafc; border:1px solid #e0e4ea; border-radius:8px; padding:10px 14px; margin-bottom:12px; }

  /* Dash tab hiding — we control visibility manually */
  .custom-tab { display:none !important; }
  .custom-tab.active-tab { display:block !important; }
  
  /* Override default Dash tab styles to be invisible */
  .js-plotly-plot .plotly .cursor-crosshair { cursor: crosshair; }
</style>
</head>
<body>{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
"""

# ── Header ─────────────────────────────────────────────────────────────────────
header = html.Div(
    html.Div([
        html.Span("⬡", style={'fontSize': '20px', 'color': '#60a5fa', 'marginRight': '10px'}),
        html.Span("Clinical Trials Swimmer Plot Generator",
                  style={'fontSize': '16px', 'fontWeight': '700', 'color': '#fff', 'letterSpacing': '0.02em'}),
        html.Span("CDISC · Oncology", style={
            'fontSize': '11px', 'color': '#93c5fd', 'marginLeft': '14px',
            'border': '1px solid #3b82f6', 'borderRadius': '12px', 'padding': '2px 10px'
        }),
    ], style={'display': 'flex', 'alignItems': 'center', 'padding': '12px 24px'}),
    style={'background': 'linear-gradient(90deg,#1e3a5f 0%,#2563eb 100%)',
           'marginBottom': '16px', 'borderRadius': '0 0 8px 8px', 'boxShadow': '0 2px 8px rgba(37,99,235,.25)'}
)



# ── Tab contents ───────────────────────────────────────────────────────────────

tab_data_prep = html.Div([

    # Dataset info bar
    html.Div([
        html.Div([
            html.Span("ADSL", style={'fontWeight': '600', 'color': '#1e40af', 'marginRight': '4px', 'fontSize': '11px'}),
            html.Span(f"{len(ADSL_DATA):,} rows · {len(ADSL_DATA.columns)} vars", style={'fontSize': '10px', 'color': '#6b7280'}),
            html.Span("  |  ", style={'color': '#d1d5db', 'fontSize': '10px'}),
            html.Span("ADRS", style={'fontWeight': '600', 'color': '#1e40af', 'marginRight': '4px', 'fontSize': '11px'}),
            html.Span(f"{len(ADRS_DATA):,} rows · {len(ADRS_DATA.columns)} vars", style={'fontSize': '10px', 'color': '#6b7280'}),
        ], style={'marginRight': '16px', 'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '2px'}),
        html.Div([
            html.Span("Explore:", style={'fontSize': '10px', 'color': '#6b7280', 'marginRight': '4px', 'whiteSpace': 'nowrap'}),
            html.Span("ADSL", style={'fontSize': '10px', 'fontWeight': '600', 'color': '#374151', 'marginRight': '3px'}),
            dcc.Dropdown(id='adsl-filter-var',
                options=[{'label': c, 'value': c} for c in ADSL_DATA.columns],
                placeholder="variable…", clearable=True,
                style={'fontSize': '10px', 'width': '130px', 'display': 'inline-block', 'marginRight': '6px'}),
            html.Span("ADRS", style={'fontSize': '10px', 'fontWeight': '600', 'color': '#374151', 'marginRight': '3px'}),
            dcc.Dropdown(id='adrs-filter-var',
                options=[{'label': c, 'value': c} for c in ADRS_DATA.columns],
                placeholder="variable…", clearable=True,
                style={'fontSize': '10px', 'width': '130px', 'display': 'inline-block'}),
        ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '2px'}),
        html.Div(id='dataset-status-sidebar'),
    ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '8px',
              'padding': '6px 10px', 'marginBottom': '10px',
              'background': '#f8fafc', 'border': '1px solid #e5e9f0', 'borderRadius': '6px'}),
    html.Div([
        html.Div(id='adsl-filter-values', style={'fontSize': '10px', 'color': '#6b7280'}),
        html.Div(id='adrs-filter-values', style={'fontSize': '10px', 'color': '#6b7280'}),
    ], id='explore-results', style={'marginBottom': '8px'}),

    # Step 1
    html.Div([
        STEP_BADGE(1, "Data Customization"),
        html.P("Describe any dataset transformations in plain English (optional).", style=HINT_STYLE),
        dcc.Textarea(
            id='data-customization-textarea',
            placeholder="e.g. derive DURATION as days from STARTDT to ENDDT; left-join ADSL to bring in TRT01P",
            style={'width': '100%', 'height': '56px', 'fontSize': '12px',
                   'border': '1px solid #d1d5db', 'borderRadius': '6px', 'resize': 'vertical', 'padding': '8px'},
            className="mb-2"
        ),
        dbc.Row([
            dbc.Col(dbc.Button("Apply", id='apply-customization-btn', color="primary", size="sm",
                               className="w-100", style={'fontSize': '12px', 'borderRadius': '6px'}), width=3),
            dbc.Col(dbc.Button("Reset", id='reset-data-btn', outline=True, color="secondary", size="sm",
                               className="w-100", style={'fontSize': '12px', 'borderRadius': '6px'}), width=3),
        ], className="mb-2"),
        html.Div(id='customization-status', style={'fontSize': '11px'}),
        html.Div([
            html.Span("Dataset Preview", style={'fontSize': '11px', 'fontWeight': '600', 'color': '#374151'}),
        ], style={'marginTop': '12px', 'marginBottom': '6px'}),
        html.Div(
            id='dataset-preview-table',
            style={'maxHeight': '220px', 'overflowY': 'auto', 'overflowX': 'auto',
                   'border': '1px solid #e5e9f0', 'borderRadius': '6px', 'padding': '4px'}
        ),
    ], className="step-card"),

    # Step 2
    html.Div([
        STEP_BADGE(2, "Swimmer Plot Variables"),
        dbc.Row([
            dbc.Col([
                html.Label("Y-axis — subjects", style=LABEL_STYLE),
                dcc.Dropdown(id='y-variable-dropdown', placeholder="SUBJID / USUBJID",
                             style={'fontSize': '12px'})
            ], width=4),
            dbc.Col([
                html.Label("X-axis — time", style=LABEL_STYLE),
                dcc.Dropdown(id='x-variable-dropdown', placeholder="Select time variable",
                             style={'fontSize': '12px'})
            ], width=4),
            dbc.Col([
                html.Label("HBAR — duration", style=LABEL_STYLE),
                dcc.Dropdown(id='hbar-variable-dropdown', placeholder="Select duration",
                             style={'fontSize': '12px'})
            ], width=4),
        ], className="mb-3"),
        html.Label("Additional variables to keep", style=LABEL_STYLE),
        dcc.Dropdown(id='keep-variables-dropdown',
                     placeholder="Select additional variables to pass to the graph",
                     multi=True, className="mb-1", style={'fontSize': '12px'}),
        html.P("Included in the dataset passed to the graph generator.", style=HINT_STYLE),
        html.Label("Overlay marker (optional)", style=LABEL_STYLE),
        dcc.Dropdown(id='overlay-marker-dropdown',
                     placeholder="Categorical variable — scatter markers at X-axis timepoints",
                     multi=False, clearable=True, className="mb-1", style={'fontSize': '12px'}),
        html.P("Character column — one marker per row, coloured by unique values.", style=HINT_STYLE),
        dbc.Button("Generate Validation Report", id='generate-validation-btn',
                   color="primary", size="sm",
                   style={'fontSize': '12px', 'borderRadius': '6px', 'width': '100%', 'marginTop': '4px'}),
        html.Div(id='validation-report-display', style={'marginTop': '12px'}),
    ], className="step-card"),

    # Step 3
    html.Div([
        STEP_BADGE(3, "Graph Customization"),
        html.P("Describe visual styling in plain English (optional).", style=HINT_STYLE),
        dcc.Textarea(
            id='graph-customization-textarea',
            placeholder="e.g. colour bars by treatment arm, add end-of-study markers, bold axis labels",
            style={'width': '100%', 'height': '56px', 'fontSize': '12px',
                   'border': '1px solid #d1d5db', 'borderRadius': '6px', 'resize': 'vertical', 'padding': '8px'},
            className="mb-2"
        ),
        dbc.Button("Generate Swimmer Plot", id='generate-code-btn',
                   color="success", size="sm", disabled=True,
                   style={'fontSize': '12px', 'borderRadius': '6px', 'width': '100%',
                          'fontWeight': '600', 'letterSpacing': '0.02em'}),
    ], className="step-card"),

], style={'padding': '4px'})

tab_code = html.Div([
    html.Div([
        html.Span("Generated Python Code", style=SECTION_HEAD),
        html.Div(id='code-display', style={'fontSize': '11px', 'marginBottom': '10px'}),
        dbc.Row([
            dbc.Col(dbc.Button("▶  Run", id='execute-code-btn', color="success", size="sm",
                               className="w-100", style={'fontSize': '12px', 'borderRadius': '6px'}), width=2),
            dbc.Col(dbc.Button("⬇  Save", id='save-code-btn', color="primary", size="sm",
                               className="w-100", style={'fontSize': '12px', 'borderRadius': '6px'}), width=2),
            dbc.Col(html.Div(id='debug-button-container'), width=3),
        ], className="mb-2"),
        html.Div(id='save-code-status', style={'fontSize': '11px'}),
    ], className="step-card"),

    html.Div([
        html.Span("Convert to R or SAS", style=SECTION_HEAD),
        html.P("Auto-saves after conversion.", style=HINT_STYLE),
        dbc.Row([
            dbc.Col(dbc.RadioItems(
                id='conversion-language',
                options=[{'label': 'R  (plotly · WebGL)', 'value': 'R'},
                         {'label': 'SAS  (GTL)', 'value': 'SAS'}],
                value='R', inline=True,
                style={'fontSize': '12px'}
            ), width=8),
            dbc.Col(dbc.Button("Convert", id='convert-code-btn', color="primary", size="sm",
                               className="w-100", style={'fontSize': '12px', 'borderRadius': '6px'}), width=2),
        ], className="mb-2"),
        html.Div(id='conversion-status', style={'fontSize': '11px', 'marginBottom': '6px'}),
        html.Div(id='conversion-notes', style={'fontSize': '11px', 'marginBottom': '6px'}),
        html.Div(id='converted-code-display', style={'fontSize': '11px'}),
    ], className="step-card"),
], style={'padding': '4px'})

tab_results = html.Div([
    html.Div([
        html.Span("Execution Status", style=SECTION_HEAD),
        html.Div(id='execution-status', style={'fontSize': '11px'}),
    ], className="step-card"),
    html.Div([
        html.Span("Swimmer Plot", style=SECTION_HEAD),
        html.Div(id='swimmer-plot-display'),
    ], className="step-card"),
], style={'padding': '4px'})

tab_dialogue = html.Div([
    html.Div([
        html.Div(id='conversation-status', style={'fontSize': '11px', 'marginBottom': '10px'}),
        html.Div([
            html.Span("💡 ", style={'marginRight': '4px'}),
            html.Span("Use ", style={'fontSize': '11px'}),
            html.Code("VAR:columnname", style={'fontSize': '11px', 'backgroundColor': '#f0f4ff',
                      'padding': '1px 5px', 'borderRadius': '3px', 'color': '#2563eb'}),
            html.Span(" to reference dataset columns  (e.g. 'overlay VAR:EOSDY as markers')",
                      style={'fontSize': '11px'}),
        ], style={'padding': '8px 12px', 'backgroundColor': '#eff6ff', 'borderRadius': '6px',
                  'border': '1px solid #bfdbfe', 'marginBottom': '10px'}),
        html.Div(id='dialogue-history', style={
            'height': '320px', 'overflowY': 'auto',
            'border': '1px solid #e5e9f0', 'borderRadius': '8px',
            'padding': '10px', 'background': '#fafbfd',
            'marginBottom': '10px', 'fontSize': '11px'
        }),
        dbc.Row([
            dbc.Col(dcc.Textarea(
                id='dialogue-input',
                placeholder="Describe a change… (e.g. 'make bars teal, overlay VAR:EOSDY as triangles')",
                style={'width': '100%', 'height': '60px', 'fontSize': '12px',
                       'border': '1px solid #d1d5db', 'borderRadius': '6px', 'padding': '8px'},
            ), width=9),
            dbc.Col([
                dbc.Button("Send", id='send-dialogue-btn', color="primary", size="sm",
                           className="w-100 mb-2", style={'fontSize': '12px', 'borderRadius': '6px'}),
                dbc.Button("Clear", id='clear-dialogue-btn', outline=True, color="secondary", size="sm",
                           className="w-100", style={'fontSize': '12px', 'borderRadius': '6px'}),
            ], width=3),
        ]),
    ], className="step-card"),
], style={'padding': '4px'})

# ── Main panel (full width, no sidebar) ───────────────────────────────────────
main_panel = html.Div([
    # Hidden stores
    dcc.Store(id='original-data-store',      storage_type='memory', data=ADRS_DATA.to_dict('records')),
    dcc.Store(id='customized-data-store',    storage_type='memory', data=ADRS_DATA.to_dict('records')),
    dcc.Store(id='generated-code-store',     storage_type='memory'),
    dcc.Store(id='validation-report-store',  storage_type='memory'),
    dcc.Store(id='execution-result-store',   storage_type='memory'),
    dcc.Store(id='conversation-history-store', storage_type='memory', data=[]),
    dcc.Store(id='converted-code-store',     storage_type='memory'),
    dcc.Store(id='active-tab-store',         storage_type='memory', data='data-tab'),

    dcc.Loading(id="global-spinner", type="circle", color="#2563eb", fullscreen=True,
                style={"backgroundColor": "rgba(255,255,255,0.7)"},
                children=html.Div(id="spinner-trigger", style={"display": "none"})),

    # Tab pill bar + content card
    html.Div([
        # Pill tab bar
        html.Div([
            html.Button("Data Preparation",      id='tab-btn-data',     n_clicks=0,
                        className="tab-btn active", **{'data-tab': 'data-tab'}),
            html.Button("Generated Code",         id='tab-btn-code',     n_clicks=0,
                        className="tab-btn",        **{'data-tab': 'code-tab'}),
            html.Button("Swimmer Plot Results",   id='tab-btn-results',  n_clicks=0,
                        className="tab-btn",        **{'data-tab': 'results-tab'}),
            html.Button("Interactive Customization", id='tab-btn-dialogue', n_clicks=0,
                        className="tab-btn",        **{'data-tab': 'dialogue-tab'}),
        ], className="tab-bar"),

        # Hidden dcc.Tabs for callback compatibility
        dcc.Tabs(id='main-tabs', value='data-tab', style={'display': 'none'}, children=[
            dcc.Tab(label='Data Preparation',        value='data-tab'),
            dcc.Tab(label='Generated Code',          value='code-tab'),
            dcc.Tab(label='Swimmer Plot Results',    value='results-tab'),
            dcc.Tab(label='Interactive Customization', value='dialogue-tab'),
        ]),

        # Tab content panels
        html.Div([
            html.Div(tab_data_prep,  id='panel-data-tab',    style={'display': 'block'}),
            html.Div(tab_code,       id='panel-code-tab',    style={'display': 'none'}),
            html.Div(tab_results,    id='panel-results-tab', style={'display': 'none'}),
            html.Div(tab_dialogue,   id='panel-dialogue-tab',style={'display': 'none'}),
        ], className="tab-content"),

    ], className="main-card pill-tabs"),

], style={'padding': '0 16px 24px'})

# App Layout
app.layout = html.Div([
    header,
    main_panel,
])

# =============================================================================
# CALLBACKS
# =============================================================================

# ── Tab switching — pure Python, no clientside callbacks ──────────────────────
@callback(
    [Output('active-tab-store',  'data'),
     Output('panel-data-tab',    'style'),
     Output('panel-code-tab',    'style'),
     Output('panel-results-tab', 'style'),
     Output('panel-dialogue-tab','style'),
     Output('tab-btn-data',      'className'),
     Output('tab-btn-code',      'className'),
     Output('tab-btn-results',   'className'),
     Output('tab-btn-dialogue',  'className')],
    [Input('tab-btn-data',     'n_clicks'),
     Input('tab-btn-code',     'n_clicks'),
     Input('tab-btn-results',  'n_clicks'),
     Input('tab-btn-dialogue', 'n_clicks'),
     Input('active-tab-store', 'data')],
    prevent_initial_call=False,
)
def switch_tab(n_data, n_code, n_results, n_dialogue, current_tab):
    """Switch visible panel and highlight the active pill button."""
    from dash import ctx
    btn_map = {
        'tab-btn-data':     'data-tab',
        'tab-btn-code':     'code-tab',
        'tab-btn-results':  'results-tab',
        'tab-btn-dialogue': 'dialogue-tab',
    }
    if ctx.triggered_id in btn_map:
        tab = btn_map[ctx.triggered_id]
    else:
        tab = current_tab or 'data-tab'

    ids    = ['data-tab', 'code-tab', 'results-tab', 'dialogue-tab']
    panels = [{'display': 'block'} if t == tab else {'display': 'none'} for t in ids]
    btns   = ['tab-btn active' if t == tab else 'tab-btn' for t in ids]
    return [tab] + panels + btns

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
                    style={'fontSize': '10px', 'marginBottom': '0'}
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
    """Reset to original dataset (only affects Step 1 data customization)"""
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    return (
        original_data,
        "",
        dbc.Alert("✅ Reset to original dataset", color="success"),
        html.Div()
    )

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

    # Create the keep columns list
    keep_columns = [y_var, x_var, hbar_var]
    if keep_vars:
        keep_columns.extend(keep_vars)
    keep_columns = list(dict.fromkeys(keep_columns))

    # Automatically include any derived columns (columns not in original ADRS)
    original_adrs_cols = set(ADRS_DATA.columns)
    derived_cols = [c for c in df.columns
                    if c not in original_adrs_cols and c not in keep_columns]

    # Final columns = selected + derived
    final_columns = keep_columns + derived_cols

    # Filter to selected columns only — row structure preserved intact for AI code generation
    unique_df = df[final_columns]
    unique_len = len(unique_df)

    print(f"Dataset filtered: {unique_len} rows × {len(final_columns)} columns, keeping: {keep_columns}")

    # ── Run data_validator standards checks against the processed data ──────────
    validation = generator.data_validator.validate_all(
        unique_df, x_var, y_var, hbar_var
    )
    has_errors   = not validation["valid"]
    errors       = validation["errors"]
    warnings     = validation["warnings"]

    # ── Run individual validation checks for detailed reporting ──────────────────
    check_results = []

    # Check 1: All required variables selected
    vars_ok, vars_missing = generator.data_validator.validate_variables_specified(x_var, y_var, hbar_var)
    check_results.append(("All required variables selected", vars_ok, None))

    # Check 2: X-axis is numeric/linear
    x_ok, x_type = generator.data_validator.validate_x_axis_numeric(unique_df, x_var)
    check_results.append(("X-axis is numeric/linear", x_ok, f"Type: {x_type}" if x_ok else None))

    # Check 3: HBAR is numeric
    hbar_ok, hbar_type = generator.data_validator.validate_hbar_numeric(unique_df, hbar_var)
    check_results.append(("HBAR is numeric", hbar_ok, f"Type: {hbar_type}" if hbar_ok else None))

    # ── Get derivation metadata from customizer ────────────────────────────────
    report = generator.get_validation_report(x_var, y_var, hbar_var, unique_df)

    # ── Build combined validation report display ───────────────────────────────

    # Section 1 — data summary
    data_summary = html.Div([
        html.Strong("Data Summary:", style={'fontSize': '12px'}),
        html.P(f"Records: {unique_len:,} rows × {len(final_columns)} columns", style={'fontSize': '11px'}),
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

    # Section 3 — detailed validation checks
    checks_list = []
    for check_name, passed, detail in check_results:
        icon = "✅" if passed else "❌"
        color = "#198754" if passed else "#dc3545"
        check_text = f"{icon} {check_name}"
        if detail and passed:
            check_text += f" ({detail})"
        checks_list.append(html.Li(check_text, style={'fontSize': '11px', 'color': color}))

    checks_block = html.Div([
        html.Strong("Validation Checks:", style={'fontSize': '12px', 'marginBottom': '5px'}),
        html.Ul(checks_list, style={'marginBottom': '0'})
    ], className="mb-2")

    # Section 4 — standards violations (errors) if any
    if errors:
        error_block = html.Div([
            html.Strong("❌ Standards Violations — must fix before generating:", style={'fontSize': '12px', 'color': '#dc3545'}),
            html.Ul([html.Li(e, style={'fontSize': '11px', 'color': '#dc3545'}) for e in errors])
        ], className="mb-2")
    else:
        error_block = html.Div()

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
            checks_block,
            error_block,
            warning_block,
            action_row
        ], style={'padding': '10px'})
    ], color="light", className="mb-2")

    # Always disable Generate button after validation — user must click Approve & Continue
    return report_display, report, True, unique_df.to_dict('records')

# Handle approval — button already enabled by validate step if no errors
# Approval enables the Generate Swimmer Plot button
@callback(
    [Output('validation-report-display', 'children', allow_duplicate=True),
     Output('generate-code-btn', 'disabled', allow_duplicate=True)],
    Input('approve-variables-btn', 'n_clicks'),
    prevent_initial_call=True
)
def approve_variables(n_clicks):
    """User confirms approval — unlock Generate Swimmer Plot button"""
    if n_clicks is None:
        return dash.no_update, dash.no_update
    return dbc.Alert("✅ Approved — Generate Swimmer Plot is ready.", color="success"), False

# Handle edit — also re-disable Generate button so user must re-approve
@callback(
    [Output('validation-report-display', 'children', allow_duplicate=True),
     Output('generate-code-btn', 'disabled', allow_duplicate=True)],
    Input('edit-variables-btn', 'n_clicks'),
    prevent_initial_call=True
)
def edit_variables(n_clicks):
    """User wants to edit variables — lock Generate button until re-approved"""
    if n_clicks is None:
        return dash.no_update, dash.no_update
    return html.Div("Please adjust your variable selections above", style={'color': 'blue'}), True

# Generate code
@callback(
    [Output('generated-code-store', 'data'),
     Output('code-display', 'children'),
     Output('active-tab-store', 'data', allow_duplicate=True),
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
            sample_data=df,
            adsl_data=ADSL_DATA,
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
     Output('active-tab-store', 'data', allow_duplicate=True)],
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

# Save code — status shown inline in Generated Code tab
@callback(
    Output('save-code-status', 'children'),
    Input('save-code-btn', 'n_clicks'),
    State('generated-code-store', 'data'),
    prevent_initial_call=True
)
def save_code(n_clicks, code):
    """Auto-save generated Python code and show status inline"""
    if n_clicks is None or not code:
        return dash.no_update
    try:
        result = generator.save_code(code)
        return dbc.Alert(f"✅ Saved: {result}", color="success", duration=4000)
    except Exception as e:
        return dbc.Alert(f"Save error: {str(e)}", color="danger")

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

        # Pre-flight check flagged a missing VAR: prefix or unavailable column
        if status == "action_required":
            msg = info[0] if info else "Please revise your request."
            code_display = html.Div([
                dbc.Alert([
                    html.Strong("⚠ Action Required — "),
                    html.Span(msg)
                ], color="warning", className="mb-3"),
                html.H6("Current Code (unchanged):"),
                html.Pre(customized_code, style={
                    'backgroundColor': '#F5F5F5',
                    'padding': '15px',
                    'borderRadius': '5px',
                    'maxHeight': '500px',
                    'overflowY': 'auto'
                })
            ])
            # Keep original code — don't overwrite store
            return current_history, "", dash.no_update, code_display, dash.no_update

        # Normal success path
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

# Code conversion — auto-saves after conversion
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
    """Convert Python code to R or SAS and auto-save"""
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if not python_code:
        return (
            html.Div(),
            dbc.Alert("No Python code available. Generate a swimmer plot first.", color="warning"),
            html.Div(),
            None
        )

    if not generator.ai_enabled:
        return (
            html.Div(),
            dbc.Alert("AI not available. Check ANTHROPIC_API_KEY.", color="danger"),
            html.Div(),
            None
        )

    print(f"Converting Python code to {target_language}...")

    try:
        converted, status, notes = generator.convert_code_to_language(python_code, target_language)

        if status == "success":
            # Auto-save
            try:
                saved_as = generator.save_converted_code(converted, target_language)
                save_msg = f" Auto-saved: {saved_as}"
            except Exception as se:
                save_msg = f" (save failed: {se})"

            status_alert = dbc.Alert(
                f"✅ Converted to {target_language}.{save_msg}",
                color="success", duration=6000
            )

            notes_display = html.Div()
            if notes:
                notes_display = html.Div([
                    html.Strong(f"{target_language} notes:", style={'fontSize': '11px'}),
                    html.Ul([html.Li(n, style={'fontSize': '11px'}) for n in notes])
                ], style={'background': '#f8f9fa', 'padding': '10px', 'borderRadius': '6px', 'marginBottom': '8px'})

            code_display = html.Div([
                html.H6(f"{target_language} Code:", style={'fontSize': '12px'}),
                html.Pre(converted, style={
                    'backgroundColor': '#F5F5F5',
                    'padding': '12px',
                    'borderRadius': '5px',
                    'maxHeight': '400px',
                    'overflowY': 'auto',
                    'overflowX': 'auto',
                    'border': '1px solid #dee2e6',
                    'fontSize': '11px',
                })
            ])

            return code_display, status_alert, notes_display, converted

        else:
            return (
                html.Pre(converted, style={'color': 'red', 'fontSize': '11px'}),
                dbc.Alert(f"Conversion to {target_language} failed.", color="danger"),
                html.Div(),
                None
            )

    except Exception as e:
        return (
            html.Div(),
            dbc.Alert(f"Conversion error: {str(e)}", color="danger"),
            html.Div(),
            None
        )


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
