import pytest

from gotcha.domain.builder import SimuladoSpec
from gotcha.domain.grading import Outcome
from gotcha.domain.models import CaseStudy, Choice, ParsedBatch, Question, QuestionKind
from gotcha.qtypes.assets import AssetError
from gotcha.qtypes.blocks import ImageBlock
from gotcha.storage.db import Database
from gotcha.storage.library import Library
from gotcha.storage.sessions import Sessions, TimeExpired
from tests import imgs


def q(n: int, topic: int = 1, **kw: object) -> Question:
    base = dict(
        number=n, topic=topic, kind=QuestionKind.SINGLE, stem=f"<p>{topic}-{n}</p>",
        choices=[Choice(letter="A", text="a"), Choice(letter="B", text="b")], answer=["A"],
    )  # fmt: skip
    return Question.model_validate({**base, **kw})


@pytest.fixture()
def lib(tmp_path):  # type: ignore[no-untyped-def]
    return Library(Database(tmp_path / "t.db"))


def batch(*questions: Question, cases: list[CaseStudy] | None = None) -> ParsedBatch:
    return ParsedBatch(format="txt", title="t", questions=list(questions), cases=cases or [])


def test_drafts_are_not_questions_until_confirmed(lib: Library) -> None:
    b = lib.create_batch("a.txt", batch(q(1), q(2)))
    assert lib.list_exams() == []
    result = lib.confirm_batch(b.id, exam_name="Meu exame")
    assert result.added == 2 and result.skipped == 0
    exam = lib.list_exams()[0]
    assert exam.name == "Meu exame" and exam.question_count == 2


def test_confirmed_questions_are_stored_in_the_canonical_v2_model(lib: Library) -> None:
    exam_id = lib.confirm_batch(
        lib.create_batch("a", batch(q(1), q(2, kind="multiple", answer=["A", "B"]))).id,
        exam_name="E",
    ).exam_id
    stored = lib.questions([exam_id])
    assert [x.type for x in stored] == ["multiple_choice", "multiple_select"]
    assert all(x.schema_version == 2 and x.exam_id == exam_id for x in stored)


def test_confirm_dedupes_by_topic_and_number(lib: Library) -> None:
    exam_id = lib.confirm_batch(lib.create_batch("p1", batch(q(1), q(2))).id, exam_name="E").exam_id
    result = lib.confirm_batch(lib.create_batch("p2", batch(q(2), q(3), q(2, topic=2))).id, exam_id=exam_id)
    assert (result.added, result.skipped) == (2, 1)
    assert lib.list_exams()[0].question_count == 4


def test_undo_removes_only_that_batch(lib: Library) -> None:
    a = lib.create_batch("a", batch(q(1)))
    exam_id = lib.confirm_batch(a.id, exam_name="E").exam_id
    b = lib.create_batch("b", batch(q(2)))
    lib.confirm_batch(b.id, exam_id=exam_id)
    lib.undo_batch(b.id)
    assert lib.list_exams()[0].question_count == 1
    assert lib.get_batch(b.id).status == "undone"


def test_case_study_is_stored_once_with_sections(lib: Library) -> None:
    case = CaseStudy(id="case-1", text="<p>contexto</p>")
    b = lib.create_batch("a", batch(q(1, case_id="case-1"), q(2, case_id="case-1"), cases=[case]))
    exam_id = lib.confirm_batch(b.id, exam_name="E").exam_id
    questions = lib.questions([exam_id])
    assert len({x.case_id for x in questions}) == 1
    doc = lib.get_case(questions[0].case_id or "")
    assert "contexto" in doc.sections[0].blocks[0].html  # type: ignore[union-attr]


def test_edit_merge_and_delete_drafts(lib: Library) -> None:
    b = lib.create_batch("a", batch(q(1), q(2), q(3)))
    lib.update_draft(b.id, 0, {"answer": ["B"], "kind": "single"})
    assert lib.get_batch(b.id).questions[0].answer == ["B"]
    lib.merge_drafts(b.id, 0)
    merged = lib.get_batch(b.id).questions
    assert len(merged) == 2 and "<p>1-1</p>" in merged[0].stem and "<p>1-2</p>" in merged[0].stem
    lib.delete_draft(b.id, 1)
    assert len(lib.get_batch(b.id).questions) == 1


def test_assets_are_content_addressed_and_analyzed(lib: Library) -> None:
    data = imgs.png(40, 20)
    sha = lib.put_asset(data, name="a.png")
    assert lib.put_asset(data, name="outra.png") == sha  # mesma imagem = um recurso
    info = lib.asset_info(sha)
    assert (info.mime, info.width, info.height) == ("image/png", 40, 20)
    assert info.names == ["a.png", "outra.png"]
    assert lib.get_asset(sha) == data  # os bytes originais são preservados


def test_unsupported_asset_is_refused(lib: Library) -> None:
    with pytest.raises(AssetError):
        lib.put_asset(b"nao e imagem")


def test_svg_is_served_sanitized_and_original_is_kept(lib: Library) -> None:
    sha = lib.put_asset(imgs.SVG_EVIL, name="x.svg")
    view, mime = lib.get_asset_view(sha) or (b"", "")
    assert mime == "image/svg+xml" and b"script" not in view and b"onload" not in view
    assert lib.get_asset(sha) == imgs.SVG_EVIL


