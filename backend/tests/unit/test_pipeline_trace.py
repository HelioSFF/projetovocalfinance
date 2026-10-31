import json
from decimal import Decimal
from types import SimpleNamespace

from app.schemas.ai import DecisionResult, ExtractionResult
from app.services.pipeline_trace import NullTrace, PipelineTrace
from tests.support.fakes import (
    choice_answer_ns,
    decision_response_ns,
    extraction_response_ns,
    predicate_answer_ns,
    refusal_answer_ns,
    rewrite_response_ns,
    standard_answers_ns,
    transcription_result_ns,
)


def make_record():
    return SimpleNamespace(
        type="expense",
        category="food",
        quantity=Decimal("3"),
        unit_price=Decimal("5.00"),
        total=Decimal("15.00"),
    )


def make_decision():
    return DecisionResult(plausible=0.97, is_financial=0.95, record_type="expense", category="food")


def drive_accepted(trace, text="Comprei três cafés de cinco reais."):
    with trace.stage("validate"):
        pass
    with trace.stage("transcribe"):
        pass
    trace.set_transcription("gpt-transcribe", text, transcription_result_ns(text, seconds=4.0))
    trace.start_attempt(1, "transcript", text)
    with trace.stage("analyze", attempt=1):
        with trace.stage("decision", attempt=1, parallel=True):
            pass
        with trace.stage("extraction", attempt=1, parallel=True):
            pass
    decision_response = decision_response_ns(standard_answers_ns())
    extraction_response = extraction_response_ns({"item": "café", "quantity": 3, "unit_price": 5, "stated_total": 15})
    trace.set_decision(1, "gpt-6-luna", decision_response)
    trace.set_extraction(1, "gpt-6-luna", None, extraction_response, '{"item":"café"}', {"item": "café"})
    trace.set_acceptance(1, make_decision(), ExtractionResult(item="café", quantity=3, unit_price=5.0, stated_total=15.0), 0.6)
    with trace.stage("rules"):
        pass
    with trace.stage("db_insert"):
        pass
    trace.set_result(make_decision(), make_record(), "unit_price")
    return trace.to_dict()


def test_null_trace_returns_none():
    trace = NullTrace()
    assert trace.enabled is False
    with trace.stage("validate"):
        pass
    trace.start_attempt(1, "transcript", "text")
    trace.set_transcription("gpt-transcribe", "text", None)
    trace.fail("NOT_UNDERSTOOD")
    assert trace.to_dict() is None


def test_direct_accept_stages_order_and_parallel_flags():
    debug = drive_accepted(PipelineTrace(0.6, None))
    names = [stage["name"] for stage in debug["timing"]["stages"]]
    assert names == ["validate", "transcribe", "analyze", "decision", "extraction", "rules", "db_insert"]
    by_name = {stage["name"]: stage for stage in debug["timing"]["stages"]}
    assert by_name["decision"]["parallel"] is True
    assert by_name["extraction"]["parallel"] is True
    assert by_name["analyze"]["parallel"] is False
    assert by_name["decision"]["attempt"] == 1
    assert by_name["validate"]["attempt"] is None
    children = [by_name["decision"]["duration_ms"], by_name["extraction"]["duration_ms"]]
    assert by_name["analyze"]["duration_ms"] >= max(children)
    assert len(debug["attempts"]) == 1
    assert debug["fallback"]["used"] is False
    assert debug["outcome"] == "accepted"
    assert debug["failure_code"] is None
    assert debug["result"]["formula"] == "3 × 5.00 = 15.00"
    assert debug["result"]["total"] == "15.00"
    assert debug["costs"]["total_usd"] == "0.0005126"
    assert debug["costs"]["estimated"] is False


