"""
Main Swimmer Plot Generator
Orchestrates the complete flow using modular components:
1. Data loading (data_utils)
2. Data customization (data_customizer)
3. Data validation (data_validator)
4. Graph generation (graph_generator)
5. Graph customization (graph_customizer)
6. Code conversion (code_converter)
"""

import pandas as pd
import numpy as np
import os

# Import modular components
from data_customizer import DataCustomizer
from data_validator import DataValidator
from graph_generator import GraphGenerator
from graph_customizer import GraphCustomizer
from code_converter import CodeConverter

# Import Claude AI
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("Anthropic not installed. Run: pip install anthropic")


class SwimmerPlotGenerator:
    def __init__(self):
        print("Clinical Trials Swimmer Plot AI Generator initialized")

        # Initialize Claude AI
        self.claude_client = None
        self.ai_enabled = False
        self._current_processed_data = None  # Store processed data for execution

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
        else:
            print("Anthropic library not available")

        # Initialize modular components
        self.data_customizer = DataCustomizer(self.claude_client, self.ai_enabled)
        self.data_validator = DataValidator()
        self.graph_generator = GraphGenerator(self.claude_client, self.ai_enabled)
        self.graph_customizer = GraphCustomizer(self.claude_client, self.ai_enabled)
        self.code_converter = CodeConverter(self.claude_client, self.ai_enabled)

        print("✅ All modules initialized successfully")

    def generate_swimmer_code(self, x_var, y_var, hbar_var, data_customization, graph_customization, sample_data):
        """Generate swimmer plot code with two-step AI customization (data then graph) - MODULAR VERSION"""

        print(f"\n=== SWIMMER PLOT GENERATION DEBUG ===")
        print(f"Variables: X={x_var}, Y={y_var}, HBAR={hbar_var}")
        print(f"Data customization: {len(data_customization) if data_customization else 0} characters")
        print(f"Graph customization: {len(graph_customization) if graph_customization else 0} characters")
        print(f"Sample data shape: {sample_data.shape if sample_data is not None else 'None'}")
        print(f"AI enabled: {self.ai_enabled}")

        if not self.ai_enabled:
            print("⚠ AI not available. Please set ANTHROPIC_API_KEY environment variable")
            return "# Error: AI not available. Please set ANTHROPIC_API_KEY environment variable", ["AI required"], "error"

        # === STEP 1: VALIDATION ===
        print("\n--- VALIDATION ---")
        validation_result = self.data_validator.validate_all(
            sample_data, x_var, y_var, hbar_var, data_customization, graph_customization
        )

        if not validation_result["valid"]:
            error_msg = "\n".join(validation_result["errors"])
            print(f"⚠ Validation failed: {error_msg}")
            return f"# Error: {error_msg}", validation_result["errors"], "error"

        if validation_result["warnings"]:
            print(f"⚠ Warnings: {validation_result['warnings']}")

        # === STEP 2: DATA CUSTOMIZATION ===
        print("\n--- STEP 1: DATA CUSTOMIZATIONS ---")
        original_data_shape = sample_data.shape
        processed_data = sample_data

        if data_customization and data_customization.strip():
            print("Applying data customizations...")
            processed_data = self.data_customizer.apply_data_customizations(
                sample_data, data_customization, x_var, y_var, hbar_var
            )
            print(f"Data transformation: {original_data_shape} → {processed_data.shape}")
        else:
            print("No data customizations provided - using original data")

        # CRITICAL: Store processed data for later use
        self._current_processed_data = processed_data

        # === STEP 3: GRAPH CODE GENERATION ===
        print("\n--- STEP 2: GRAPH CODE GENERATION ---")
        print("Generating swimmer plot code with graph customizations...")
        code = self.graph_generator.generate_with_ai(
            x_var, y_var, hbar_var, graph_customization, processed_data,
            derivation_context=self.data_customizer.derivation_context
        )

        print(f"Generated {len(code)} characters of swimmer plot code")

        # === STEP 4: INITIALIZE CUSTOMIZATION CONTEXT ===
        self.graph_customizer.set_plot_context(code, x_var, y_var, hbar_var, processed_data.shape)

        info = [
            f"Y-axis: {y_var} (categorical - subjects)",
            f"X-axis: {x_var} (linear - time/days)",
            f"HBAR: {hbar_var} (duration per subject)",
            f"Data rows: {original_data_shape[0]} → {processed_data.shape[0]}",
            "Two-step AI customization: Data → Graph"
        ]

        return code, info, "new"

    # === INTERACTIVE CUSTOMIZATION ===
    def customize_plot_interactively(self, user_request):
        """Apply iterative customizations to the current plot through dialogue"""
        return self.graph_customizer.customize_plot_interactively(user_request)

    def get_conversation_history(self):
        """Get conversation history for UI display"""
        return self.graph_customizer.get_conversation_history()

    def clear_conversation_history(self):
        """Clear conversation history"""
        self.graph_customizer.clear_conversation_history()

    # === CODE CONVERSION ===
    def convert_code_to_language(self, python_code, target_language):
        """Convert Python swimmer plot code to R or SAS"""
        plot_context = self.graph_customizer.current_plot_context
        return self.code_converter.convert_code_to_language(python_code, target_language, plot_context)

    def save_converted_code(self, code_content, language):
        """Save converted code with appropriate file extension"""
        return self.code_converter.save_converted_code(code_content, language)

    # === DEBUGGING ===
    def debug_code(self, failed_code, error_message, sample_data, x_var, y_var, hbar_var):
        """AI debugging with strict swimmer plot guardrails"""
        return self.graph_generator.debug_code(failed_code, error_message, sample_data, x_var, y_var, hbar_var)

    # === VALIDATION REPORTS ===
    def get_validation_report(self, x_var, y_var, hbar_var, processed_data):
        """Generate validation report for user approval"""
        return self.data_customizer.get_validation_report(x_var, y_var, hbar_var, processed_data)

    def filter_data_to_plot_variables(self, data, required_vars, additional_vars=None):
        """Filter dataset to keep only variables needed for plotting"""
        return self.data_customizer.filter_data_to_plot_variables(data, required_vars, additional_vars)

    # === CODE EXECUTION ===
    def execute_code_safely(self, code_content, processed_data):
        """Execute swimmer plot code safely"""
        return self.graph_generator.execute_code_safely(code_content, processed_data)

    def save_code(self, code_content):
        """Save generated swimmer plot code"""
        return self.graph_generator.save_code(code_content)

    # === BACKWARDS COMPATIBILITY ===
    # These properties maintain backwards compatibility with existing code
    @property
    def current_plot_context(self):
        """Get current plot context (backwards compatibility)"""
        return self.graph_customizer.current_plot_context

    @current_plot_context.setter
    def current_plot_context(self, value):
        """Set current plot context (backwards compatibility)"""
        self.graph_customizer.current_plot_context = value

    @property
    def derivation_context(self):
        """Get derivation context (backwards compatibility)"""
        return self.data_customizer.derivation_context

    def _clean_code(self, generated_code):
        """Simple code cleaning - delegates to data_customizer"""
        return self.data_customizer._clean_code(generated_code)
