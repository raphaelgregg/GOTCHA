import pytest

from gotcha.importers import Source
from gotcha.sandbox import SandboxError, SandboxTimeout, parse_isolated, run_isolated
from tests.html_fixture import card, page


def test_runs_function_in_subprocess() -> None:
    assert run_isolated("tests.sandbox_helpers:double", 21, timeout=20) == 42


def test_timeout_kills_the_process() -> None:
    with pytest.raises(SandboxTimeout):
        run_isolated("tests.sandbox_helpers:sleeper", 30, timeout=1)


def test_network_is_blocked_inside_sandbox() -> None:
    assert run_isolated("tests.sandbox_helpers:try_network", timeout=20).startswith("bloqueado")


def test_exceptions_are_reported_without_crashing_the_parent() -> None:
    with pytest.raises(SandboxError, match="falha interna"):
        run_isolated("tests.sandbox_helpers:boom", timeout=20)


def test_parse_isolated_returns_batch_and_assets() -> None:
    html = page(card(1, answer_img="r.png"))
    batch = parse_isolated(Source(filename="p.html", data=html, assets={"r.png": b"IMG"}), "html")
    assert batch.questions[0].images[0].sha is not None
    assert list(batch.assets.values()) == [b"IMG"]
