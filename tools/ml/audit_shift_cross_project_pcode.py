#!/usr/bin/env python3
"""Audit portable SHIFT high-P-code and optional foreign-model transfer output.

This is a representation/OOD probe, not semantic ground truth. The script checks
that model_text is architecture-normalized and free of obvious join-key leakage,
then summarizes prediction/routing/OOD behavior when a classified JSONL is given.
When the monotone foreign-project guard has been applied, both pre-guard and
post-guard actions are reported explicitly.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.CrossProjectPcodeAudit/2"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(row)
    return rows


def header_value(text: str, name: str) -> str | None:
    prefix = name + "="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    return None


def quantiles(values: Iterable[float]) -> dict[str, float | None]:
    data = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not data:
        return {"min": None, "median": None, "p90": None, "max": None}

    def pick(q: float) -> float:
        index = min(len(data) - 1, max(0, round((len(data) - 1) * q)))
        return data[index]

    return {
        "min": data[0],
        "median": statistics.median(data),
        "p90": pick(0.90),
        "max": data[-1],
    }


def corpus_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    formats = collections.Counter()
    statuses = collections.Counter()
    arch = collections.Counter()
    endian = collections.Counter()
    ptr = collections.Counter()
    callconv = collections.Counter()
    leakage = []
    emitted = []
    truncated = 0

    for index, row in enumerate(rows, 1):
        formats[str(row.get("format"))] += 1
        status = str(row.get("decompile_status"))
        statuses[status] += 1
        if status != "ok":
            continue
        text = row.get("model_text")
        if not isinstance(text, str) or not text:
            leakage.append({"row": index, "reason": "missing_model_text"})
            continue
        arch[str(header_value(text, "ARCH"))] += 1
        endian[str(header_value(text, "ENDIAN"))] += 1
        ptr[str(header_value(text, "PTR_SIZE"))] += 1
        callconv[str(header_value(text, "CALLCONV"))] += 1
        source_entry = row.get("source_entry")
        source_name = row.get("source_name")
        program = row.get("program")
        for label, value in (
            ("source_entry", source_entry),
            ("source_name", source_name),
            ("program", program),
        ):
            if isinstance(value, str) and value and value in text:
                leakage.append({"row": index, "reason": f"{label}_leaked"})
        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        emitted_ops = metrics.get("emitted_ops")
        if isinstance(emitted_ops, int):
            emitted.append(emitted_ops)
            if emitted_ops > 256:
                leakage.append({"row": index, "reason": "emitted_ops_gt_256"})
        if bool(metrics.get("truncated")):
            truncated += 1

    ok = statuses.get("ok", 0)
    return {
        "rows": len(rows),
        "formats": dict(sorted(formats.items())),
        "statuses": dict(sorted(statuses.items())),
        "architecture": dict(sorted(arch.items())),
        "endian": dict(sorted(endian.items())),
        "pointer_size": dict(sorted(ptr.items())),
        "calling_convention": dict(sorted(callconv.items())),
        "truncated": truncated,
        "truncated_fraction": truncated / ok if ok else 0.0,
        "emitted_ops": quantiles(emitted),
        "leakage_findings": leakage,
        "portable_contract_pass": bool(ok) and not leakage,
    }


def transfer_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    predictions = collections.Counter(str(row.get("prediction")) for row in rows)
    actions = collections.Counter(str(row.get("action")) for row in rows)
    base_actions = collections.Counter(
        str(row.get("base_action", row.get("action"))) for row in rows
    )
    confidence = [
        float(row["confidence"])
        for row in rows
        if isinstance(row.get("confidence"), (int, float))
    ]
    raw_confidence = [
        float(row["raw_confidence"])
        for row in rows
        if isinstance(row.get("raw_confidence"), (int, float))
    ]
    similarity = [
        float(row["family_similarity"])
        for row in rows
        if isinstance(row.get("family_similarity"), (int, float))
    ]
    contrast = [
        float(row["contrast_margin"])
        for row in rows
        if isinstance(row.get("contrast_margin"), (int, float))
    ]
    accept = actions.get("accept", 0)
    base_accept = base_actions.get("accept", 0)
    changed = sum(bool(row.get("foreign_guard_changed")) for row in rows)
    guard_present = any("foreign_guard_format" in row for row in rows)
    reason_counts = collections.Counter(
        reason
        for row in rows
        for reason in row.get("foreign_guard_reasons", [])
        if isinstance(reason, str)
    )
    promotions = sum(
        1
        for row in rows
        if str(row.get("base_action", row.get("action"))) != "accept"
        and str(row.get("action")) == "accept"
    )
    report = {
        "rows": len(rows),
        "predictions": dict(sorted(predictions.items())),
        "base_actions": dict(sorted(base_actions.items())),
        "actions": dict(sorted(actions.items())),
        "base_accept_fraction": base_accept / len(rows) if rows else 0.0,
        "accept_fraction": accept / len(rows) if rows else 0.0,
        "confidence": quantiles(confidence),
        "raw_confidence": quantiles(raw_confidence),
        "family_similarity": quantiles(similarity),
        "contrast_margin": quantiles(contrast),
        "semantic_labels_available": False,
        "interpretation": "OOD/representation probe only; accept is not correctness on SHIFT.",
        "foreign_guard": None,
    }
    if guard_present:
        report["foreign_guard"] = {
            "format": next(
                (str(row.get("foreign_guard_format")) for row in rows if row.get("foreign_guard_format")),
                None,
            ),
            "changed_accepts": changed,
            "changed_fraction": changed / len(rows) if rows else 0.0,
            "accept_retention": accept / base_accept if base_accept else 0.0,
            "promotions": promotions,
            "reasons": dict(sorted(reason_counts.items())),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--classified", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    corpus = read_jsonl(args.corpus)
    if not corpus:
        raise SystemExit("corpus is empty")
    report: dict[str, Any] = {
        "format": FORMAT,
        "corpus": corpus_audit(corpus),
        "transfer": None,
    }
    if args.classified is not None:
        classified = read_jsonl(args.classified)
        report["transfer"] = transfer_audit(classified)
        if len(classified) != report["corpus"]["statuses"].get("ok", 0):
            report["transfer"]["row_count_warning"] = (
                "classified rows differ from successful corpus rows"
            )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    corpus_report = report["corpus"]
    print("format:", FORMAT)
    print("rows:", corpus_report["rows"])
    print("statuses:", corpus_report["statuses"])
    print("architecture:", corpus_report["architecture"])
    print("pointer size:", corpus_report["pointer_size"])
    print("portable contract pass:", corpus_report["portable_contract_pass"])
    print("leakage findings:", len(corpus_report["leakage_findings"]))
    if report["transfer"] is not None:
        transfer = report["transfer"]
        print("predictions:", transfer["predictions"])
        print("base actions:", transfer["base_actions"])
        print("actions:", transfer["actions"])
        print("base accept fraction:", round(transfer["base_accept_fraction"], 6))
        print("accept fraction:", round(transfer["accept_fraction"], 6))
        print("family similarity:", transfer["family_similarity"])
        print("contrast margin:", transfer["contrast_margin"])
        if transfer["foreign_guard"] is not None:
            print("foreign guard:", transfer["foreign_guard"])
        print("semantic labels available:", transfer["semantic_labels_available"])
    if args.output is not None:
        print("output:", args.output)
    return 0 if corpus_report["portable_contract_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
