"""
Shared utilities for the Swimmer Plot Generator.
"""

import os
import pandas as pd

MODEL = "claude-sonnet-4-6"


def clean_code(text: str) -> str:
    """Strip markdown fences and remove fig.show() for Dash compatibility."""
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
    return text.replace('fig.show()', '# fig.show() removed for Dash integration').strip()


def call_ai(client, prompt, max_tokens=4000, temperature=0.1) -> str:
    """Call Claude, strip the response, and clean code fences. Returns clean code string."""
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return clean_code(msg.content[0].text.strip())


def next_save_path(prefix: str, ext: str, directory: str = "./saved_code") -> str:
    """Return the next available auto-numbered file path under directory.

    Example: next_save_path('swimmer_plot', 'py') → './saved_code/swimmer_plot_1.py'
    """
    os.makedirs(directory, exist_ok=True)
    i = 1
    while os.path.exists(f"{directory}/{prefix}_{i}.{ext}"):
        i += 1
    return f"{directory}/{prefix}_{i}.{ext}"
