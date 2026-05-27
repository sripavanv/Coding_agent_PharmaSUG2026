"""
Swimmer Plot Generator — Orchestrator
Coordinates the full pipeline:
  1. Validate  →  2. Data customization  →  3. Graph generation
  4. Interactive customization  →  5. Code conversion (R/SAS)
"""

import os

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("Anthropic not installed. Run: pip install anthropic")

from data_customizer import DataCustomizer
from data_validator import DataValidator
from graph_generator import GraphGenerator
from graph_customizer import GraphCustomizer
from code_converter import CodeConverter


class SwimmerPlotGenerator:
    def __init__(self):
        print("Clinical Trials Swimmer Plot AI Generator initialized")

        self.claude_client = None
        self.ai_enabled = False
        self._current_processed_data = None

        if CLAUDE_AVAILABLE:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                try:
                    self.claude_client = anthropic.Anthropic(api_key=api_key)
                    self.ai_enabled = True
                    print("Claude AI enabled for two-step customization!")
                except Exception as e:
                    print(f"Claude client initialization failed: {e}")
            else:
                print("ANTHROPIC_API_KEY environment variable not set")

        self.data_customizer  = DataCustomizer(self.claude_client, self.ai_enabled)
        self.data_validator   = DataValidator()
        self.graph_generator  = GraphGenerator(self.claude_client, self.ai_enabled)
        self.graph_customizer = GraphCustomizer(self.claude_client, self.ai_enabled)
        self.code_converter   = CodeConverter(self.claude_client, self.ai_enabled)
        print("✅ All modules initialized successfully")

    # ── Main pipeline ──────────────────────────────────────────────────────────

    def generate_swimmer_code(self, x_var, y_var, hbar_var, data_customization, graph_customization, sample_data, adsl_data=None):
        """Generate swimmer plot code with two-step AI customization (data then graph)"""
        print(f"\n=== SWIMMER PLOT GENERATION ===")
        print(f"Variables: X={x_var}, Y={y_var}, HBAR={hbar_var}")
        print(f"AI enabled: {self.ai_enabled}")

        if not self.ai_enabled:
            return "# Error: AI not available. Please set ANTHROPIC_API_KEY environment variable", ["AI required"], "error"

        # Step 1: Validate
        validation = self.data_validator.validate_all(
            sample_data, x_var, y_var, hbar_var, data_customization, graph_customization
        )
        if not validation["valid"]:
            return f"# Error: {'; '.join(validation['errors'])}", validation["errors"], "error"
        if validation["warnings"]:
            print(f"⚠ Warnings: {validation['warnings']}")

        # Step 2: Data customization
        original_shape = sample_data.shape
        print("\n--- STEP 1: DATA CUSTOMIZATIONS ---")
        processed_data = (
            self.data_customizer.apply_data_customizations(
                sample_data, data_customization, x_var, y_var, hbar_var,
                adsl_data=adsl_data,
            )
            if data_customization and data_customization.strip()
            else sample_data
        )
        self._current_processed_data = processed_data

        # Step 3: Graph code generation
        print("\n--- STEP 2: GRAPH CODE GENERATION ---")
        code = self.graph_generator.generate_with_ai(
            x_var, y_var, hbar_var, graph_customization, processed_data,
            derivation_context=self.data_customizer.derivation_context,
        )
        print(f"Generated {len(code)} characters of swimmer plot code")

        # Step 4: Seed customizer context with available columns
        available_columns = list(processed_data.columns)
        self.graph_customizer.set_plot_context(code, x_var, y_var, hbar_var, processed_data.shape, available_columns)

        info = [
            f"Y-axis: {y_var} (categorical - subjects)",
            f"X-axis: {x_var} (linear - time/days)",
            f"HBAR: {hbar_var} (duration per subject)",
            f"Data rows: {original_shape[0]} → {processed_data.shape[0]}",
            "Two-step AI customization: Data → Graph",
        ]
        return code, info, "new"

    # ── Delegated operations ───────────────────────────────────────────────────

    def customize_plot_interactively(self, user_request):
        return self.graph_customizer.customize_plot_interactively(user_request)

    def get_conversation_history(self):
        return self.graph_customizer.get_conversation_history()

    def clear_conversation_history(self):
        self.graph_customizer.clear_conversation_history()

    def convert_code_to_language(self, python_code, target_language):
        return self.code_converter.convert_code_to_language(
            python_code, target_language, self.graph_customizer.current_plot_context
        )

    def save_converted_code(self, code_content, language):
        return self.code_converter.save_converted_code(code_content, language)

    def debug_code(self, failed_code, error_message, sample_data, x_var, y_var, hbar_var):
        return self.graph_generator.debug_code(failed_code, error_message, sample_data, x_var, y_var, hbar_var)

    def get_validation_report(self, x_var, y_var, hbar_var, processed_data):
        return self.data_customizer.get_validation_report(x_var, y_var, hbar_var, processed_data)


    def execute_code_safely(self, code_content, processed_data):
        return self.graph_generator.execute_code_safely(code_content, processed_data)

    def save_code(self, code_content):
        return self.graph_generator.save_code(code_content)

    # ── Backwards-compatibility properties ────────────────────────────────────

    @property
    def current_plot_context(self):
        return self.graph_customizer.current_plot_context

    @current_plot_context.setter
    def current_plot_context(self, value):
        self.graph_customizer.current_plot_context = value

    @property
    def derivation_context(self):
        return self.data_customizer.derivation_context

