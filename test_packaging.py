"""Run with the build virtual environment after building the Windows bundle."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication
import video_resizer as vr


def main():
    bundle = Path(__file__).parent / "dist" / "VideoResizer" / "_internal"
    with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", str(bundle), create=True):
        ffmpeg = vr.get_ffmpeg_binary()
    assert Path(ffmpeg).is_file(), "Bundled FFmpeg is missing"
    assert bundle in Path(ffmpeg).parents, "FFmpeg must come from the bundle"
    assert not (bundle / "profiles.json").exists(), "Do not distribute personal profiles"
    assert (bundle / "ui_theme.qss").is_file(), "Packaged UI theme is missing"
    for name in ["BeVietnamPro-Regular.ttf", "BeVietnamPro-Bold.ttf", "JetBrainsMono-Regular.ttf", "brand.png", "upload.svg"]:
        assert (bundle / "assets" / name).stat().st_size > 0, f"Packaged asset missing: {name}"
    vr.FFMPEG_CMD = ffmpeg
    cpu = "CPU (libx264 - Cân bằng)"
    vr.AVAILABLE_ENCODERS = {cpu: ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p"]}
    app = QApplication([])
    with tempfile.TemporaryDirectory(prefix="VideoResizer-test-") as folder:
        with patch.object(sys, "frozen", True, create=True), patch.object(vr.QStandardPaths, "writableLocation", return_value=folder):
            window = vr.VideoResizerApp()
            assert Path(window.profiles_file) == Path(folder) / "VideoResizer" / "profiles.json"
            assert list(window.profiles) == ["Mặc định"]
            window.save_profiles_to_disk()
            assert json.loads(Path(window.profiles_file).read_text(encoding="utf-8"))["profiles"] == window.profiles
            window.load_profiles()
            assert list(window.profiles) == ["Mặc định"]
            window.close()
        source = str(Path(folder) / "nguồn thử.mp4")
        subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=0.3", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.3", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", source], check=True, capture_output=True)
        worker = vr.WorkerThread([source], folder, True, True, True, None, None, None, render_mode="low_spec", selected_encoder=cpu)
        for width, height in [(1080, 1080), (1920, 1080), (1080, 1920)]:
            output = str(Path(folder) / f"result-{width}x{height}.mp4")
            assert worker.run_ffmpeg(source, width, height, output)
            probe = subprocess.run([ffmpeg, "-i", output], capture_output=True).stderr.decode("utf-8", errors="replace")
            assert f"{width}x{height}" in probe and "Audio: aac" in probe, probe
            subprocess.run([ffmpeg, "-v", "error", "-i", output, "-f", "null", "-"], check=True, capture_output=True)
            print(f"PASS: {width}x{height}, audio, Unicode paths, decoded output")
    print("PASS: bundled FFmpeg, clean defaults, writable profiles and reload")


if __name__ == "__main__":
    main()
