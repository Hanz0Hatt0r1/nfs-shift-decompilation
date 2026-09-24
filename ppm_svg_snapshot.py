"""Convert a captured P6 PPM frame into a compact GitHub-visible SVG snapshot."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def _tokens(data: bytes):
    i = 0
    n = len(data)
    while i < n:
        while i < n and data[i] in b" \t\r\n":
            i += 1
        if i >= n:
            break
        if data[i] == 35:  # '#'
            while i < n and data[i] not in b"\r\n":
                i += 1
            continue
        start = i
        while i < n and data[i] not in b" \t\r\n":
            i += 1
        yield data[start:i]


def read_ppm(path: str | Path) -> tuple[int, int, bytes]:
    data = Path(path).read_bytes()
    if not data.startswith(b"P6"):
        raise ValueError("only binary P6 PPM is supported")
    tokens = _tokens(data)
    magic = next(tokens)
    width = int(next(tokens))
    height = int(next(tokens))
    max_value = int(next(tokens))
    if magic != b"P6" or max_value != 255:
        raise ValueError("PPM must be P6 with max value 255")
    header = b"P6"
    # Locate the payload by re-parsing the header robustly.
    marker = f"{width} {height} 255".encode()
    pos = data.find(marker)
    if pos < 0:
        raise ValueError("PPM header not found")
    payload_start = pos + len(marker)
    while payload_start < len(data) and data[payload_start] in b" \t\r\n":
        payload_start += 1
    pixels = data[payload_start:]
    expected = width * height * 3
    if len(pixels) != expected:
        raise ValueError(f"PPM payload size mismatch: {len(pixels)} != {expected}")
    return width, height, pixels


def _sample(
    width: int,
    height: int,
    pixels: bytes,
    out_width: int,
    out_height: int,
) -> list[tuple[int, int, int]]:
    result = []
    for y in range(out_height):
        source_y = min(height - 1, int((y + 0.5) * height / out_height))
        for x in range(out_width):
            source_x = min(width - 1, int((x + 0.5) * width / out_width))
            offset = (source_y * width + source_x) * 3
            result.append(tuple(pixels[offset:offset + 3]))
    return result


def ppm_to_svg(
    input_path: str | Path,
    output_path: str | Path,
    *,
    max_width: int = 80,
    max_height: int = 60,
) -> dict[str, int | str]:
    width, height, pixels = read_ppm(input_path)
    if max_width <= 0 or max_height <= 0:
        raise ValueError("snapshot dimensions must be positive")
    scale = min(max_width / width, max_height / height, 1.0)
    out_width = max(1, int(round(width * scale)))
    out_height = max(1, int(round(height * scale)))
    samples = _sample(width, height, pixels, out_width, out_height)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    input_sha = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()

    # SVG uses a regular cell grid; each cell is a representative pixel from
    # the captured frame, keeping the result small enough for source control.
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" ',
        f'viewBox="0 0 {out_width} {out_height}" role="img" ',
        f'aria-labelledby="title desc"><title id="title">SHIFT D3D9 captured frame snapshot</title>',
        f'<desc id="desc">Generated from P6 frame {input_sha}; source {width}x{height}, snapshot {out_width}x{out_height}.</desc>',
    ]
    for index, (r, g, b) in enumerate(samples):
        x = index % out_width
        y = index // out_width
        parts.append(
            f'<rect x="{x}" y="{y}" width="1" height="1" '
            f'fill="rgb({r},{g},{b})"/>'
        )
    parts.append("</svg>\n")
    output.write_text("".join(parts), encoding="utf-8")
    return {
        "format": "SHIFT.PPMSnapshotSVG/1",
        "input_sha256": input_sha,
        "source_width": width,
        "source_height": height,
        "snapshot_width": out_width,
        "snapshot_height": out_height,
        "output": str(output),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a captured P6 PPM frame to compact GitHub-visible SVG"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-width", type=int, default=80)
    parser.add_argument("--max-height", type=int, default=60)
    args = parser.parse_args(argv)
    print(ppm_to_svg(
        args.input,
        args.output,
        max_width=args.max_width,
        max_height=args.max_height,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
