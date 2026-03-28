# Clinical Trials Swimmer Plot Generator

> AI-powered oncology swimmer plot generation with structured prompt engineering and validation checkpoints — built on the framework presented in **PharmaSUG 2026 Paper AI-101**: *"How to Train Your Dragon: Embedding AI in Clinical Workflow"* by Sri Pavan Vemuri.

---

## Overview

This tool embeds **Anthropic Claude AI** into a clinical data workflow to generate, customize, and export publication-ready oncology swimmer plots from CDISC ADaM datasets. The visualization is the proving ground — the real contribution is the **blueprint**: a reusable methodology for reliable AI integration in pharmaceutical data analysis.

The framework rests on two pillars:

1. **Structured Prompt Engineering** — Clear role definitions, explicit guardrails, and structured context that guide the LLM toward consistent, reproducible outputs.
2. **Validation Checkpoints** — Layered verification that catches errors before they compound, ensuring CDISC compliance and structural integrity at every stage.

---

## Features

- **Natural language data customization** — Filter, derive, and merge CDISC datasets (ADSL, ADRS) using plain English instructions
- **AI-powered code generation** — Produces executable Plotly swimmer plot code via `claude-sonnet-4-20250514`
- **Built-in debugging** — Automatically detects execution failures and triggers AI-driven code correction
- **Iterative conversational refinement** — Chat-style interface for incremental plot customization with persistent conversation history
- **Multi-language export** — Converts finalized Python/Plotly code to **R** (ggplot2 + plotly) or **SAS** (GTL / PROC SGRENDER)
- **CDISC-compliant guardrails** — Enforces ADaM naming conventions, subject identifier merge keys, and swimmer plot structural invariants throughout

---

## Architecture

The system is a multi-layered pipeline orchestrated by a `SwimmerPlotGenerator` class — think of it like a conductor leading a six-piece ensemble, where each module is expert in exactly one thing:

```
SwimmerPlotGenerator (orchestrator)
├── DataValidator       — enforces variable type and existence rules
├── DataCustomizer      — translates NLP instructions into pandas transformations
├── GraphGenerator      — generates and executes Plotly swimmer plot code
├── GraphCustomizer     — maintains conversation context for iterative refinement
└── CodeConverter       — translates Python code to R or SAS
```

The web interface is built with **Dash** and uses a reactive, tab-based layout that walks users through the workflow sequentially: data loading → customization → variable selection → code generation → interactive refinement → export.

---

## Tech Stack

| Component | Technology |
|---|---|
| Web interface | Python Dash + Bootstrap |
| Visualization | Plotly Graph Objects |
| AI backend | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Data processing | Pandas, NumPy |
| Data standards | CDISC ADaM (ADSL, ADRS) |
| Export targets | R (ggplot2/plotly), SAS (GTL) |

---

## Prerequisites

- Python 3.8+
- An [Anthropic API key](https://console.anthropic.com/)
- CDISC ADaM datasets: `ADSL.csv` and `ADRS_ONCO.csv` in the project root

---

## Installation

```bash
git clone https://github.com/your-username/swimmer-plot-generator.git
cd swimmer-plot-generator

pip install dash dash-bootstrap-components plotly pandas numpy anthropic
```

---

## Usage

1. **Set your API key:**

```bash
# macOS/Linux
export ANTHROPIC_API_KEY='your-key-here'

# Windows
set ANTHROPIC_API_KEY=your-key-here
```

2. **Place your CDISC datasets** in the project root:
   - `ADSL.csv`
   - `ADRS_ONCO.csv`

3. **Launch the app:**

```bash
python dash_app.py
```

4. **Open** `http://localhost:8050` in your browser.

---

## Workflow

| Step | Tab | Description |
|------|-----|-------------|
| 1 | Data Preparation | Load ADRS/ADSL datasets; optionally customize via natural language |
| 2 | Variable Selection | Specify Y-axis (subjects), X-axis (time), and HBAR (duration) |
| 3 | Validation | Review auto-generated validation report; approve to proceed |
| 4 | Code Generation | AI generates Plotly swimmer plot code with optional graph styling |
| 5 | Generated Code | Inspect, run, debug, and save the generated code |
| 6 | Results | View the rendered interactive swimmer plot |
| 7 | Interactive Customization | Iteratively refine the plot via natural language dialogue |
| 8 | Code Conversion | Export finalized code to R or SAS |

---

## Project Structure

```
swimmer-plot-generator/
├── dash_app.py          # Dash web interface and callbacks
├── code_generator.py    # SwimmerPlotGenerator orchestrator
├── data_customizer.py   # NLP → pandas transformation via Claude AI
├── data_validator.py    # Variable and data type validation
├── graph_generator.py   # AI code generation, execution, debugging
├── graph_customizer.py  # Conversational plot refinement
├── code_converter.py    # Python → R / SAS translation
├── data_utils.py        # CDISC dataset loaders
├── ADSL.csv             # [You provide] Subject-level dataset
├── ADRS_ONCO.csv        # [You provide] Response dataset
└── outputs/
    ├── validation_reports/
    ├── graphs/
    └── code/
```

---

## Swimmer Plot Invariants

The system enforces these structural rules at every stage — they cannot be overridden:

- **Y-axis** must be a categorical subject identifier (`SUBJID`/`USUBJID`)
- **Horizontal bars** (`go.Bar(orientation='h')`) are mandatory — one per subject
- **X-axis** must be numeric or datetime (linear scale)
- **Overlay markers** (`go.Scatter()`) must reference the same Y-axis values as the bars
- Custom Y-position mappings and numeric index substitutions are **forbidden**

---

## Configuration

Update `BASE_DIR` in `data_utils.py` to point to your CDISC data directory:

```python
BASE_DIR = Path("/path/to/your/cdisc/data")
```

---

## Recommended Reading

- [Develop Generative AI Applications: Get Started (Coursera)](https://www.coursera.org)
- [CS50's Introduction to Programming with Python (edX)](https://www.edx.org/learn/python/harvard-university-cs50-s-introduction-to-programming-with-python)
- [Attention Is All You Need (Google Research)](https://research.google/pubs/attention-is-all-you-need/)

---

## Contact

**Sri Pavan Vemuri** — sripavanv@gmail.com

Questions and contributions are welcome!

---

## License

This project is intended for research and educational use. Feel free to copy and use the code. But please ensure compliance with your organization's policies when using AI-generated code in regulated clinical environments.