def test_image_shared_between_questions_has_two_references_and_orphans_are_listed(
    lib: Library,
) -> None:
    sha = lib.put_asset(imgs.png())
    orphan = lib.put_asset(imgs.png(5, 5, "blue"))
    b = lib.create_batch("a", batch(q(1), q(2)))
    exam_id = lib.confirm_batch(b.id, exam_name="E").exam_id
    for stored in lib.questions([exam_id]):
        lib.replace_question(
            stored.uid,
            stored.model_copy(update={"prompt": [*stored.prompt, ImageBlock(asset=sha, alt="x")]}),
        )
    assert lib.asset_refs(sha) == 2
    assert orphan in lib.orphan_assets() and sha not in lib.orphan_assets()


def test_rename_and_delete_exam(lib: Library) -> None:
    exam_id = lib.confirm_batch(lib.create_batch("a", batch(q(1))).id, exam_name="A").exam_id
    lib.rename_exam(exam_id, "B")
    assert lib.list_exams()[0].name == "B"
    lib.delete_exam(exam_id)
    assert lib.list_exams() == [] and lib.questions([exam_id]) == []


def test_replace_question_validates_semantics(lib: Library) -> None:
    exam_id = lib.confirm_batch(lib.create_batch("a", batch(q(1))).id, exam_name="E").exam_id
    stored = lib.questions([exam_id])[0]
    broken = stored.model_copy(update={"correct": "zzz"})
    with pytest.raises(ValueError, match="gabarito"):
        lib.replace_question(stored.uid, broken)


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture()
def env(tmp_path):  # type: ignore[no-untyped-def]
    db = Database(tmp_path / "s.db")
    clock = Clock()
    lib = Library(db)
    sessions = Sessions(db, lib, clock)
    exam_id = lib.confirm_batch(
        lib.create_batch("a", batch(q(1), q(2), q(3, kind="interactive", choices=[], answer=[]))).id,
        exam_name="E",
    ).exam_id
    return lib, sessions, clock, exam_id


def uids(lib: Library, exam_id: str) -> list[str]:
    return [x.uid for x in lib.questions([exam_id])]


def test_session_flow_and_result(env) -> None:  # type: ignore[no-untyped-def]
    lib, sessions, _, exam_id = env
    s = sessions.create(SimuladoSpec(exam_ids=[exam_id], shuffle=False))
    qids = uids(lib, exam_id)
    sessions.answer(s.id, qids[0], {"selected": ["A"]})
    sessions.answer(s.id, qids[1], {"selected": ["B"]})
    sessions.answer(s.id, qids[2], {"self_mark": True})
    result = sessions.finish(s.id)
    assert (result.summary.auto_correct, result.summary.auto_total) == (1, 2)
    assert result.summary.self_pct == 100.0
    assert result.details[1].outcome is Outcome.INCORRECT
    assert sessions.get(s.id).finished_at is not None


def test_invalid_response_is_refused_at_answer_time(env) -> None:  # type: ignore[no-untyped-def]
    lib, sessions, _, exam_id = env
    s = sessions.create(SimuladoSpec(exam_ids=[exam_id]))
    with pytest.raises(ValueError):
        sessions.answer(s.id, uids(lib, exam_id)[0], {"campo": 1})


def test_timer_is_backend_controlled(env) -> None:  # type: ignore[no-untyped-def]
    lib, sessions, clock, exam_id = env
    s = sessions.create(SimuladoSpec(exam_ids=[exam_id], mode="exam", time_limit_minutes=10))
    assert sessions.remaining_seconds(s.id) == 600
    clock.t += 100
    assert sessions.remaining_seconds(s.id) == 500
    sessions.pause(s.id)
    clock.t += 1000
    assert sessions.remaining_seconds(s.id) == 500
    sessions.resume(s.id)
    clock.t += 501
    assert sessions.remaining_seconds(s.id) == 0
    with pytest.raises(TimeExpired):
        sessions.answer(s.id, uids(lib, exam_id)[0], {"selected": ["A"]})


def test_history_feeds_the_builder(env) -> None:  # type: ignore[no-untyped-def]
    lib, sessions, _, exam_id = env
    s = sessions.create(SimuladoSpec(exam_ids=[exam_id], shuffle=False))
    qids = uids(lib, exam_id)
    sessions.answer(s.id, qids[0], {"selected": ["B"]})
    sessions.mark(s.id, qids[1], True)
    sessions.finish(s.id)
    again = sessions.create(SimuladoSpec(exam_ids=[exam_id], only="wrong"))
    assert again.question_ids == [qids[0]]
    marked = sessions.create(SimuladoSpec(exam_ids=[exam_id], only="marked"))
    assert marked.question_ids == [qids[1]]


def test_empty_selection_is_refused(env) -> None:  # type: ignore[no-untyped-def]
    _, sessions, _, exam_id = env
    with pytest.raises(ValueError, match="nenhuma questão"):
        sessions.create(SimuladoSpec(exam_ids=[exam_id], only="wrong"))
