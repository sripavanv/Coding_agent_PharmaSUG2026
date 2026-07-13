"""
Graph Customizer Module
Handles iterative, dialogue-based modifications to an existing swimmer plot.
"""

import re
from datetime import datetime

from utils import clean_code

MODEL = "claude-sonnet-4-6"

# Deterministic verb-intent detection used by the add/remove category guards.
# Stemmed (\w*) so inflections match: "removing", "excluded", "dropped", "adding", etc.
# \b(remove)\b alone does NOT match "removing" -- no word boundary between the stem
# and its suffix -- which was silently disabling the gate for natural phrasing.
_REMOVE_INTENT = re.compile(
    r'\b(remov\w*|delet\w*|dropp?\w*|get\s+rid\s+of|took?\s+off|hidd?\w*|exclud\w*|without)\b',
    re.I)
_ADD_INTENT = re.compile(
    r'\b(add\w*|overlay\w*|includ\w*|show\w*|plott?\w*|putt?\w*|introduc\w*|display\w*)\b',
    re.I)


class GraphCustomizer:
    def __init__(self, claude_client=None, ai_enabled=False):
        self.claude_client = claude_client
        self.ai_enabled    = ai_enabled
        self.conversation_history = []
        self.current_plot_context = {
            'code': '', 'x_var': '', 'y_var': '', 'hbar_var': '',
            'processed_data_shape': None, 'available_columns': []
        }

    def set_plot_context(self, code, x_var, y_var, hbar_var,
                         processed_data_shape, available_columns=None):
        """Set a new plot context and reset conversation history."""
        self.current_plot_context = {
            'code': code, 'x_var': x_var, 'y_var': y_var,
            'hbar_var': hbar_var, 'processed_data_shape': processed_data_shape,
            'available_columns': available_columns or []
        }
        self.conversation_history.clear()

    # ── Public API ─────────────────────────────────────────────────────────────

    def customize_plot_interactively(self, user_request, system_hint=None, category=None):
        """Apply a natural-language modification to the current plot code.

        category : optional scope key ('add_overlay', 'remove_overlay', 'axes',
                   'markers', 'title', 'legend'). For 'add_overlay'/'remove_overlay'
                   the add/remove contract is enforced deterministically — before the
                   AI call (verb-intent gate) and after (structural trace diff) — so
                   the prompt is no longer the only guard.

        Special AI response prefixes — no code change, message shown in dialogue:
          ALREADY_OVERLAID: <col>    — column already has a trace
          PROTECTED_TRACE: <name>    — structural trace, cannot remove
          WRONG_CATEGORY: <message>  — request intent contradicts selected category
          CLARIFICATION_NEEDED: <q>  — ambiguous request
        """
        if not self.ai_enabled:
            return "# Error: AI required for interactive customization", ["AI required"], "error"
        if not self.current_plot_context['code']:
            return "# Error: No plot context — generate a plot first.", ["No context"], "error"

        self._append_history('user', user_request)
        print(f"\n=== INTERACTIVE CUSTOMIZATION ===\nRequest: {user_request}  (category={category})")

        code_before = self.current_plot_context['code']

        # ── Deterministic intent gate — runs before any AI call ────────────────
        if category in ('add_overlay', 'remove_overlay'):
            mismatch = self._precheck_intent(category, user_request)
            if mismatch:
                msg = self._msg_wrong_category(mismatch)
                self._append_history('assistant', msg)
                print(f"⛔ Intent gate blocked request: {mismatch}")
                return code_before, [msg], "wrong_category"

        try:
            traces_before = self._get_overlay_traces(code_before)

            response_code = self._apply_customization(
                user_request, system_hint=system_hint, category=category)

            # ── Special single-line AI responses — no code change ──────────────
            # Tolerant detection: ignore leading blank lines and comment hashes,
            # match case-insensitively, and accept the detail on the same line
            # (KEY: detail) or on the following line.
            special = {
                "ALREADY_OVERLAID":     (self._msg_already_overlaid, "already_overlaid"),
                "PROTECTED_TRACE":      (self._msg_protected_trace,  "protected_trace"),
                "WRONG_CATEGORY":       (self._msg_wrong_category,   "wrong_category"),
                "CLARIFICATION_NEEDED": (self._msg_clarification,    "clarification_needed"),
            }
            first_line  = next((l.strip() for l in response_code.splitlines() if l.strip()), "")
            marker_line = first_line.lstrip("#").strip()
            for key, (handler, status) in special.items():
                if marker_line.upper().startswith(key):
                    detail = marker_line[len(key):].lstrip(": ").strip()
                    msg    = handler(detail)
                    self._append_history('assistant', msg)
                    return code_before, [msg], status

            # ── Post-AI column validation (safety net) ─────────────────────────
            # Only 'add_overlay' is allowed to introduce a new dataset column, so
            # this check only makes sense for that category. Running it for
            # axes/markers/title/legend was a false-positive source: those
            # categories legitimately emit bracket string literals that aren't
            # column names at all (fig['layout']['xaxis'], 'title', 'closest',
            # 'paper', 'italic', ...), and the check has no way to tell those
            # apart from a real column reference — so valid edits in those four
            # categories were being silently reverted as "unknown column".
            if category == 'add_overlay':
                available_cols = self.current_plot_context.get('available_columns', [])
                ok, bad_cols   = self._check_new_column_refs(response_code, available_cols)

                if not ok:
                    self.current_plot_context['code'] = code_before
                    msg = (
                        f"⚠ Column(s) not found in dataset: {', '.join(bad_cols)}.\n"
                        f"Available: {', '.join(available_cols[:10])}{'...' if len(available_cols) > 10 else ''}.\n"
                        f"Plot kept as-is."
                    )
                    print(f"⚠ Column check failed — reverted: {bad_cols}")
                    self._append_history('assistant', msg)
                    return code_before, [msg], "invalid_columns"

            # ── Structural integrity check (all categories) ────────────────────
            # The HBAR go.Bar trace is mandatory and must never be dropped, no
            # matter which category was edited (axes/markers/title/legend included).
            if not self._has_mandatory_structure(response_code):
                self.current_plot_context['code'] = code_before
                if self._looks_like_plot_code(response_code):
                    # It IS plot code, but the mandatory bar trace went missing.
                    msg = ("⚠ The change would remove the mandatory treatment-duration "
                           "bars (go.Bar). Plot kept as-is.")
                    print("⛔ Structural check: plot code dropped go.Bar — reverted.")
                    status = "invalid_structure"
                else:
                    # Not a complete plot — almost always an unknown column or an
                    # unclear request, so the model returned a fragment / prose.
                    msg = ("⚠ Couldn't apply that. The request may reference a column "
                           "that isn't in your Step 2 selection, or it wasn't specific "
                           "enough. Try naming an available column "
                           "(e.g. \u201Cadd ADTTE as circle markers\u201D). Plot kept as-is.")
                    print("⛔ Structural check: response was not complete plot code "
                          "(likely unknown column / unclear request) — reverted.")
                    status = "unclear_request"
                self._append_history('assistant', msg)
                return code_before, [msg], status

            # ── Structural contract check (deterministic diff) ─────────────────
            if category in ('add_overlay', 'remove_overlay'):
                traces_after = self._get_overlay_traces(response_code)
                ok2, msg2 = self._enforce_contract(category, traces_before, traces_after)
                if not ok2:
                    self.current_plot_context['code'] = code_before
                    print(f"⛔ Contract violation — reverted: {msg2}")
                    self._append_history('assistant', msg2)
                    return code_before, [msg2], "contract_violation"

            # ── Accept ─────────────────────────────────────────────────────────
            self.current_plot_context['code'] = response_code
            self._append_history('assistant',
                f"Applied: {user_request[:100]}{'...' if len(user_request) > 100 else ''}")
            return response_code, ["Customization applied"], "customized"

        except Exception as e:
            print(f"⚠ Customization failed: {e}")
            return code_before, [f"Error: {e}"], "error"

    def get_conversation_history(self):
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        self.conversation_history.clear()

    # ── Message builders ───────────────────────────────────────────────────────

    def _msg_already_overlaid(self, detail):
        return (
            f"⚠ '{detail}' is already overlaid in the current plot.\n"
            f"To change its appearance, use Markers & Bars or Legend. No changes made."
        )

    def _msg_protected_trace(self, detail):
        return (
            f"⚠ '{detail}' is a structural trace (X-axis, Y-axis, or HBAR) and cannot be removed.\n"
            f"Only non-structural overlay traces can be removed. No changes made."
        )

    def _msg_wrong_category(self, detail):
        return f"⚠ Wrong category: {detail}. No changes made."

    def _msg_clarification(self, detail):
        return f"❓ {detail}"

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _append_history(self, role, content):
        """Append with plain string timestamp — safe for JSON / dcc.Store."""
        self.conversation_history.append({
            'type':      role,
            'content':   content,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
        })

    def _get_current_overlay_traces(self):
        """Overlay traces in the CURRENT context code (backwards-compatible wrapper)."""
        return self._get_overlay_traces(self.current_plot_context.get('code', ''))

    def _get_overlay_traces(self, code):
        """Return list of (trace_name, col_name) for every non-Bar add_trace in `code`.
        Uses paren-counting so nested dicts/filters don't truncate the block.
        """
        code    = code or ''
        results = []
        for m in re.finditer(r'fig\.add_trace\s*\(\s*go\.(?!Bar\b)\w+\s*\(', code, re.DOTALL):
            start = m.end()
            depth = 1
            i     = start
            while i < len(code) and depth > 0:
                if   code[i] == '(': depth += 1
                elif code[i] == ')': depth -= 1
                i += 1
            block      = code[start:i - 1]
            name_match = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", block)
            # x= last bracket on that line covers both simple and filtered patterns
            x_match    = re.search(r"x\s*=\s*[^\n,]+\[['\"]([^'\"]+)['\"]\]", block)
            if name_match:
                results.append((
                    name_match.group(1),
                    x_match.group(1) if x_match else name_match.group(1),
                ))
        return results

    # ── Deterministic category guards ──────────────────────────────────────────

    def _precheck_intent(self, category, text):
        """Verb-intent gate. Returns a WRONG_CATEGORY detail string on mismatch, else None.
        Catches the common case (e.g. 'remove X' typed in the Add Overlay box) before
        an AI call is spent — without relying on the model to police itself.
        Requests containing BOTH verbs are deferred to the AI (and backstopped by the
        structural contract check).
        """
        has_remove = bool(_REMOVE_INTENT.search(text))
        has_add    = bool(_ADD_INTENT.search(text))
        if category == 'add_overlay' and has_remove and not has_add:
            return "Use the Remove Overlay category to remove a trace."
        if category == 'remove_overlay' and has_add and not has_remove:
            return "Use the Add Overlay category to add a new overlay."
        return None

    def _enforce_contract(self, category, before, after):
        """Structural diff check on the actual code change — the real safety net.
        Even if the model ignores every instruction, this inspects what changed.
        Returns (ok, message); message is None when ok.
        """
        names_before = {n for n, _ in before}
        names_after  = {n for n, _ in after}
        added   = sorted(names_after - names_before)
        removed = sorted(names_before - names_after)

        if category == 'add_overlay' and (removed or len(added) != 1):
            return False, (
                f"⚠ Add Overlay must add exactly one overlay and remove none "
                f"(added={added or 'none'}, removed={removed or 'none'}). Plot kept as-is."
            )
        if category == 'remove_overlay' and (added or len(removed) != 1):
            return False, (
                f"⚠ Remove Overlay must remove exactly one overlay and add none "
                f"(added={added or 'none'}, removed={removed or 'none'}). Plot kept as-is."
            )
        return True, None

    def _has_mandatory_structure(self, code):
        """True if the code still contains the mandatory HBAR bar trace.
        Mirrors the generator's debug invariant: a swimmer plot must always keep
        its go.Bar treatment-duration trace. Cheap textual check, no execution.
        """
        code = code or ''
        return ('go.Bar' in code) and ('fig.add_trace' in code)

    def _looks_like_plot_code(self, code):
        """True if the response resembles a full Plotly figure (has a figure and/or
        traces), vs. a fragment, prose, or empty reply. Used only to choose the
        right user-facing message when the mandatory-structure check fails.
        """
        code = code or ''
        return ('go.Figure' in code) or ('fig.add_trace' in code)

    def _check_new_column_refs(self, new_code, available_cols):
        """Check every bracket column reference in AI code against available_cols.
        Covers both UPPER and lowercase column names.
        """
        if not available_cols:
            return True, []

        bracket_refs = re.findall(r'\w+\[["\']([^"\']+)["\']\]', new_code)

        # Plausible column names: 2+ chars, starts with letter, no spaces
        col_refs = {
            c for c in bracket_refs
            if len(c) >= 2 and c[0].isalpha() and ' ' not in c
        }

        # Exclude obvious non-column string literals (plotly params, css values, etc.)
        exclude_patterns = re.compile(
            r'^(markers?|lines?|rgba?|rgb|#[0-9a-fA-F]+|circle|square|diamond|'
            r'triangle.*|star|cross|outside|inside|auto|top|bottom|left|right|'
            r'linear|category|date|log|h|v|overlay|group|stack|text|none|'
            r'solid|dash|dot|longdash|dashdot|longdashdot)$',
            re.IGNORECASE
        )
        col_refs = {c for c in col_refs if not exclude_patterns.match(c)}

        available_set = set(available_cols)
        bad = [c for c in sorted(col_refs) if c not in available_set]

        print(f"DEBUG col_refs: {col_refs}")
        print(f"DEBUG bad_cols: {bad}")
        return (len(bad) == 0), bad

    # ── AI call ────────────────────────────────────────────────────────────────

    def _apply_customization(self, user_request, system_hint=None, category=None):
        ctx            = self.current_plot_context
        y, x, hbar     = ctx['y_var'], ctx['x_var'], ctx['hbar_var']
        available_cols = ctx.get('available_columns', [])

        # ── Two explicit lists given to Claude ────────────────────────────────
        # List 1: dataset columns available to add as overlays
        addable = [c for c in available_cols if c not in {x, y, hbar, 'SUBJID', 'USUBJID'}]
        cols_str = (
            "COLUMNS AVAILABLE TO ADD AS OVERLAYS (from Step 2 selection):\n"
            + "\n".join(f"  • {c}" for c in addable)
            + "\n\nSTRICT RULE: ONLY these columns may be used in new overlay traces.\n"
            "Do NOT introduce any column not listed above — not even if it sounds plausible."
            if addable
            else f"No additional columns selected. Only structural vars: {x}, {y}, {hbar}."
        )

        # List 2: overlay traces currently in the code (removable)
        current_overlays = self._get_current_overlay_traces()
        structural_names = {'Treatment Duration', hbar, x, y}
        removable = [(n, c) for n, c in current_overlays if n not in structural_names]
        if removable:
            removable_str = (
                "OVERLAY TRACES CURRENTLY IN THE PLOT (these and ONLY these can be removed):\n"
                + "\n".join(f"  • name='{n}'  (column: {c})" for n, c in removable)
            )
        else:
            removable_str = "OVERLAY TRACES CURRENTLY IN THE PLOT: none (only the HBAR exists)."

        # Already-overlaid column names — for ALREADY_OVERLAID detection
        overlaid_cols = {c for _, c in current_overlays}
        overlaid_str  = (
            "COLUMNS ALREADY OVERLAID (do NOT add these again):\n"
            + "\n".join(f"  • {c}" for c in sorted(overlaid_cols))
            if overlaid_cols else "COLUMNS ALREADY OVERLAID: none."
        )

        scope_section = ""
        if system_hint:
            scope_section = (
                "\n═══════════════════════════════════════════════════════════════════\n"
                "CATEGORY SCOPE — STRICTLY ENFORCED\n"
                "═══════════════════════════════════════════════════════════════════\n"
                f"{system_hint}\n"
                "═══════════════════════════════════════════════════════════════════\n"
            )

        # ── Scope-aware overlay rules ─────────────────────────────────────────
        # Ship only the rules relevant to this category so the prompt body never
        # contradicts the scope hint. Backstopped by the deterministic contract
        # check in customize_plot_interactively.
        add_rules = (
            "ADD OVERLAY:\n"
            "  • Only use columns from \"COLUMNS AVAILABLE TO ADD AS OVERLAYS\" above.\n"
            "  • x= MUST be a numeric/day column. NEVER a categorical string column.\n"
            "  • Always filter non-null: plot_data[plot_data['COL'].notna()].\n"
            "  • DO NOT create subject_positions dicts or numeric Y index mappings.\n"
            "  • If column is already in \"COLUMNS ALREADY OVERLAID\" → respond ALREADY_OVERLAID."
        )
        remove_rules = (
            "REMOVE OVERLAY:\n"
            "  • Only remove traces listed in \"OVERLAY TRACES CURRENTLY IN THE PLOT\" above.\n"
            "  • If trace name is not in that list → respond CLARIFICATION_NEEDED.\n"
            f"  • NEVER remove go.Bar traces or structural variables ({x}, {y}, {hbar}).\n"
            "  • If user asks to remove a structural trace → respond PROTECTED_TRACE."
        )
        if category == 'add_overlay':
            overlay_rules = (add_rules +
                "\n\nThis is an ADD-ONLY operation. Add exactly one overlay; do NOT remove "
                "or alter any existing trace. If the request asks to remove/delete anything → "
                "respond WRONG_CATEGORY: Use the Remove Overlay category to remove a trace.")
        elif category == 'remove_overlay':
            overlay_rules = (remove_rules +
                "\n\nThis is a REMOVE-ONLY operation. Remove exactly one overlay; do NOT add "
                "or alter any other trace. If the request asks to add/create anything → "
                "respond WRONG_CATEGORY: Use the Add Overlay category to add an overlay.")
        else:
            overlay_rules = add_rules + "\n\n" + remove_rules

        prompt = f"""MODIFY the existing swimmer plot code — do NOT regenerate from scratch.
{scope_section}
═══════════════════════════════════════════════════════════════════
FUNDAMENTAL SWIMMER PLOT STRUCTURE — NEVER VIOLATE
═══════════════════════════════════════════════════════════════════
1. Y-AXIS: {y} column — categorical subject IDs, one tick per subject.
   NEVER use numeric indices. NEVER remove subjects.
   fig.update_yaxes(type='category') — ALWAYS category, never change.

2. HBAR (Horizontal Bars):
   go.Bar(orientation='h', y=hbar_data['{y}'], x=hbar_data['{hbar}'])
   ONE bar per subject — MANDATORY. Cannot be removed or restructured.
   hbar_data = plot_data.drop_duplicates(subset=['{y}']) — NEVER change this.

3. X-AXIS: {x} column — numeric/linear time scale. NEVER categorical.
   fig.update_xaxes(type='linear') — ALWAYS linear, never change.

4. OVERLAYS: go.Scatter traces using plot_data (ALL rows, not hbar_data).
   y= MUST reference {y} column values — NEVER numeric indices or y_pos variables.
   x= MUST be a numeric/day column — NEVER a categorical string column.
   DO NOT create subject_positions dicts or computed Y index mappings.

5. MODIFY ONLY — do not rewrite imports, variable names, data loading,
   or the plot_data / hbar_data setup. Add or change only what is requested.

CURRENT PLOT CONTEXT:
- Variables: X={x}, Y={y}, HBAR={hbar}
- Data shape: {ctx['processed_data_shape']}

{cols_str}

{overlaid_str}

{removable_str}

CURRENT CODE (reflects all previous customizations — this is the complete state):
```python
{ctx['code']}
```

USER REQUEST: {user_request}

═══════════════════════════════════════════════════════════════════
OVERLAY RULES
═══════════════════════════════════════════════════════════════════
{overlay_rules}

═══════════════════════════════════════════════════════════════════
MODIFICATION GUIDELINES
═══════════════════════════════════════════════════════════════════
ALLOWED:
• Colors, sizes, borders, symbols, opacity on existing traces
• Hover info, annotations, title/labels, legend
• Add new go.Scatter() overlay — ONLY from available columns above
• Remove existing non-structural overlay traces — ONLY from removable list above
• Change layout parameters

FORBIDDEN:
• Delete or structurally modify go.Bar() traces
• Change y={y} to numeric indices, y_pos variables, or any computed mapping
• Change fig.update_yaxes(type='category') or fig.update_xaxes(type='linear')
• Modify plot_data / hbar_data setup lines
• Regenerate or rewrite the entire code from scratch
• Use any column NOT in the available list above

═══════════════════════════════════════════════════════════════════
SPECIAL RESPONSES — return ONLY the prefix line, no code, when:
═══════════════════════════════════════════════════════════════════
ALREADY_OVERLAID: <column_name>
  → Column already has a go.Scatter trace in the current code.

PROTECTED_TRACE: <trace_name>
  → User asked to remove a structural trace ({x}, {y}, {hbar}, Treatment Duration).

WRONG_CATEGORY: <one-sentence explanation>
  → The request intent contradicts the selected category.
    Examples:
    - Remove Overlay category but request says add/create a trace →
      WRONG_CATEGORY: Use the Add Overlay category to add a trace.
    - Add Overlay category but request says remove/delete a trace →
      WRONG_CATEGORY: Use the Remove Overlay category to remove a trace.
    - Axes category but request mentions adding a data variable as overlay →
      WRONG_CATEGORY: Use the Add Overlay category to overlay a variable.

CLARIFICATION_NEEDED: <one specific question>
  → Request is too ambiguous to act on safely.

Otherwise return the COMPLETE modified Python code with all traces intact.
REVERT requests: restore only the previously changed parameter; leave everything else."""

        message = self.claude_client.messages.create(
            model=MODEL, max_tokens=4000, temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        response = message.content[0].text.strip()

        for prefix, internal in [
            ("ALREADY_OVERLAID:",     "# ALREADY_OVERLAID"),
            ("PROTECTED_TRACE:",      "# PROTECTED_TRACE"),
            ("WRONG_CATEGORY:",       "# WRONG_CATEGORY"),
            ("CLARIFICATION_NEEDED:", "# CLARIFICATION_NEEDED"),
        ]:
            if response.startswith(prefix):
                detail = response.split(":", 1)[1].strip()
                print(f"AI special response [{prefix}] {detail}")
                return f"{internal}\n# {detail}"

        return self._clean_code(response)

    def _clean_code(self, text):
        return clean_code(text)
