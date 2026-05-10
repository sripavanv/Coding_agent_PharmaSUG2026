"""
Graph Customizer Module
Handles iterative, dialogue-based modifications to an existing swimmer plot.
"""

import pandas as pd

MODEL = "claude-sonnet-4-6"


class GraphCustomizer:
    def __init__(self, claude_client=None, ai_enabled=False):
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled
        self.conversation_history = []
        self.current_plot_context = {
            'code': '', 'x_var': '', 'y_var': '', 'hbar_var': '', 'processed_data_shape': None,
        }

    def set_plot_context(self, code, x_var, y_var, hbar_var, processed_data_shape):
        """Set a new plot context and reset conversation history."""
        self.current_plot_context = {
            'code': code, 'x_var': x_var, 'y_var': y_var,
            'hbar_var': hbar_var, 'processed_data_shape': processed_data_shape,
        }
        self.conversation_history.clear()

    # ── Public API ─────────────────────────────────────────────────────────────

    def customize_plot_interactively(self, user_request):
        """Apply a natural-language modification to the current plot code."""
        if not self.ai_enabled:
            return "# Error: AI required for interactive customization", ["AI required"], "error"
        if not self.current_plot_context['code']:
            return "# Error: No plot context — generate a plot first.", ["No context"], "error"

        self.conversation_history.append({
            'type': 'user', 'content': user_request, 'timestamp': pd.Timestamp.now(),
        })

        print(f"\n=== INTERACTIVE CUSTOMIZATION ===")
        print(f"Request: {user_request}")
        print(f"History: {len(self.conversation_history)} messages")

        try:
            modified_code = self._apply_customization(user_request)
            self.current_plot_context['code'] = modified_code
            self.conversation_history.append({
                'type': 'assistant',
                'content': f"Applied: {user_request[:100]}...",
                'timestamp': pd.Timestamp.now(),
            })
            ctx = self.current_plot_context
            info = [
                "Interactive customization applied",
                f"Conversation history: {len(self.conversation_history)} messages",
                f"Variables: {ctx['x_var']}, {ctx['y_var']}, {ctx['hbar_var']}",
            ]
            return modified_code, info, "customized"

        except Exception as e:
            print(f"⚠ Customization failed: {e}")
            return f"# Error: {e}", ["Customization failed"], "error"

    def get_conversation_history(self):
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        self.conversation_history.clear()
        print("Conversation history cleared.")

    # ── Internal ───────────────────────────────────────────────────────────────

    def _apply_customization(self, user_request):
        ctx = self.current_plot_context
        y, x, hbar = ctx['y_var'], ctx['x_var'], ctx['hbar_var']

        # Last 6 messages for context
        history_str = ""
        if self.conversation_history:
            lines = []
            for i, m in enumerate(self.conversation_history[-6:], 1):
                role = "User" if m['type'] == 'user' else "Assistant"
                snippet = m['content'][:150] + ("..." if len(m['content']) > 150 else "")
                lines.append(f"  {i}. {role}: {snippet}")
            history_str = "\nCONVERSATION HISTORY (last 6):\n" + "\n".join(lines) + "\n"

        prompt = f"""MODIFY the existing swimmer plot code — do NOT regenerate from scratch.

═══════════════════════════════════════════════════════════════════
SWIMMER PLOT INVARIANTS — NEVER CHANGE
═══════════════════════════════════════════════════════════════════
• Y-axis: {y} column values (never numeric indices)
• HBAR: go.Bar(orientation='h') — mandatory, one per subject
• X-axis: {x} (numeric)
• Overlays: go.Scatter with y={y} column values directly
• NEVER delete go.Bar traces. NEVER remove subjects.
{history_str}
CURRENT PLOT CONTEXT:
- Variables: X={x}, Y={y}, HBAR={hbar}
- Data shape: {ctx['processed_data_shape']}
- Code length: {len(ctx['code'])} characters

CURRENT CODE:
```python
{ctx['code']}
```

USER REQUEST: {user_request}

═══════════════════════════════════════════════════════════════════
MODIFICATION GUIDELINES
═══════════════════════════════════════════════════════════════════
ALLOWED:
• Colors, sizes, borders, symbols, opacity
• Hover info, annotations, title/labels, legend
• Add new go.Scatter() overlay traces
• Change layout parameters

FORBIDDEN:
• Delete go.Bar() traces
• Change y={y} to numeric indices or y_pos variables
• Remove subjects from the plot
• Regenerate the entire code

REVERT requests: restore only the previously changed parameter; leave everything else.

DERIVE + OVERLAY requests: tell the user:
  "Variable derivation must be done in the data customization step first.
   Once [variable] exists in the dataset, I can overlay it here."

Return the COMPLETE modified code with all traces intact:"""

        message = self.claude_client.messages.create(
            model=MODEL, max_tokens=4000, temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        response = message.content[0].text.strip()

        if response.startswith("CLARIFICATION_NEEDED:"):
            question = response.replace("CLARIFICATION_NEEDED:", "").strip()
            print(f"AI needs clarification: {question}")
            return f"# CLARIFICATION_NEEDED\n# {question}"

        return self._clean_code(response)

    def _clean_code(self, text):
        if '```python' in text:
            s = text.find('```python') + 9
            e = text.find('```', s)
            if e > s:
                text = text[s:e].strip()
        elif '```' in text:
            s = text.find('```') + 3
            e = text.find('```', s)
            if e > s:
                text = text[s:e].strip()
        return text.replace('fig.show()', '# fig.show() removed for Shiny integration').strip()
