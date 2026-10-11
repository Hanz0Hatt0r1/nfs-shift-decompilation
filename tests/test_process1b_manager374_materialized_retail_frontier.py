import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_p1b_manager374_materialized_retail_frontier.py"
SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def module():
    spec = importlib.util.spec_from_file_location("p1b_materialized_frontier", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def probe(fmt, count_key, rows_key, rows):
    return {
        "format": fmt,
        "version": 1,
        "ready": True,
        "authority": {"retail_executable_sha256": SHA},
        "surface": {count_key: len(rows), rows_key: rows},
    }


def sample_results():
    mod = module()
    return {
        "same_region": probe(
            mod.PROBES["same_region"]["format"],
            mod.PROBES["same_region"]["candidate_count_key"],
            mod.PROBES["same_region"]["candidate_rows_key"],
            [
                {
                    "site": "0x00401010",
                    "receiver_register": "ecx",
                    "materializer_site": "0x00401000",
                    "address_register": "eax",
                    "mnemonic": "mov",
                }
            ],
        ),
        "ebp_spill_reload": probe(
            mod.PROBES["ebp_spill_reload"]["format"],
            mod.PROBES["ebp_spill_reload"]["candidate_count_key"],
            mod.PROBES["ebp_spill_reload"]["candidate_rows_key"],
            [
                {
                    "site": "0x00402020",
                    "receiver_register": "esi",
                    "materializer_site": "0x00402000",
                    "address_register": "edx",
                    "mnemonic": "mov",
                }
            ],
        ),
        "esp_spill_reload": probe(
            mod.PROBES["esp_spill_reload"]["format"],
            mod.PROBES["esp_spill_reload"]["candidate_count_key"],
            mod.PROBES["esp_spill_reload"]["candidate_rows_key"],
            [
                {
                    "site": "0x00402020",
                    "receiver_register": "esi",
                    "materializer_site": "0x00402000",
                    "address_register": "ebx",
                    "mnemonic": "xchg",
                },
                {
                    "site": "0x00403030",
                    "receiver_register": "edi",
                    "materializer_site": "0x00403000",
                    "address_register": "eax",
                    "mnemonic": "add",
                },
            ],
        ),
    }


def test_compose_preserves_all_probe_records_and_deduplicates_sites():
    data = module().compose(sample_results())
    surface = data["surface"]
    assert surface["candidate_record_count_by_probe"] == {
        "same_region": 1,
        "ebp_spill_reload": 1,
        "esp_spill_reload": 2,
    }
    assert surface["candidate_record_count"] == 4
    assert surface["unique_candidate_site_count"] == 3
    assert surface["unique_candidate_sites"] == ["0x00401010", "0x00402020", "0x00403030"]
    shared = next(row for row in surface["candidate_site_sources"] if row["site"] == "0x00402020")
    assert shared["source_probes"] == ["ebp_spill_reload", "esp_spill_reload"]
    transports = {row["transport_class"] for row in surface["candidate_records"]}
    assert transports == {"same-region-gpr", "ebp-spill-reload", "esp-normalized-spill-reload"}


def test_empty_real_frontier_is_still_semantically_fail_closed():
    mod = module()
    results = {}
    for name, cfg in mod.PROBES.items():
        results[name] = probe(cfg["format"], cfg["candidate_count_key"], cfg["candidate_rows_key"], [])
    data = mod.compose(results)
    assert data["surface"]["unique_candidate_site_count"] == 0
    adj = data["adjudication"]
    assert adj["retail_materialized_probe_bundle_execution_complete"] is True
    assert adj["retail_materialized_candidate_frontier_composed"] is True
    assert adj["all_materialized_candidate_receivers_classified"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_wrong_probe_format_fails_closed():
    results = sample_results()
    results["same_region"]["format"] = "SHIFT.Wrong/1"
    with pytest.raises(ValueError, match="format drift"):
        module().compose(results)


def test_wrong_retail_sha_fails_closed():
    results = sample_results()
    results["ebp_spill_reload"]["authority"]["retail_executable_sha256"] = "00" * 32
    with pytest.raises(ValueError, match="retail hash drift"):
        module().compose(results)


def test_candidate_count_mismatch_fails_closed():
    results = sample_results()
    results["esp_spill_reload"]["surface"]["reload_derived_zero_displacement_write_candidate_count"] = 3
    with pytest.raises(ValueError, match="candidate count mismatch"):
        module().compose(results)


def test_missing_receiver_provenance_fails_closed():
    results = sample_results()
    del results["same_region"]["surface"]["zero_displacement_write_candidates"][0]["receiver_register"]
    with pytest.raises(ValueError, match="receiver provenance missing"):
        module().compose(results)


def test_probe_bundle_key_drift_fails_closed():
    results = sample_results()
    del results["esp_spill_reload"]
    with pytest.raises(ValueError, match="probe bundle key drift"):
        module().compose(results)
