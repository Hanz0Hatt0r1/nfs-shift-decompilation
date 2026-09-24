"""Convert a captured P6 PPM frame into a compact quantized SVG snapshot.

The SVG intentionally downsamples and run-length-encodes horizontal pixels so
large D3D9 screenshots can be reviewed directly in GitHub without committing
the original capture or game assets.
"""
from __future__ import annotations

import argparse
import html
from pathlib import Path


def read_ppm(path: str | Path) -> tuple[int, int, bytes]:
    data = Path(path).read_bytes()
    if not data.startswith(b"P6"):
        raise ValueError("expected binary P6 PPM")
    pos = 2

    def token() -> bytes:
        nonlocal pos
        while pos < len(data) and data[pos] in b" \t\r\n":
            pos += 1
        if pos >= len(data):
            raise ValueError("truncated PPM header")
        start = pos
        while pos < len(data) and data[pos] not in b" \t\r\n":
            pos += 1
        return data[start:pos]

    width = int(token())
    height = int(token())
    max_value = int(token())
    if max_value != 255:
        raise ValueError("only 8-bit PPM is supported")
    while pos < len(data) and data[pos] in b" \t\r\n":
        pos += 1
    pixels = data[pos:]
    if len(pixels) != width * height * 3:
        raise ValueError(
            f"PPM payload size mismatch: expected {width*height*3}, got {len(pixels)}"
        )
    return width, height, pixels


def _quantize(value: int, levels: int) -> int:
    if levels <= 1:
        return 0
    return round(value * (levels - 1) / 255)


def ppm_to_svg(
    path: str | Path,
    *,
    max_width: int = 320,
    max_height: int = 200,
    levels: int = 16,
) -> str:
    width, height, pixels = read_ppm(path)
    scale = min(max_width / width, max_height / height, 1.0)
    out_w = max(1, int(round(width * scale)))
    out_h = max(1, int(round(height * scale)))

    rows: list[str] = []
    for oy in range(out_h):
        sy = min(height - 1, int(oy / scale))
        runs: list[tuple[int, tuple[int, int, int]]] = []
        last = None
        run_start = 0
        for ox in range(out_w):
            sx = min(width - 1, int(ox / scale))
            offset = (sy * width + sx) * 3
            rgb = (
                _quantize(pixels[offset], levels),
                _quantize(pixels[offset + 1], levels),
                _quantize(pixels[offset + 2], levels),
            )
            if rgb != last:
                if last is not None:
                    runs.append((ox - run_start, last))
                last = rgb
                run_start = ox
        if last is not None:
            runs.append((out_w - run_start, last))

        x = 0
        for run_width, rgb in runs:
            r = round(rgb[0] * 255 / max(1, levels - 1))
            g = round(rgb[1] * 255 / max(1, levels - 1))
            b = round(rgb[2] * 255 / max(1, levels - 1))
            rows.append(
                f'<path d="M{x} {oy}h{run_width}v1H{x}z" '
                f'fill="#{r:02x}{g:02x}{b:02x}"/>'
            )
            x += run_width

    title = html.escape(Path(path).name)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {out_w} {out_h}" shape-rendering="crispEdges">\n'
        f'<!-- D3D9 Present screenshot snapshot: {title}; '
        f'quantized {out_w}x{out_h}, {levels} levels/channel -->\n'
        + "\n".join(rows)
        + "\n</svg>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert D3D9 PPM capture to compact SVG")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--max-width", type=int, default=320)
    parser.add_argument("--max-height", type=int, default=200)
    parser.add_argument("--levels", type=int, default=16)
    args = parser.parse_args()
    svg = ppm_to_svg(
        args.input,
        max_width=args.max_width,
        max_height=args.max_height,
        levels=args.levels,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(
        {
            "input": str(args.input),
            "output": str(out),
            "bytes": out.stat().st_size,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
