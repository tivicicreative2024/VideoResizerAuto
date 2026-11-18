"""One output plan for live review and FFmpeg, without modifying any file."""
from datetime import datetime
import os
from pathlib import Path
import re

FORMATS = [(1080, 1080), (1920, 1080), (1080, 1920)]
RATIOS = {(1080, 1080): "1x1", (1920, 1080): "16x9", (1080, 1920): "9x16"}
DEFAULT_TEMPLATE = "%F_%S"


def validate_name(name):
    if (not name.strip() or name.endswith((" ", "."))
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or len(name.encode("utf-16-le")) // 2 > 255):
        raise ValueError("Tên file không hợp lệ: tránh ký tự < > : \" / \\ | ? *, dấu chấm/khoảng trắng cuối tên và tên quá dài.")
    base = name.split(".")[0].rstrip(" ").upper()
    if base in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", base):
        raise ValueError(f"Windows không cho phép tên '{base}'. Hãy dùng tên khác.")


def plan_outputs(files, output_dir, formats, template=DEFAULT_TEMPLATE, start=1, padding=3, date=None):
    if not formats or any(tuple(size) not in RATIOS for size in formats):
        raise ValueError("Chọn ít nhất một tỉ lệ đầu ra hợp lệ.")
    if not isinstance(start, int) or start < 1 or not isinstance(padding, int) or not 1 <= padding <= 6:
        raise ValueError("Số bắt đầu phải từ 1; số chữ số phải từ 1 đến 6.")
    if not template or "%" in re.sub(r"%[FNSD%]", "", template):
        raise ValueError("Mẫu tên chỉ hỗ trợ %F, %N, %S, %D và %%.")
    day = date or datetime.now().astimezone().strftime("%Y%m%d")
    key = lambda path: os.path.abspath(path).casefold()
    reserved = {key(f) for f in files}
    rows = []
    # Validate even before sources are selected, so the inline error is useful.
    sample = re.sub(r"%([FNSD%])", lambda m: {"F": "video", "N": str(start), "S": "9x16", "D": day, "%": "%"}[m[1]], template)
    validate_name(sample)
    for file in files:
        source = Path(file)
        directory = Path(output_dir) if output_dir else source.parent
        for width, height in formats:
            number = start + len(rows)
            ratio = RATIOS[(width, height)]
            tokens = {"F": source.stem, "N": str(number).zfill(padding), "S": ratio, "D": day, "%": "%"}
            stem = re.sub(r"%([FNSD%])", lambda m: tokens[m[1]], template)
            validate_name(stem)
            output = directory / (stem + source.suffix)
            counter = 1
            while key(output) in reserved or os.path.lexists(output):
                counter += 1
                output = directory / f"{stem}-{counter}{source.suffix}"
            validate_name(output.name)
            reserved.add(key(output))
            rows.append({"input": str(file), "output": str(output), "width": width, "height": height,
                         "ratio": ratio, "number": number, "renamed": counter > 1})
    return rows
