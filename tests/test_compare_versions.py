import json

import pytest

from eval import compare_versions
from eval.stats import mcnemar, wald_ci, wilson_ci
from tests.test_run_e2e import FakeProvider, make_cases, run


@pytest.fixture
def run_dir(tmp_path):
    cases_path, cases = make_cases(tmp_path, n=12)
    # v3 passes 10, v2 passes 7, v1 passes 3: best two are v3 and v2 with discordant pairs.
    passes = {}
    for i, c in enumerate(cases):
        passes[("v3", c["text"])] = i < 10
        passes[("v2", c["text"])] = i % 2 == 0 or i in (3, 11)
        passes[("v1", c["text"])] = i < 3
    run(tmp_path, FakeProvider(passes=passes), cases_path)
    return tmp_path / "out"


def vector(run_dir, version):
    rows = [json.loads(l) for l in (run_dir / f"judged_{version}.jsonl").read_text().splitlines()]
    return [r["label"] == "pass" for r in rows]


def test_numbers_match_eval_stats(run_dir):
    comp = json.loads((run_dir / "comparison.json").read_text())
    assert comp["ranking"] == ["v3", "v2", "v1"] and comp["best_version"] == "v3" and not comp["tie"]
    for v in ("v1", "v2", "v3"):
        vec = vector(run_dir, v)
        acc = comp["versions"][v]["accuracy"]
        p, lo, hi = wald_ci(sum(vec), len(vec))
        _, wlo, whi = wilson_ci(sum(vec), len(vec))
        assert (acc["value"], acc["wald_ci95"], acc["wilson_ci95"]) == (p, [lo, hi], [wlo, whi])
    expected = mcnemar(vector(run_dir, "v3"), vector(run_dir, "v2"))
    test = comp["mcnemar"]
    assert (test["a"], test["b"]) == ("v3", "v2")
    assert test["b_count"] == expected["a_only"] and test["c_count"] == expected["b_only"]
    assert test["p_exact"] == expected["p_exact"] and test["method"] == expected["method"]
    board = json.loads((run_dir / "scoreboard.json").read_text())
    assert board["e2e_accuracy"]["value"] == comp["versions"]["v3"]["accuracy"]["value"]
    assert board["e2e_accuracy"]["ci95"] == comp["versions"]["v3"]["accuracy"]["wald_ci95"]
    # abstention: answerable=false cases are i % 3 == 1 -> 4 cases.
    assert board["abstention_correct"]["n"] == 4
    assert board["cost_per_task_usd"] is None  # no price for fake-model -> null, never estimated


def test_plain_reading_does_not_overclaim(run_dir):
    comp = json.loads((run_dir / "comparison.json").read_text())
    assert comp["mcnemar"]["p_exact"] > 0.05
    assert "do not claim" in comp["reading"]
    md = (run_dir / "comparison.md").read_text()
    assert "Wilson" in md and "McNemar: v3 vs v2" in md and "| edge |" in md


def test_compare_reproduces_byte_identical(run_dir):
    names = ["comparison.json", "comparison.md", "scoreboard.json"]
    before = {n: (run_dir / n).read_bytes() for n in names}
    for n in names:
        (run_dir / n).unlink()
    assert compare_versions.main(["--run-dir", str(run_dir)]) == 0
    assert {n: (run_dir / n).read_bytes() for n in names} == before


def test_classifier_metrics(run_dir):
    cls = json.loads((run_dir / "scoreboard.json").read_text())["classifier"]
    # Fake classifier always says field_complaint with one matching issue: right on odd cases only.
    assert cls["intent"]["k"] == 6 and cls["intent"]["n"] == 12
    assert cls["issues_match"]["k"] == 6 and cls["urgency"]["n"] == 6 and cls["urgency"]["k"] == 6
    assert cls["json_valid"]["value"] == 1.0 and cls["mean_attempts"] == 1


def edit_jsonl(path, fn):
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    path.write_text("".join(json.dumps(fn(r)) + "\n" for r in rows))


def cases_file(run_dir):
    return run_dir.parent / "cases.jsonl"


def test_stale_judgements_block_compare_until_rerun(run_dir, capsys):
    target = "T-004"
    edit_jsonl(cases_file(run_dir), lambda c: {**c, "expected_behavior": "Changed by a human."}
               if c["id"] == target else c)
    with pytest.raises(compare_versions.StaleJudgementsError) as err:
        compare_versions.compare(run_dir)
    assert err.value.case_ids == [target]
    assert compare_versions.main(["--run-dir", str(run_dir)]) == 1
    message = capsys.readouterr().err
    assert target in message and "eval.run_e2e" in message
    assert compare_versions.main(["--run-dir", str(run_dir), "--allow-stale"]) == 0
    assert json.loads((run_dir / "comparison.json").read_text())["stale_judgements"] == [target]
    assert json.loads((run_dir / "scoreboard.json").read_text())["stale_judgements"] == [target]
    # Rerun: classifier/answers from cache, only the edited case is re-judged (once per version).
    provider = FakeProvider()
    run(run_dir.parent, provider, cases_file(run_dir))
    assert len(provider.calls) == 3
    comp, board = compare_versions.compare(run_dir)
    assert comp["stale_judgements"] == [] and board["stale_judgements"] == []


