"""Pure-Python desktop reference rasterizer for SHIFT mesh IR.

This is a geometry oracle, not the final material renderer. It consumes neutral
MEB JSON (or an equivalent mesh dictionary) and produces deterministic PPM output
without reading BFF archives or invoking the original game runtime.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import hashlib
from pathlib import Path
from typing import Any, Iterable

from render_command import validate_render_command
from static_draw import build_static_draw_contract
from texture_reference import sample_texture_2d