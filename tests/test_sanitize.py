"""Todo HTML importado é sanitizado antes de ser exibido."""

from gotcha.domain.sanitize import clean_html, to_plain_text


def test_removes_script_and_handlers() -> None:
    html = '<p onclick="x()">oi</p><script>alert(1)</script>'
    out = clean_html(html)
    assert "script" not in out and "onclick" not in out and "oi" in out


def test_keeps_tables_and_code() -> None:
    html = "<table><tr><td>a</td></tr></table><pre><code>SELECT 1</code></pre>"
    out = clean_html(html)
    assert "<table>" in out and "<pre>" in out and "SELECT 1" in out


def test_removes_javascript_links() -> None:
    assert "javascript" not in clean_html('<a href="javascript:alert(1)">x</a>')


def test_removes_images_and_iframes() -> None:
    out = clean_html('<img src="http://evil/x.png"><iframe src="http://evil"></iframe>')
    assert "img" not in out and "iframe" not in out


def test_plain_text_collapses_whitespace() -> None:
    assert to_plain_text("<p>a   <b>b</b></p>\n<p>c</p>") == "a b\nc"