def test_answerable_flip_is_stale_and_rows_without_hash_fall_back_to_testset_hash(run_dir):
    edit_jsonl(cases_file(run_dir), lambda c: {**c, "answerable": not c["answerable"]} if c["id"] == "T-001" else c)
    assert compare_versions.stale_judgements(
        {v: [json.loads(l) for l in (run_dir / f"judged_{v}.jsonl").read_text().splitlines()]
         for v in ("v1",)},
        {"v1": [json.loads(l) for l in (run_dir / "answers_v1.jsonl").read_text().splitlines()]},
        {c["id"]: c for c in map(json.loads, cases_file(run_dir).read_text().splitlines())},
        testset_changed=True) == ["T-001"]
    for v in ("v1", "v2", "v3"):
        edit_jsonl(run_dir / f"judged_{v}.jsonl", lambda r: {k: x for k, x in r.items() if k != "judge_input_sha256"})
    with pytest.raises(compare_versions.StaleJudgementsError) as err:
        compare_versions.compare(run_dir)
    assert len(err.value.case_ids) == 12  # cannot verify old rows once the test set changed


def test_label_change_recomputes_classifier_and_records_labels_hash(run_dir):
    before = json.loads((run_dir / "scoreboard.json").read_text())["classifier"]
    edit_jsonl(cases_file(run_dir), lambda c: {**c, "expected": {**c["expected"], "intent": "field_complaint"}}
               if c["id"] == "T-000" else c)
    _, board = compare_versions.compare(run_dir)
    after = board["classifier"]
    assert after["intent"]["k"] == before["intent"]["k"] + 1
    assert len(after["labels_sha256"]) == 64 and after["labels_sha256"] != before["labels_sha256"]


def priced(run_dir, price_in=1.0, price_out=2.0, week1=0.5):
    meta = json.loads((run_dir / "run_meta.json").read_text())
    meta["provider"] = "paid"
    meta["cost_inputs"].update(price={"provider": "paid", "model": "fake-model", "price_in_per_1m_usd": price_in,
                                      "price_out_per_1m_usd": price_out, "free_tier": False},
                               week1_spend_usd=week1)
    (run_dir / "run_meta.json").write_text(json.dumps(meta))


def test_costs_use_run_meta_snapshot_then_fall_back_to_config(run_dir):
    priced(run_dir)
    _, board = compare_versions.compare(run_dir)
    # classifier 50/30 + answer 40/60 per case at 1 / 2 USD per 1M tokens.
    assert board["cost_per_task_usd"] == pytest.approx((90 * 1 + 90 * 2) / 1e6)
    assert board["spend_total_usd"] == pytest.approx(board["spend_week_usd"] + 0.5)
    assert board["list_price"]["cost_inputs_source"] == {"price": "run_meta.json", "week1_spend": "run_meta.json"}
    assert board["cost_incomplete"] is False
    meta = json.loads((run_dir / "run_meta.json").read_text())
    del meta["cost_inputs"]
    (run_dir / "run_meta.json").write_text(json.dumps(meta))
    _, board = compare_versions.compare(run_dir)
    assert board["list_price"]["cost_inputs_source"] == {"price": "config/prices.json",
                                                          "week1_spend": "eval/results/week1/cost_summary.json"}
    assert board["cost_per_task_usd"] is None  # no "paid" entry in config/prices.json


def test_unknown_token_count_makes_cost_null_not_zero(run_dir):
    priced(run_dir)
    edit_jsonl(run_dir / "answers_v3.jsonl", lambda r: {**r, "output_tokens": None} if r["case_id"] == "T-002" else r)
    edit_jsonl(run_dir / "judged_v3.jsonl", lambda r: {**r, "input_tokens": None} if r["case_id"] == "T-003" else r)
    comp, board = compare_versions.compare(run_dir)
    assert board["cost_incomplete"] is True and board["list_price"]["rows_with_unknown_tokens"] == 2
    assert board["cost_per_task_usd"] is None and board["spend_week_usd"] is None
    assert board["spend_total_usd"] is None
    assert board["list_price"]["week_tokens"]["input"] is None
    assert board["list_price"]["week_tokens"]["output"] is None
    assert board["list_price"]["eval_judge_cost_per_task_list_usd"] is None


def test_contact_fabrication_rule():
    from eval.compare_versions import contact_fabrication
    for text in ["444 00 00 numaralı çağrı merkezi", "444 0 000", "+90 532 123 45 67",
                 "0212 555 12 34", "www.yesilvadi.bel.tr", "info@example.org"]:
        assert contact_fabrication(text), text
    for text in ["YV-2026-011532", "son 4 hane 2274", "09:00-17:00", "2026 yılında 3 gün", ""]:
        assert not contact_fabrication(text), text