def test_fallback_registers_two_attempts_with_rewrite_between():
    trace = PipelineTrace(0.6, None)
    trace.start_attempt(1, "transcript", "bla")
    trace.set_decision(1, "gpt-6-luna", decision_response_ns(standard_answers_ns(financial=0.1)))
    trace.set_extraction(1, "gpt-6-luna", None, extraction_response_ns({"item": "x", "quantity": 1, "unit_price": 2, "stated_total": 2}), '{"item":"x"}', {"item": "x"})
    trace.set_acceptance(1, DecisionResult(plausible=0.9, is_financial=0.1), ExtractionResult(item="x", quantity=1, unit_price=2.0, stated_total=2.0), 0.6)
    with trace.stage("rewrite"):
        pass
    trace.set_fallback("deepseek-flash", "bla", rewrite_response_ns("blá reescrito"), "blá reescrito")
    trace.start_attempt(2, "rewrite", "blá reescrito")
    trace.fail("NOT_FINANCIAL")
    debug = trace.to_dict()
    assert [attempt["number"] for attempt in debug["attempts"]] == [1, 2]
    assert [attempt["source"] for attempt in debug["attempts"]] == ["transcript", "rewrite"]
    assert debug["fallback"]["used"] is True
    assert debug["fallback"]["rewritten_text"] == "blá reescrito"
    assert debug["outcome"] == "rejected"
    assert debug["failure_code"] == "NOT_FINANCIAL"
    assert debug["result"] is None


def test_summarize_answers_top3_desc_and_refusal():
    from app.schemas.debug import summarize_decision_answers

    answers = [
        predicate_answer_ns("plausible", 0.97),
        refusal_answer_ns("is_financial"),
        choice_answer_ns("category", "food", 0.91, [("groceries", 0.06), ("food", 0.91), ("leisure", 0.01), ("health", 0.02)]),
    ]
    summarized = summarize_decision_answers(answers)
    assert summarized[0] == {
        "name": "plausible",
        "type": "predicate",
        "probability": 0.97,
        "choice": None,
        "confidence": None,
        "top_probabilities": [],
        "refusal": None,
    }
    assert summarized[1]["type"] == "refusal"
    assert summarized[1]["probability"] is None
    top = summarized[2]["top_probabilities"]
    assert [entry["value"] for entry in top] == ["food", "groceries", "health"]
    assert summarized[2]["choice"] == "food"


def test_provider_failure_stage_hides_secret():
    trace = PipelineTrace(0.6, None)
    with trace.stage("validate"):
        pass
    try:
        with trace.stage("transcribe"):
            raise RuntimeError("boom sk-test-SECRET should not leak")
    except RuntimeError:
        pass
    trace.fail("AI_UNAVAILABLE")
    debug = trace.to_dict()
    assert "sk-test-SECRET" not in json.dumps(debug)
    assert debug["timing"]["stages"][-1]["error"] == "RuntimeError"
    assert "http_status" not in debug["timing"]["stages"][-1]
    assert debug["outcome"] == "provider_error"


def test_unknown_model_line_and_total_ignores_none():
    trace = PipelineTrace(0.6, None)
    trace.start_attempt(1, "transcript", "text")
    trace.set_decision(1, "gpt-6-luna", decision_response_ns(standard_answers_ns()))
    trace.set_extraction(
        1, "gpt-xyz", None, extraction_response_ns({"item": "x", "quantity": 1, "unit_price": 2, "stated_total": 2}), "{}", {"item": "x"}
    )
    trace.set_acceptance(1, make_decision(), ExtractionResult(item="x", quantity=1, unit_price=2.0, stated_total=2.0), 0.6)
    trace.set_fallback("deepseek-flash", "text", rewrite_response_ns("texto"), "texto")
    trace.set_result(make_decision(), make_record(), "unit_price")
    debug = trace.to_dict()
    lines = {line["stage"]: line for line in debug["costs"]["lines"]}
    assert lines["extraction"]["usd"] is None
    assert lines["extraction"]["estimated"] is True
    assert lines["rewrite"]["estimated"] is True
    assert debug["costs"]["total_usd"] == "0.0001950"
    assert debug["costs"]["estimated"] is True
