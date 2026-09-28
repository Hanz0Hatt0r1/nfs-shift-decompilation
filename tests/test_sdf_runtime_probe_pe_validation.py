from d3d9_pe_evidence import PEImage, PESection
import sdf_runtime_probe_pe_validation as runtime


def _fake_image() -> PEImage:
    sections = (
        PESection(
            name=".text",
            virtual_address=0x1000,
            virtual_size=0x400000,
            raw_pointer=0x400,
            raw_size=0x400000,
        ),
    )
    data = bytearray(0x400400)
    for name, address in runtime.FUNCTIONS.items():
        rva = address - runtime.IMAGE_BASE
        offset = 0x400 + (rva - 0x1000)
        prologue = runtime.EXPECTED_PROLOGUES[name]
        data[offset:offset + len(prologue)] = prologue
    return PEImage(
        data=bytes(data),
        image_base=runtime.IMAGE_BASE,
        machine=0x014C,
        optional_magic=0x10B,
        sections=sections,
    )


def test_probe_targets_validate_known_image_and_prologues():
    result = runtime.validate_probe_targets(_fake_image())
    assert result["ready"] is True
    assert result["status"] == "validated"
    assert all(item["matches"] for item in result["targets"].values())


def test_probe_targets_block_wrong_image_base():
    image = _fake_image()
    wrong = PEImage(
        data=image.data,
        image_base=0x500000,
        machine=image.machine,
        optional_magic=image.optional_magic,
        sections=image.sections,
    )
    result = runtime.validate_probe_targets(wrong)
    assert result["ready"] is False
    assert any(error.startswith("image-base:") for error in result["errors"])


def test_probe_targets_block_wrong_prologue():
    image = _fake_image()
    data = bytearray(image.data)
    address = runtime.FUNCTIONS["builtin_solver"]
    rva = address - runtime.IMAGE_BASE
    offset = 0x400 + (rva - 0x1000)
    data[offset] ^= 0xFF
    modified = PEImage(
        data=bytes(data),
        image_base=image.image_base,
        machine=image.machine,
        optional_magic=image.optional_magic,
        sections=image.sections,
    )
    result = runtime.validate_probe_targets(modified)
    assert result["ready"] is False
    assert "builtin_solver:prologue-mismatch" in result["errors"]


def test_probe_targets_block_non_i386_machine():
    image = _fake_image()
    wrong = PEImage(
        data=image.data,
        image_base=image.image_base,
        machine=0x8664,
        optional_magic=image.optional_magic,
        sections=image.sections,
    )
    result = runtime.validate_probe_targets(wrong)
    assert result["ready"] is False
    assert "machine:0x8664!=0x14c" in result["errors"]


def test_probe_contract_matches_supplied_retail_executable():
    report = runtime.describe_probe_pe_validation_contract()
    assert report["executable"]["sha256"] == runtime.EXPECTED_EXECUTABLE_SHA256
    assert report["executable"]["image_base"] == "0x00400000"
    assert report["targets"]["builtin_solver"]["address"] == "0x007b0f20"
    assert report["targets"]["post_solve"]["address"] == "0x007b4110"


def test_probe_cli_parser_supports_sha_override():
    import tools.validate_sdf_probe_pe as cli
    args = cli.build_parser().parse_args([
        "SHIFT.exe",
        "--allow-other-sha256",
    ])
    assert args.allow_other_sha256 is True
