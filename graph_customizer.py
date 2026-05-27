"""
Graph Customizer Module
Handles iterative, dialogue-based modifications to an existing swimmer plot.
"""

import pandas as pd

from utils import clean_code

MODEL = "claude-sonnet-4-6"


class GraphCustomizer:
    def __init__(self, claude_client=None, ai_enabled=False):
        self.claude_client = claude_client
        self.ai_enabled = ai_enabled
        self.conversation_history = []
        self.current_plot_context = {
            'code': '', 'x_var': '', 'y_var': '', 'hbar_var': '', 'processed_data_shape': None,
            'available_columns': []
        }

    def set_plot_context(self, code, x_var, y_var, hbar_var, processed_data_shape, available_columns=None):
        """Set a new plot context and reset conversation history."""
        self.current_plot_context = {
            'code': code, 'x_var': x_var, 'y_var': y_var,
            'hbar_var': hbar_var, 'processed_data_shape': processed_data_shape,
            'available_columns': available_columns or []
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
            result = self._apply_customization(user_request)

            # Pre-flight check returned a user action message — don't update code or history
            if result.startswith('# USER_ACTION_REQUIRED'):
                msg = result.replace('# USER_ACTION_REQUIRED\n# ', '').strip()
                self.conversation_history.append({
                    'type': 'assistant',
                    'content': msg,
                    'timestamp': pd.Timestamp.now(),
                })
                return self.current_plot_context['code'], [msg], "action_required"

            self.current_plot_context['code'] = result
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
            return result, info, "customized"

        except Exception as e:
            print(f"⚠ Customization failed: {e}")
            return f"# Error: {e}", ["Customization failed"], "error"

    def get_conversation_history(self):
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        self.conversation_history.clear()
        print("Conversation history cleared.")

    # ── Internal ───────────────────────────────────────────────────────────────
    # ── Pre-flight variable check ──────────────────────────────────────────────

    def _check_var_references(self, user_request, available_cols):
        """Python-side enforcement of VAR: prefix convention.

        Returns (ok, message) where:
          ok=True  → safe to call AI
          ok=False → return message directly to user, skip AI call
        """
        import re

        # Detect bare column-like tokens that look like dataset variables but lack VAR:
        # Heuristic: ALL_CAPS words of 3+ chars, or known patterns like overlaying a word
        # that matches an available column without the VAR: prefix.
        var_tagged = re.findall(r'VAR:(\w+)', user_request)

        # Strip VAR: prefixed words first, then find bare ALL_CAPS words (3+ chars)
        request_stripped = re.sub(r'VAR:\w+', '', user_request)
        bare_upper = re.findall(r'\b([A-Z][A-Z0-9_]{2,})\b', request_stripped)

        # Deduplicate; skip common non-column words
        IGNORE = {'NL', 'AI', 'SAS', 'GTL', 'HTML', 'CSS', 'URL', 'API',
                  'NA', 'TRUE', 'FALSE', 'NULL', 'AND', 'OR', 'NOT',
                  'FOR', 'USE', 'ADD', 'SET', 'GET', 'PUT', 'ALL', 'NEW', 'OLD'}
        bare_upper = [w for w in dict.fromkeys(bare_upper) if w not in IGNORE and w not in var_tagged]

        if bare_upper:
            suggestions = "  ".join(f"VAR:{w}" for w in bare_upper)
            return False, (
                f"⚠ Looks like you're referencing column(s) **{', '.join(bare_upper)}** "
                f"without the required `VAR:` prefix.\n\n"
                f"Please rewrite using the prefix so the system can validate the column before calling AI:\n"
                f"→ {suggestions}"
            )

        # Check VAR: tagged columns exist in available_cols
        unavailable = [v for v in var_tagged if v not in available_cols]

        if unavailable:
            col_list = ", ".join(f"`VAR:{v}`" for v in unavailable)
            return False, (
                f"❌ Column(s) {col_list} are not available in the current plot dataset.\n\n"
                f"To use {'this column' if len(unavailable)==1 else 'these columns'}:\n"
                f"1. Go back to **Step 2: Swimmer Plot Variables**\n"
                f"2. Add the column(s) to **Additional Variables to Keep**\n"
                f"3. Click **Generate Validation Report** → **Generate Swimmer Plot**\n"
                f"4. Return here to Interactive Customization\n\n"
                f"💡 If it's a derived variable, create it in **Step 1: Data Customization** first."
            )

        return True, ""


    def _apply_customization(self, user_request):
        ctx = self.current_plot_context
        y, x, hbar = ctx['y_var'], ctx['x_var'], ctx['hbar_var']
        available_cols = ctx.get('available_columns', [])

        # ── Python-side VAR: check — runs before AI call ──────────────────────
        ok, msg = self._check_var_references(user_request, available_cols)
        if not ok:
            return f'# USER_ACTION_REQUIRED\n# {msg}'

        # Last 6 messages for context
        history_str = ""
        if self.conversation_history:
            lines = []
            for i, m in enumerate(self.conversation_history[-6:], 1):
                role = "User" if m['type'] == 'user' else "Assistant"
                snippet = m['content'][:150] + ("..." if len(m['content']) > 150 else "")
                lines.append(f"  {i}. {role}: {snippet}")
            history_str = "\nCONVERSATION HISTORY (last 6):\n" + "\n".join(lines) + "\n"

        # Build available columns display
        if available_cols:
            cols_str = f"AVAILABLE COLUMNS IN DATASET:\n{', '.join(available_cols)}\n\nThese are the ONLY columns you can use in data['column_name'] references."
        else:
            cols_str = f"AVAILABLE COLUMNS IN DATASET:\nPrimary columns: {x}, {y}, {hbar}\n(No additional columns were selected in Step 2)"

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

{cols_str}

CURRENT CODE:
```python
{ctx['code']}
```

USER REQUEST: {user_request}

═══════════════════════════════════════════════════════════════════
VARIABLE NAMING CONVENTION
═══════════════════════════════════════════════════════════════════
Dataset columns are referenced with the VAR: prefix (e.g. VAR:EOSDY).
PRE-FLIGHT CHECK ALREADY PASSED: all VAR: columns in this request have been
confirmed to exist in AVAILABLE COLUMNS — proceed directly with the modification.
If no VAR: prefix is present, the request is a style/layout change only.

═══════════════════════════════════════════════════════════════════
MODIFICATION GUIDELINES
═══════════════════════════════════════════════════════════════════
ALLOWED:
• Colors, sizes, borders, symbols, opacity
• Hover info, annotations, title/labels, legend
• Add new go.Scatter() overlay traces (ONLY using columns from AVAILABLE COLUMNS)
• Change layout parameters

FORBIDDEN:
• Delete go.Bar() traces
• Change y={y} to numeric indices or y_pos variables
• Remove subjects from the plot
• Regenerate the entire code
• Use variables NOT listed in AVAILABLE COLUMNS above
• Generate code with unavailable variables

REVERT requests: restore only the previously changed parameter; leave everything else.

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
        return clean_code(text)
