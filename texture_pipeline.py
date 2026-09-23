"""DDS and D3D9 sampler state contract for the platform-neutral renderer."""
from __future__ import annotations

from typing import Any


FORMAT = "SHIFT.TextureResource/1"

DDS_FORMATS = {
    "DXT1": {
        "block_compressed": True,
        "block_bytes": 8,
        "gpu_format": "BC1_RGBA",
        "upload": "native-compressed",
        "required_extension": "EXT_texture_compression_s3tc",
    },
    "DXT3": {
        "block_compressed": True,
        "block_bytes": 16,
        "gpu_format": "BC2_RGBA",
        "upload": "native-compressed",
        "required_extension": "EXT_texture_compression_s3tc",
    },
    "DXT5": {
        "block_compressed": True,
        "block_bytes": 16,
        "gpu_format": "BC3_RGBA",
        "upload": "native-compressed",
        "required_extension": "EXT_texture_compression_s3tc",
    },
    "ATI1": {
        "block_compressed": True,
        "block_bytes": 8,
        "gpu_format": "BC4_R",
        "upload": "native-compressed",
        "required_extension": "EXT_texture_compression_rgtc",
    },
    "BC4U": {
        "block_compressed": True,
        "block_bytes": 8,
        "gpu_format": "BC4_R",
        "upload": "native-compressed",
        "required_extension": "EXT_texture_compression_rgtc",
    },
    "ATI2": {
        "block_compressed": True,
        "block_bytes": 16,
        "gpu_format": "BC5_RG",
        "upload": "native-compressed",
        "required_extension": "EXT_texture_compression_rgtc",
    },
    "BC5U": {
        "block_compressed": True,
        "block_bytes": 16,
        "gpu_format": "BC5_RG",
        "upload": "native-compressed",
        "required_extension": "EXT_texture_compression_rgtc",
    },
    "": {
        "block_compressed": False,
        "gpu_format": "RGBA8_OR_RGB8",
        "upload": "uncompressed",
        "required_extension": None,
    },
}


