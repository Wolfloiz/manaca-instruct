"""The one implementation of the `### Instrução / ### Entrada / ### Resposta` template
(specs/002 contracts/evaluation-presentation.md).

Training (`src/train_qlora.py`) and evaluation (`src/evaluate.py`) both render prompts
through this function so the two sides cannot drift apart again — feature 001 trained
with `### Entrada:` on 2,696/3,956 examples while the evaluator never produced that block.
"""

from __future__ import annotations


def format_prompt(instruction: str, input: str = "", output: str | None = None) -> str:
    parts = [f"### Instrução:\n{instruction}"]
    if input:
        parts.append(f"### Entrada:\n{input}")
    parts.append("### Resposta:\n" + (output if output is not None else ""))
    return "\n\n".join(parts)
