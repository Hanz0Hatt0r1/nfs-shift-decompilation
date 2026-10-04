"""Exact retail archive identities for the first playable Linux slice.

Archive basenames are discovery hints only.  A selected retail archive becomes
admissible only when its complete SHA-256 matches one of the source-backed
identities below and that identity resolves to exactly one materialized corpus
occurrence.  Byte-identical duplicate occurrences are deliberately not collapsed
into one semantic resource identity.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RetailArchiveIdentity:
    archive_name: str
    sha256: str
    evidence: str

    def as_dict(self) -> dict[str, str]:
        return {
            "archive_name": self.archive_name,
            "sha256": self.sha256,
            "evidence": self.evidence,
        }


# Current playable-slice target: Silverstone Era 3 Grand Prix.
_TRACK_IDENTITIES: dict[tuple[str, str], RetailArchiveIdentity] = {
    (
        "silverstone_era3_grandprix",
        "visual",
    ): RetailArchiveIdentity(
        archive_name="Silverstone_Era3_GrandPrix.bff",
        sha256="aac2e1fe721aec25494d0bfc84eac2bd49d1628fe55b165097ae694ef7a7d56c",
        evidence="evidence/silverstone_era3_imb_corpus.json",
    ),
    (
        "silverstone_era3_grandprix",
        "physics",
    ): RetailArchiveIdentity(
        archive_name="Silverstone_Era3_GrandPrix_Physics.bff",
        sha256="b90b70a1965260599570efef5bce4a76e5f96732c9831e6614e8541b886edbd7",
        evidence="evidence/silverstone_era3_imb_corpus.json",
    ),
}


# Current playable-slice target: BMW M3 E36.
_VEHICLE_IDENTITIES: dict[tuple[str, str], RetailArchiveIdentity] = {
    (
        "bmw_m3_e36",
        "primary",
    ): RetailArchiveIdentity(
        archive_name="BMW_M3_E36.bff",
        sha256="c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70",
        evidence="docs/render-evidence/bmw_m3_e36_render_bff_evidence.json",
    ),
    (
        "bmw_m3_e36",
        "cockpit",
    ): RetailArchiveIdentity(
        archive_name="BMW_M3_E36_Cockpit.bff",
        sha256="a9bc1b3c0dfb21408913089d565fa2ffc80f2fb2c4a408ab9aef101d012f15be",
        evidence="docs/render-evidence/bmw_m3_e36_render_bff_evidence.json",
    ),
}


_RENDER_IDENTITIES: dict[str, RetailArchiveIdentity] = {
    "render.bff": RetailArchiveIdentity(
        archive_name="RENDER.bff",
        sha256="b0b03960ba7e620b7ad5e2b027ed13de67afffe168eb8b30da73c2a632a7c0af",
        evidence="docs/render-evidence/bmw_m3_e36_render_bff_evidence.json",
    ),
}


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def track_archive_identity(track: str, role: str) -> RetailArchiveIdentity | None:
    return _TRACK_IDENTITIES.get((str(track).casefold(), str(role).casefold()))


def vehicle_archive_identity(vehicle: str, role: str) -> RetailArchiveIdentity | None:
    return _VEHICLE_IDENTITIES.get((str(vehicle).casefold(), str(role).casefold()))


def render_archive_identity(archive_name: str) -> RetailArchiveIdentity | None:
    return _RENDER_IDENTITIES.get(str(archive_name).casefold())
