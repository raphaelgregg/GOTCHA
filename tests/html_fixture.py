"""Gera HTML sintético que imita só a FORMA de uma página salva de simulado."""

from __future__ import annotations

from html import escape


def card(
    number: int,
    topic: int = 1,
    stem: str = "Enunciado",
    choices: list[str] | None = None,
    answer: str = "",
    answer_img: str | None = None,
    voted: str = "",
    stem_img: str | None = None,
) -> str:
    lis = ""
    for i, text in enumerate(choices or []):
        letter = "ABCDEF"[i]
        badge = (
            '<span class="badge most-voted-answer-badge">Most Voted</span>'
            if letter in voted
            else ""
        )
        lis += (
            f'<li class="multi-choice-item" data-choice-letter="{letter}">'
            f'<span class="multi-choice-letter">{letter}.</span> {escape(text)}{badge}</li>'
        )
    choices_html = f'<div class="question-choices-container"><ul>{lis}</ul></div>' if lis else ""
    img = f'<img class="in-exam-image" src="./page_files/{stem_img}">' if stem_img else ""
    ans_img = f'<img src="./page_files/{answer_img}">' if answer_img else ""
    return f"""
<div class="card exam-question-card">
  <div class="card-header">Question #{number}
    <span class="question-title-topic">Topic {topic}</span></div>
  <div class="card-body question-body">
    <p class="card-text">{stem}<br>{img}</p>
    {choices_html}
    <a class="btn reveal-solution">Reveal Solution</a>
    <a class="btn question-discussion-button">Discussion <span class="badge">3</span></a>
    <p class="card-text question-answer">
      <span class="correct-answer-box"><strong>Correct Answer:</strong>
        <span class="correct-answer">{answer}{ans_img}</span></span>
      <span class="answer-description"></span>
    </p>
    <div class="voting-summary"><div class="vote-bar">50%</div></div>
  </div>
</div>"""


def page(*cards: str, extra: str = "") -> bytes:
    body = "".join(cards)
    return (
        f"<html><head><meta charset='utf-8'><script>var x=1;</script></head>"
        f"<body><div class='questions-container'>{body}</div>{extra}</body></html>"
    ).encode()
