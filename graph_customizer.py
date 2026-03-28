"""
Graph Customizer Module
Handles interactive customization of generated swimmer plots
Supports iterative dialogue-based modifications
"""

import pandas as pd


class GraphCustomizer:
    def __init__(self, claude_client=None, ai_enabled=False):
        """Initialize graph customizer with AI client"""
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled

        # Conversation history for iterative customization
        self.conversation_history = []
        self.current_plot_context = {
            'code': '',
            'x_var': '',
            'y_var': '',
            'hbar_var': '',
            'processed_data_shape': None
        }

    def set_plot_context(self, code, x_var, y_var, hbar_var, processed_data_shape):
        """Set the current plot context for customization"""
        self.current_plot_context = {
            'code': code,
            'x_var': x_var,
            'y_var': y_var,
            'hbar_var': hbar_var,
            'processed_data_shape': processed_data_shape
        }
        # Clear conversation history when new plot is set
        self.conversation_history = []

    def customize_plot_interactively(self, user_request):
        """Apply iterative customizations to the current plot through dialogue"""

        if not self.ai_enabled:
            return "# Error: AI not available for interactive customization", ["AI required"], "error"

        if not self.current_plot_context['code']:
            return "# Error: No plot context available. Generate a plot first.", ["No context"], "error"

        # Add user request to conversation history
        self.conversation_history.append({
            'type': 'user',
            'content': user_request,
            'timestamp': pd.Timestamp.now()
        })

        print(f"\n=== INTERACTIVE CUSTOMIZATION ===")
        print(f"User request: {user_request}")
        print(f"Conversation history: {len(self.conversation_history)} messages")

        try:
            # Build conversation context for AI
            conversation_context = self._build_conversation_context()

            # Generate customized code
            customized_code = self._apply_interactive_customization(user_request, conversation_context)

            # Update current context
            self.current_plot_context['code'] = customized_code

            # Add AI response to conversation history
            self.conversation_history.append({
                'type': 'assistant',
                'content': f"Applied customization: {user_request[:100]}...",
                'timestamp': pd.Timestamp.now()
            })

            info = [
                f"Interactive customization applied",
                f"Conversation history: {len(self.conversation_history)} messages",
                f"Variables: {self.current_plot_context['x_var']}, {self.current_plot_context['y_var']}, {self.current_plot_context['hbar_var']}"
            ]

            return customized_code, info, "customized"

        except Exception as e:
            error_msg = f"Interactive customization failed: {str(e)}"
            print(error_msg)
            return f"# Error: {error_msg}", ["Customization failed"], "error"

    def _build_conversation_context(self):
        """Build conversation context for AI from history"""

        context_parts = [
            f"CURRENT PLOT CONTEXT:",
            f"- Variables: X={self.current_plot_context['x_var']}, Y={self.current_plot_context['y_var']}, HBAR={self.current_plot_context['hbar_var']}",
            f"- Data shape: {self.current_plot_context['processed_data_shape']}",
            f"- Current code length: {len(self.current_plot_context['code'])} characters",
            ""
        ]

        if self.conversation_history:
            context_parts.append("CONVERSATION HISTORY:")
            for i, msg in enumerate(self.conversation_history[-6:], 1):  # Last 6 messages
                role = "User" if msg['type'] == 'user' else "Assistant"
                content = msg['content'][:150] + "..." if len(msg['content']) > 150 else msg['content']
                context_parts.append(f"{i}. {role}: {content}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _apply_interactive_customization(self, user_request, conversation_context):
        """Apply interactive customization using AI"""

        current_code = self.current_plot_context['code']
        y_var = self.current_plot_context.get('y_var', 'Unknown')
        x_var = self.current_plot_context.get('x_var', 'Unknown')
        hbar_var = self.current_plot_context.get('hbar_var', 'Unknown')

        prompt = f"""MODIFY existing swimmer plot code. DO NOT regenerate from scratch.

═══════════════════════════════════════════════════════════════════
SWIMMER PLOT CORE STRUCTURE - NEVER VIOLATE
═══════════════════════════════════════════════════════════════════
A swimmer plot MUST ALWAYS have:

1. Y-AXIS: {y_var} column (subject identifiers)
   - One tick per unique subject
   - NEVER change to numeric indices
   - NEVER remove subjects

2. HBAR (Horizontal Bars):
   - go.Bar(orientation='h') traces
   - y={y_var} column values
   - x={hbar_var} column values (bar length)
   - ONE bar per unique subject
   - MUST ALWAYS EXIST - this IS the swimmer plot

3. X-AXIS: {x_var} column (numeric time/days)
   - NEVER change to categorical

4. OVERLAYS (optional):
   - go.Scatter() traces on top of bars
   - y={y_var} column values (same as bars for alignment)
   - x={x_var} column values (timepoints)

═══════════════════════════════════════════════════════════════════
EXISTING CODE TO MODIFY
═══════════════════════════════════════════════════════════════════
```python
{current_code}
```

═══════════════════════════════════════════════════════════════════
USER REQUEST
═══════════════════════════════════════════════════════════════════
{user_request}

═══════════════════════════════════════════════════════════════════
MODIFICATION GUIDELINES
═══════════════════════════════════════════════════════════════════

ALLOWED MODIFICATIONS:
• Change colors: Modify marker_color, color parameters
• Change sizes: Modify marker size, width parameters
• Add borders: Add marker_line parameters
• Change symbols: Modify marker symbol parameter
• Add/remove hover: Use fig.update_traces(hoverinfo=...)
• Add annotations: Use fig.add_annotation() or text/textposition in go.Bar()
• Change title/labels: Modify fig.update_layout() parameters
• Add/remove legend: Modify showlegend parameters
• Change opacity: Modify opacity parameters
• Add overlay markers: Add new go.Scatter() trace for new variables
  - If overlaying variable EOS (or similar timepoint), use x=data['EOS']
  - If overlaying categorical at existing timepoints, use x=data['{x_var}']
  - Example: "overlay EOS" → x=eos_subset['EOS'], NOT x=eos_subset['{x_var}']

MODIFICATION APPROACH:
1. Locate the specific parameter/section to modify
2. Make MINIMAL changes - only what user requested
3. Keep all existing traces (HBAR and overlays)
4. Keep all Y-axis as {y_var} column values
5. Keep all X-axis as numeric values

FORBIDDEN ACTIONS:
• DO NOT delete go.Bar() traces (HBAR is mandatory)
• DO NOT regenerate the entire code from scratch
• DO NOT change y={y_var} to numeric indices or positions
• DO NOT change data filtering/subsetting (that's data prep)
• DO NOT remove subjects from the plot
• DO NOT change variable names ({x_var}, {y_var}, {hbar_var})

REVERT REQUESTS:
If user says "revert" or "undo":
• Identify what was changed in previous modification
• Restore ONLY that specific parameter to its original value
• Keep everything else as-is
• DO NOT regenerate entire code

DERIVE AND OVERLAY REQUESTS:
If user asks to "derive variable X and overlay it":
• This requires data preparation FIRST
• Tell user: "Data derivation must be done in data customization step first. Once variable X exists in the dataset, I can overlay it on the plot."
• DO NOT attempt to derive variables in graph code

═══════════════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════════════
1. Identify EXACTLY what parameter/section needs modification
2. Locate that section in the existing code
3. Make ONLY the requested change
4. Return COMPLETE modified code with swimmer plot structure intact
5. Preserve all go.Bar() and go.Scatter() traces
6. Keep y={y_var} and x={x_var}/{hbar_var} unchanged"""

        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()

            # Check if AI is asking for clarification
            if response_text.startswith("CLARIFICATION_NEEDED:"):
                clarification_question = response_text.replace("CLARIFICATION_NEEDED:", "").strip()
                print(f"AI needs clarification: {clarification_question}")
                # Return special marker so server can display this as a question
                return f"# CLARIFICATION_NEEDED\n# {clarification_question}"

            modified_code = self._clean_code(response_text)
            print(f"Applied interactive customization: {len(modified_code)} characters")

            return modified_code

        except Exception as e:
            print(f"⚠ Interactive customization failed: {e}")
            return current_code  # Return unchanged code if customization fails

    def get_conversation_history(self):
        """Get conversation history for UI display"""
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("Conversation history cleared")

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