def _norm_state(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def _map_filter(value: Any) -> str | None:
    state = _norm_state(value)
    if state in {None, "", "NONE"}:
        return None
    if state in {"POINT", "NEAREST"}:
        return "NEAREST"
    if state in {"LINEAR"}:
        return "LINEAR"
    if state in {"ANISOTROPIC"}:
        return "ANISOTROPIC"
    return None


def _map_mip_filter(value: Any) -> str | None:
    state = _norm_state(value)
    if state in {None, "", "NONE"}:
        return "NONE"
    if state in {"POINT", "NEAREST"}:
        return "POINT"
    if state == "LINEAR":
        return "LINEAR"
    return None


def _map_address(value: Any) -> str | None:
    state = _norm_state(value)
    return {
        None: None,
        "": None,
        "WRAP": "REPEAT",
        "REPEAT": "REPEAT",
        "CLAMP": "CLAMP_TO_EDGE",
        "CLAMP_TO_EDGE": "CLAMP_TO_EDGE",
        "MIRROR": "MIRRORED_REPEAT",
        "MIRRORED_REPEAT": "MIRRORED_REPEAT",
    }.get(state)


def _min_filter(min_filter: str | None, mip_filter: str | None) -> str | None:
    if min_filter == "NEAREST":
        return {
            "NONE": "NEAREST",
            "POINT": "NEAREST_MIPMAP_NEAREST",
            "LINEAR": "NEAREST_MIPMAP_LINEAR",
        }.get(mip_filter)
    if min_filter == "LINEAR":
        return {
            "NONE": "LINEAR",
            "POINT": "LINEAR_MIPMAP_NEAREST",
            "LINEAR": "LINEAR_MIPMAP_LINEAR",
        }.get(mip_filter)
    return None


def _color_space(binding: dict[str, Any]) -> tuple[str, bool]:
    srgb = bool(binding.get("srgb"))
    linear = bool(binding.get("linear"))
    if srgb and linear:
        return "conflict", False
    if srgb:
        return "sRGB", True
    if linear:
        return "linear", True
    return "unspecified", True


def classify_dds(metadata: dict[str, Any]) -> dict[str, Any]:
    fourcc = str(metadata.get("fourcc") or "")
    info = DDS_FORMATS.get(fourcc)
    if info is None:
        return {
            "status": "unknown-format",
            "fourcc": fourcc,
            "upload": "unsupported",
        }
    mipmaps = int(metadata.get("mipmaps") or 1)
    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    result = {
        "status": "known",
        "fourcc": fourcc,
        "width": width,
        "height": height,
        "mipmaps": mipmaps,
        **info,
    }
    if width <= 0 or height <= 0:
        result["status"] = "invalid-dimensions"
    if info["block_compressed"]:
        result["blocks_x"] = max(1, (width + 3) // 4)
        result["blocks_y"] = max(1, (height + 3) // 4)
    return result


def build_sampler_contract(binding: dict[str, Any]) -> dict[str, Any]:
    min_filter = _map_filter(binding.get("min_filter"))
    mag_filter = _map_filter(binding.get("mag_filter"))
    mip_filter = _map_mip_filter(binding.get("mip_filter"))
    address_u = _map_address(binding.get("address_u"))
    address_v = _map_address(binding.get("address_v"))
    address_w = _map_address(binding.get("address_w"))

    reasons: list[str] = []
    if binding.get("min_filter") is not None and min_filter is None:
        reasons.append(f"sampler-min-filter:unsupported:{binding.get('min_filter')}")
    if binding.get("mag_filter") is not None and mag_filter is None:
        reasons.append(f"sampler-mag-filter:unsupported:{binding.get('mag_filter')}")
    if binding.get("mip_filter") is not None and mip_filter is None:
        reasons.append(f"sampler-mip-filter:unsupported:{binding.get('mip_filter')}")
    for axis, raw, mapped in (
        ("u", binding.get("address_u"), address_u),
        ("v", binding.get("address_v"), address_v),
        ("w", binding.get("address_w"), address_w),
    ):
        if raw is not None and mapped is None:
            reasons.append(f"sampler-address-{axis}:unsupported:{raw}")
    effective_min = _min_filter(min_filter, mip_filter)
    if min_filter is not None and effective_min is None:
        reasons.append("sampler-min-filter:invalid-mip-combination")
    if mag_filter == "ANISOTROPIC":
        reasons.append("sampler-mag-filter:anisotropic-not-valid-for-mag")
    return {
        "format": "SHIFT.SamplerState/1",
        "source": "D3D9-FX",
        "min_filter": min_filter,
        "mag_filter": mag_filter,
        "mip_filter": mip_filter,
        "min_filter_gl": effective_min,
        "mag_filter_gl": None if mag_filter == "ANISOTROPIC" else mag_filter,
        "address_u": address_u,
        "address_v": address_v,
        "address_w": address_w,
        "max_anisotropy": int(binding.get("max_anisotropy") or 1),
        "lod_bias": int(binding.get("lod_bias") or 0),
        "ready": not reasons,
        "blocking_reasons": reasons,
    }


def build_texture_contract(metadata: dict[str, Any], binding: dict[str, Any] | None = None) -> dict[str, Any]:
    binding = dict(binding or {})
    dds = classify_dds(metadata)
    sampler = build_sampler_contract(binding)
    color_space, color_ready = _color_space(binding)
    reasons: list[str] = []
    if dds.get("status") != "known":
        reasons.append(f"dds:{dds.get('status')}")
    if not sampler["ready"]:
        reasons.extend(sampler["blocking_reasons"])
    if not color_ready:
        reasons.append("color-space:srgb-and-linear-both-set")
    if dds.get("required_extension"):
        reasons.append(f"gpu-extension-required:{dds['required_extension']}")
    return {
        "format": FORMAT,
        "source": "DDS",
        "dds": dds,
        "sampler": sampler,
        "color_space": color_space,
        "ready": not reasons,
        "blocking_reasons": reasons,
    }
