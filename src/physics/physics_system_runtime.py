"""Evidence-backed reconstruction of the SHIFT PhysX/PhysicsSystem runtime boundary.

The implementation follows recovered retail routines in SHIFT.exe.c:
FUN_0070fae0, FUN_0070f580, FUN_007506b0, FUN_00750620, FUN_0074d290,
FUN_0074d310 and FUN_0074d400.

This module deliberately models the observable contract and control flow instead
of inventing names for opaque PhysX scene-descriptor fields.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any

FORMAT = "SHIFT.PhysicsSystemRuntime/1"
MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"
TWEAKER_FORMAT = "SHIFT.PhysicsTweakerRuntime/1"

PHYSX_SDK_VERSION = 0x02080100
PHYSX_COOKING_VERSION = 0x02080100
CSM_VERSION = 0x0AFB

SOURCE_FILE = ".\\Source\\System\\PhysicsSystem.cpp"
PARTICIPANT_SOURCE_FILE = ".\\Source\\System\\PhysicsParticipant.cpp"
MANAGER_SOURCE_FILE = (
    "c:\\dev\\p4v\\gecko\\branches\\20090901_pc_patch\\src\\physics\\include\\"
    "../Source/Manager/cPhysicsManager.hpp"
)

PHYSX_CREATE_PARAMETER_WORDS = {
    1: 0x3C23D70A,
    8: 0x3F800000,
}

# FUN_007506b0 creates this local sequence before NxCreatePhysicsSDK.
# Exact field meanings are not established by the decompilation, so offsets are
# intentionally not named as semantic PhysX properties.
SDK_CREATE_LOCAL_WORDS = {
    "word_0": 0,
    "word_1": 0,
    "word_3": 0x00010000,
    "word_4": 0x00000100,
    "word_5": 0x00000800,
}

SCENE_DESCRIPTOR_OBSERVED_WORDS = {
    0x2C: 0x3C888889,
    0x30: 0x00000000,
    0x4C: 0x00000005,
    0x50: 0x00000004,
    0x54: 0x00000064,
    0x58: 0x00000000,
    0x60: 0x00000002,
    0x68: 0x00000000,
    0x70: 0x00000000,
    0x74: 0x00000002,
    0x78: 0x00000002,
}

FILTER_RELATION_SEEDS = ((1, 2, 0), (3, 3, 0), (3, 2, 0))

MANAGER_VTABLE = "PTR_FUN_00b04524"
MANAGER_PATH_FIELDS = {
    0x370: "Tracks/_Data/",
    0x374: "Tracks/",
    0x378: "vehicles/",
    0x37C: "Physics/",
    0x380: "<DAT_00b04554>",
    0x384: "<field_0x380>/Drivers/",
}

RESOURCE_SUFFIXES = {
    "dynamic_root": "dynamic/",
    "dynamic_name": "Dynamic",
    "dynamic_fx": "dynamic/fx/fx",
    "triggers": "triggers.xml",
    "aiw": "AIW/{mission}.aiw",
    "sections": "Sections/{mission}.tsl",
}

@dataclass(frozen=True)
class VtableCall:
    offset: int
    args: tuple[int, ...]
    target: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "vtable_offset": self.offset,
            "vtable_offset_hex": f"0x{self.offset:x}",
            "args": list(self.args),
            "target": self.target,
        }


def _word_float(word: int) -> float:
    return struct.unpack("<f", struct.pack("<I", word & 0xFFFFFFFF))[0]


def _hex(word: int) -> str:
    return f"0x{word & 0xFFFFFFFF:08x}"


def build_manager_layout() -> dict[str, Any]:
    """Return the constructor-visible Physics Manager layout evidence."""
    zeroed_flags = [0x280 + i * 4 for i in range(0xA2, 0xAF)]
    return {
        "format": MANAGER_FORMAT,
        "version": 1,
        "source": MANAGER_SOURCE_FILE,
        "functions": ["FUN_0070fae0", "FUN_0070f580"],
        "vtable": MANAGER_VTABLE,
        "base_constructor": "FUN_00647a10",
        "named_object": "Physics Manager",
        "array_fields": [
            {"offset": off, "offset_hex": f"0x{off:x}", "initializer": "FUN_00533e70"}
            for off in range(0x370, 0x388, 4)
        ],
        "path_fields": [
            {"offset": off, "offset_hex": f"0x{off:x}", "value": value}
            for off, value in MANAGER_PATH_FIELDS.items()
        ],
        "constructor_zeroed_offsets": zeroed_flags,
        "special_defaults": {
            "0x2b1": 1,
            "0x450": 2,
            "0x490": 2,
            "0x494": 2,
            "0x480": 4,
            "0x484": 4,
            "0x488": 4,
            "0x48c": 5,
            "0x460": 3,
            "0x464": 3,
        },
        "shutdown": {
            "destroy_auxiliary": "FUN_007511b0 when field 0xaa is set",
            "allocator_release_vtable_offset": 0x1C,
            "array_destruct_order": [
                "0x384", "0x380", "0x37c", "0x378", "0x374", "0x370"
            ],
            "base_destructor": "FUN_00647b20",
        },
        "status": "evidence-backed-layout",
    }


def build_physics_paths(mission: str) -> dict[str, str]:
    """Build resource paths that are constructed verbatim by FUN_007506b0."""
    if not mission:
        raise ValueError("mission must be non-empty")
    return {
        "mission_collision_stem": f"campaign/missions/{mission}/physics/{mission}",
        "mission_collision_csm": f"campaign/missions/{mission}/physics/{mission}.csm",
        "aiw": f"AIW/{mission}.aiw",
        "sections": f"Sections/{mission}.tsl",
        "triggers": "triggers.xml",
        "dynamic": "dynamic/",
        "dynamic_named": "dynamic/Dynamic",
        "dynamic_fx": "dynamic/fx/fx",
    }


def build_filter_relations() -> list[dict[str, int | str]]:
    relations: list[dict[str, int | str]] = [
        {"group_a": a, "group_b": b, "flags": flags}
        for a, b, flags in FILTER_RELATION_SEEDS
    ]
    relations.extend(
        {"group_a": 0x1E, "group_b": i, "flags": 0}
        for i in range(0x1F)
    )
    relations.extend(
        {"group_a": 0x1D, "group_b": i, "flags": 0}
        for i in range(0x1F)
        if i != 4
    )
    return relations


def build_scene_descriptor_defaults() -> dict[str, Any]:
    """Expose FUN_0074e460 defaults while keeping unknown words opaque."""
    return {
        "format": "SHIFT.PhysicsSceneDescriptorTemplate/1",
        "version": 1,
        "initializer": "FUN_0074e460",
        "observed_words": {
            f"offset_0x{off:02x}": {
                "u32": value,
                "hex": _hex(value),
                "f32_candidate": _word_float(value),
            }
            for off, value in SCENE_DESCRIPTOR_OBSERVED_WORDS.items()
        },
        "semantic_status": "field-names-unresolved",
    }


def build_physics_system_contract(mission: str | None = None) -> dict[str, Any]:
    """Return the reconstructed startup contract around FUN_007506b0."""
    paths = build_physics_paths(mission) if mission else None
    provider_registry = build_physics_provider_registry()
    provider_dispatch = build_physics_provider_dispatch_contract()
    return {
        "format": FORMAT,
        "version": 1,
        "status": "evidence-backed-contract",
        "source": SOURCE_FILE,
        "functions": [
            "FUN_007506b0",
            "FUN_00750620",
            "FUN_00710870",
            "FUN_00750080",
        ],
        "provider_registry": provider_registry,
        "provider_dispatch": provider_dispatch,
        "physx": {
            "sdk_version": PHYSX_SDK_VERSION,
            "sdk_version_hex": _hex(PHYSX_SDK_VERSION),
            "cooking_library_version": PHYSX_COOKING_VERSION,
            "create_allocations": [
                {"name": "allocator", "bytes": 0xC0, "constructor": "FUN_0079d060"},
                {"name": "error_stream", "bytes": 4, "vtable": "PTR_LAB_00b08834"},
                {"name": "contact_modifier", "bytes": 4, "vtable": "PTR_LAB_00b08844"},
                {"name": "contact_report", "bytes": 4, "vtable": "PTR_FUN_00b0884c"},
                {"name": "trigger_report", "bytes": 4, "vtable": "PTR_FUN_00b08854"},
            ],
            "create_api": {
                "NxCreatePhysicsSDK": {
                    "version": PHYSX_SDK_VERSION,
                    "parameter_block": {
                        "word_0": SDK_CREATE_LOCAL_WORDS["word_0"],
                        "word_1": SDK_CREATE_LOCAL_WORDS["word_1"],
                        "word_3": SDK_CREATE_LOCAL_WORDS["word_3"],
                        "word_4": SDK_CREATE_LOCAL_WORDS["word_5"],
                        "word_5": SDK_CREATE_LOCAL_WORDS["word_4"],
                    },
                    "sdk_parameter_writes": [
                        {
                            "parameter": param,
                            "value_u32": value,
                            "value_hex": _hex(value),
                            "value_f32": _word_float(value),
                        }
                        for param, value in PHYSX_CREATE_PARAMETER_WORDS.items()
                    ],
                },
                "NxGetCookingLib": {"version": PHYSX_COOKING_VERSION, "init_call": [0, 0]},
            },
        },
        "scene": {
            "descriptor": build_scene_descriptor_defaults(),
            "create_vtable_offset": 0x10,
            "post_create_calls": [
                VtableCall(0x148, (0x3D088889, 8, 0), "scene runtime parameter call").to_dict(),
                VtableCall(0xCC, (0, 0, 0x8E), "scene runtime parameter call").to_dict(),
                VtableCall(0x18C, (0,), "set contact modifier").to_dict(),
                VtableCall(0x19C, (0,), "set contact report").to_dict(),
                VtableCall(0x194, (0,), "set trigger report").to_dict(),
            ],
            "filter_relations": build_filter_relations(),
            "scene_field_0x25c_capture": "FUN_0079cfd0 input is returned from scene vtable +0x25c",
        },
        "assets": {
            "collision_stream": {
                "extension": ".csm",
                "version": CSM_VERSION,
                "version_hex": _hex(CSM_VERSION),
                "loader": "FUN_00750080",
                "required_first_stream": True,
                "optional_second_stream": True,
                "required_error": "Failed to load %s collision stream",
                "version_error": "CSM version is incorrect (%d), should be %d, is your data up to date? please talk to SteveD and he will help you",
            },
            "dynamic": RESOURCE_SUFFIXES,
            "paths": paths,
        },
        "callbacks_and_helpers": [
            "FUN_0077ded0(0xc1af08)",
            "FUN_007768b0(&DAT_00c1a5e0)",
            "FUN_00781a10(FUN_00782a10(), scene)",
            "FUN_00780c60(FUN_00782a10())",
            "FUN_00720190(&DAT_00c10f68)",
            "FUN_0079f990(FUN_0079f930())",
            "FUN_00752c30(&DAT_00c134b8, triggers)",
            "FUN_00752d20(0xc134b8)",
            "FUN_00750620()",
        ],
        "startup_order": [
            "construct Physics Manager",
            "derive resource paths",
            "allocate PhysX allocator/error/callback objects",
            "NxCreatePhysicsSDK",
            "set SDK parameters",
            "NxGetCookingLib + initialize",
            "initialize scene descriptor + create scene",
            "install collision filters",
            "register runtime helpers/callbacks",
            "load primary .csm and optional secondary .csm",
            "load dynamic .obj.xml resources",
            "load triggers.xml / related runtime assets",
            "initialize global physics state",
            "FUN_00750620 auxiliary scene object",
        ],
        "explicit_unknowns": [
            "semantic names of FUN_0074e460 scene descriptor fields",
            "meaning of SDK parameter ids 1 and 8 beyond observed writes",
            "meaning of collision-stream record fields inside FUN_0074e880",
            "runtime meaning of the opaque dynamic/AIW/TSL resource consumers",
        ],
    }


def build_physics_tweaker_contract() -> dict[str, Any]:
    """Return the loader boundary recovered from FUN_0074d290/FUN_0074d310."""
    return {
        "format": TWEAKER_FORMAT,
        "version": 1,
        "source": ".\\Source\\System\\Extras.cpp",
        "functions": ["FUN_0074d290", "FUN_0074d310", "FUN_0074d400"],
        "path": "PhysicsTweaker.xml",
        "registry": {
            "lazy_init_flag": "DAT_00c13380 bit 0",
            "object": "DAT_00c13280",
            "registration": "DAT_00c13260 = FUN_0074c840(&DAT_00c13280)",
        },
        "load": {
            "database_getter": "FUN_00710870",
            "load_call": "FUN_00640150(local_680, FUN_00710870(), 1)",
            "failure_behavior": "logs and emits source-backed diagnostic; execution then invokes target object's virtual load hook",
            "virtual_load_offset": 0x20,
            "virtual_finish_offset": 0x24,
        },
        "status": "loader-boundary-reconstructed",
    }



def build_physics_provider_dispatch_contract() -> dict[str, Any]:
    """Describe the exact provider probe/replace chain in FUN_007b3820."""
    return {
        "format": "SHIFT.PhysicsProviderDispatch/1",
        "version": 1,
        "source": {
            "constructor": "FUN_007b3820",
            "selector": "FUN_007d2e70",
            "accept_probe_vtable_offset": "+0x14",
        },
        "candidate_order": [
            {
                "selector_index": 0,
                "slot": "DAT_00c23da8",
                "acceptance_argument": "physics_system+0x3c",
            },
            {
                "selector_index": 1,
                "slot": "DAT_00c23dac",
                "acceptance_argument": "physics_system+0x3c",
            },
        ],
        "termination": {
            "after_index_1": "selector index 2 returns null",
            "null_provider": "enter generic FUN_007b2010/FUN_007b1360 fallback",
            "rejected_provider": "probe next selector index",
        },
        "accepted_provider_rewrite": {
            "release_old_matrix": {
                "function": "FUN_0064f4b0",
                "source_slot": "physics_system+0x38",
            },
            "free_old_row_table": {
                "function": "FUN_00886930",
                "source_slot": "physics_system+0x3c",
            },
            "replace_row_table": {
                "vtable_offset": "+0x0c",
                "destination": "physics_system+0x3c",
            },
            "replace_graph_storage": {
                "vtable_offset": "+0x04",
                "destination": "physics_system+0x40",
            },
            "replace_aux_storage": {
                "vtable_offset": "+0x08",
                "destination": "physics_system+0x44",
            },
            "finalize": {
                "vtable_offset": "+0x2c",
                "destination": "physics_system+0x48",
            },
        },
        "generic_fallback": {
            "matrix_rebuild": "FUN_007b2010",
            "compact_graph_allocation": {
                "bytes": "node_count * 8",
                "destination": "physics_system+0x40",
            },
            "compact_graph_builder": "FUN_007b1360",
            "per_body_allocation": {
                "index_matrix_bytes": "node_count * node_count * 8",
                "row_storage_bytes": "node_count * 8",
                "index_vector_bytes": "node_count * 4",
                "derived_index_rule": "(row_pointer[i] - matrix_base) >> 3",
            },
        },
        "common_post_provider": {
            "body_output_node_count": "physics_system+0x34",
            "per_body_runtime_base": "physics_system+0x14 + 0x170 + body_index * 0x170",
            "per_body_offsets": {
                "+0xa4": "node_count",
                "+0xa8": "node_count * node_count",
                "+0xac": "node_count",
                "+0x150": "node_count * 8 allocation",
                "+0x154": "node_count * node_count * 8 allocation",
                "+0x158": "node_count * 4 allocation",
                "+0x15c": "node-derived index vector",
            },
        },
        "limitations": [
            "Provider acceptance is a runtime virtual call; this contract does not synthesize a return value.",
            "Concrete provider classes and the semantic type of returned storage remain unresolved.",
        ],
    }


def build_physics_provider_registry() -> dict[str, Any]:
    """Describe the two source-visible physics provider slots returned by FUN_007d2e70."""
    return {
        "format": "SHIFT.PhysicsProviderRegistry/1",
        "version": 1,
        "selector": {
            "function": "FUN_007d2e70",
            "index_zero": "DAT_00c23da8",
            "index_one": "DAT_00c23dac",
            "other_indices": "null",
        },
        "lifecycle": {
            "provider_zero_init": "FUN_007d2f70",
            "provider_zero_shutdown": "FUN_007c6e10",
            "provider_one_init": "FUN_007cd980",
            "provider_one_shutdown": "FUN_007cdb00",
        },
        "consumer_vtable": {
            "presence_probe": "+0x14",
            "reset_allocation_state": "+0x0c",
            "replace_primary_storage": "+0x04",
            "replace_aux_storage": "+0x08",
            "finalize": "+0x2c",
        },
        "selection_semantics": {
            "default_consumer": "FUN_007b3820 probes provider slots from index 0 upward until one accepts the runtime allocation base",
            "unsupported_selector": "returns null",
        },
        "limitations": [
            "Neither slot is assigned a PhysX class name without direct type evidence.",
            "Vtable methods are recorded by offset only; argument semantics remain separate targets.",
        ],
    }

