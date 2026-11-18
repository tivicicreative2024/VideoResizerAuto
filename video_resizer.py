import sys
import os
import subprocess
import json
import tempfile
import shutil
import re
from output_naming import plan_outputs, FORMATS, DEFAULT_TEMPLATE
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QCheckBox, QPushButton, QFileDialog, QListWidget, 
                             QProgressBar, QTextEdit, QMessageBox, QFrame, QComboBox, QInputDialog, QSpinBox, QDialog, QTableWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QStandardPaths
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap
from resizer_ui import build_ui, ThumbnailWorker

def get_ffmpeg_binary():
    # 1. PyInstaller frozen environment
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        candidates = [
            os.path.join(base_dir, "ffmpeg.exe"),
            os.path.join(base_dir, "ffmpeg"),
            os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe"),
        ]
        bin_dir = os.path.join(base_dir, "imageio_ffmpeg", "binaries")
        if os.path.isdir(bin_dir):
            for f in os.listdir(bin_dir):
                if f.startswith("ffmpeg"):
                    candidates.insert(0, os.path.join(bin_dir, f))
        for cand in candidates:
            if os.path.isfile(cand):
                return cand

    # 2. imageio_ffmpeg default
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    # 3. System PATH fallback
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    return "ffmpeg"

FFMPEG_CMD = get_ffmpeg_binary()

AVAILABLE_ENCODERS = {}

def get_available_encoders():
    global AVAILABLE_ENCODERS
    if AVAILABLE_ENCODERS:
        return AVAILABLE_ENCODERS

    encoders = {}
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    candidates = []
    if sys.platform == 'win32':
        candidates = [
            ('NVIDIA NVENC (GPU)', ['-c:v', 'h264_nvenc', '-preset', 'p4', '-cq', '23', '-b:v', '0', '-pix_fmt', 'yuv420p']),
            ('Intel QSV (GPU)', ['-c:v', 'h264_qsv', '-global_quality', '23', '-preset', 'veryfast', '-pix_fmt', 'nv12']),
            ('AMD AMF (GPU)', ['-c:v', 'h264_amf', '-quality', 'speed', '-rc', 'cbr', '-b:v', '6000k', '-pix_fmt', 'yuv420p']),
        ]
    elif sys.platform == 'darwin':
        candidates = [
            ('Apple VideoToolbox (GPU)', ['-c:v', 'h264_videotoolbox', '-b:v', '6000k', '-pix_fmt', 'yuv420p']),
        ]

    for name, args in candidates:
        try:
            cmd = [FFMPEG_CMD, '-f', 'lavfi', '-i', 'testsrc=duration=1:size=320x240:rate=30'] + args + ['-f', 'null', '-']
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
            if res.returncode == 0:
                encoders[name] = args
        except Exception:
            pass

    encoders['CPU (libx264 - Siêu nhanh cho máy yếu)'] = ['-c:v', 'libx264', '-preset', 'superfast', '-crf', '23', '-pix_fmt', 'yuv420p']
    encoders['CPU (libx264 - Cân bằng)'] = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p']

    AVAILABLE_ENCODERS = encoders
    return AVAILABLE_ENCODERS

def detect_best_encoder():
    available = get_available_encoders()
    for name, args in available.items():
        if 'GPU' in name:
            return name, args
    if 'CPU (libx264 - Cân bằng)' in available:
        return 'CPU (libx264 - Cân bằng)', available['CPU (libx264 - Cân bằng)']
    return 'CPU (libx264 - Siêu nhanh cho máy yếu)', available['CPU (libx264 - Siêu nhanh cho máy yếu)']


class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(int, int, str)
    output_signal = pyqtSignal(int, bool)

    def __init__(self, input_files, output_dir, do_square, do_horizontal, do_vertical, 
                 outro_square, outro_horizontal, outro_vertical, icon_settings=None, video_scales=None,
                 render_mode="balanced", selected_encoder="Tự động phát hiện", limit_30fps=False, output_plan=None):
        super().__init__()
        self.input_files = list(input_files)
        self.output_dir = output_dir
        self.do_square = do_square
        self.do_horizontal = do_horizontal
        self.do_vertical = do_vertical
        self.outro_square = outro_square
        self.outro_horizontal = outro_horizontal
        self.outro_vertical = outro_vertical
        self.icon_settings = {key: value.copy() for key, value in (icon_settings or {}).items()}
        self.video_scales = dict(video_scales or {})
        self.render_mode = render_mode
        self.selected_encoder = selected_encoder
        self.limit_30fps = limit_30fps
        self.output_plan = output_plan

    def run(self):
        total_files = len(self.input_files)
        success_count = 0
        save_dir = self.output_dir or (os.path.dirname(self.input_files[0]) if total_files else "")
        try:
            formats = [size for size, checked in zip(FORMATS, [self.do_square, self.do_horizontal, self.do_vertical]) if checked]
            plan = self.output_plan if self.output_plan is not None else plan_outputs(self.input_files, self.output_dir, formats)
            outros = {(1080, 1080): self.outro_square, (1920, 1080): self.outro_horizontal, (1080, 1920): self.outro_vertical}
            for index, source in enumerate(self.input_files, 1):
                self.log_signal.emit(f"[{index}/{total_files}] Đang xử lý: {os.path.basename(source)}")
                success = True
                for row_index, row in enumerate(plan):
                    if row["input"] != source:
                        continue
                    ok = self.run_ffmpeg(source, row["width"], row["height"], row["output"],
                                         outros[(row["width"], row["height"])], self.video_scales.get(source, 100),
                                         self.icon_settings.get(source))
                    self.output_signal.emit(row_index, ok)
                    success = success and ok
                success_count += int(success)
                self.progress_signal.emit(index, total_files)
        except (OSError, ValueError) as error:
            self.log_signal.emit(f"Lỗi xử lý: {error}")
        finally:
            self.finished_signal.emit(success_count, total_files, save_dir)

    def has_audio(self, file_path):
        # imageio-ffmpeg chỉ cung cấp ffmpeg, không có ffprobe, nhưng có thể dùng ffmpeg để check audio
        cmd = [FFMPEG_CMD, '-i', file_path]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
            output = result.stderr.decode('utf-8', errors='ignore')
            return 'Audio:' in output
        except Exception:
            return False

    def media_duration(self, file_path):
        """Seconds from ffmpeg's 'Duration:' line, or None; bounds the silent track for files without audio."""
        cmd = [FFMPEG_CMD, '-i', file_path]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
            match = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', result.stderr.decode('utf-8', errors='ignore'))
            return int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3]) if match else None
        except Exception:
            return None

    def silent_input(self, file_path):
        # anullsrc is endless: without -t, concat never sees the segment end and FFmpeg runs forever.
        duration = self.media_duration(file_path)
        if not duration:
            raise OSError(f"Không đọc được thời lượng của {os.path.basename(file_path)} để tạo âm thanh im lặng.")
        return ['-f', 'lavfi', '-t', f'{duration:.3f}', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100']

    def run_ffmpeg(self, input_file, target_width, target_height, output_file, outro_file=None, video_scale=100, icon_set=None):
        try:
            if os.path.lexists(output_file):
                raise FileExistsError(f"Đã có file {output_file}; không ghi đè. Hãy cập nhật danh sách tên.")
            # Only private staging files may be overwritten during a GPU-to-CPU retry.
            directory = os.path.dirname(os.path.abspath(output_file))
            with tempfile.TemporaryDirectory(prefix=".videoresizer-", dir=directory) as staging:
                temp_output = os.path.join(staging, os.path.basename(output_file))
                if not self._encode_video(input_file, target_width, target_height, temp_output, outro_file, video_scale, icon_set):
                    return False
                if not os.path.isfile(temp_output) or os.path.getsize(temp_output) == 0:
                    raise OSError("FFmpeg không tạo được video đầu ra hợp lệ.")
                if os.name == 'nt':
                    os.rename(temp_output, output_file)
                else:
                    # Exclusive creation keeps the same no-overwrite guarantee on other platforms.
                    with open(output_file, 'xb') as destination:
                        try:
                            with open(temp_output, 'rb') as source:
                                shutil.copyfileobj(source, destination)
                        except BaseException:
                            destination.close()
                            os.unlink(output_file)
                            raise
            return True
        except OSError as error:
            self.log_signal.emit(f"Lỗi xuất {os.path.basename(output_file)}: {error}")
            return False

    def _encode_video(self, input_file, target_width, target_height, output_file, outro_file=None, video_scale=100, icon_set=None):
        inputs = ['-y', '-threads', '0', '-i', input_file]
        input_idx = 1
        
        has_a_main = self.has_audio(input_file)
        
        if outro_file:
            inputs.extend(['-threads', '0', '-i', outro_file])
            outro_idx = input_idx
            input_idx += 1
            has_a_outro = self.has_audio(outro_file)
        
        if icon_set and icon_set.get("path"):
            inputs.extend(['-i', icon_set["path"]])
            icon_idx = input_idx
            input_idx += 1
            
        # Tối ưu hóa bộ lọc mờ nền theo chế độ render (Render Performance Modes):
        # - low_spec: Downscale 1/4 + boxblur(10:3) + upscale bicubic (nhanh gấp 5-6 lần, siêu nhẹ cho CPU)
        # - balanced: Downscale 1/3 + boxblur(13:3) + upscale bicubic (mịn mượt, cân bằng hoàn hảo)
        # - high_quality: Giữ nguyên Full Gaussian Blur (radius=40, power=3)
        if self.render_mode == "low_spec":
            bg_w = max(16, (target_width // 4) & ~1)
            bg_h = max(16, (target_height // 4) & ~1)
            bg_filter = (
                f"[0:v]split=2[in_bg][in_fg];"
                f"[in_bg]scale={bg_w}:{bg_h}:force_original_aspect_ratio=increase,"
                f"crop={bg_w}:{bg_h},"
                f"boxblur=luma_radius=10:luma_power=3:chroma_radius=10:chroma_power=3,"
                f"scale={target_width}:{target_height}:flags=bicubic[bg];"
            )
        elif self.render_mode == "high_quality":
            bg_filter = (
                f"[0:v]split=2[in_bg][in_fg];"
                f"[in_bg]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
                f"crop={target_width}:{target_height},"
                f"boxblur=luma_radius=40:luma_power=3:chroma_radius=40:chroma_power=3[bg];"
            )
        else: # "balanced" (mặc định)
            bg_w = max(16, (target_width // 3) & ~1)
            bg_h = max(16, (target_height // 3) & ~1)
            bg_filter = (
                f"[0:v]split=2[in_bg][in_fg];"
                f"[in_bg]scale={bg_w}:{bg_h}:force_original_aspect_ratio=increase,"
                f"crop={bg_w}:{bg_h},"
                f"boxblur=luma_radius=13:luma_power=3:chroma_radius=13:chroma_power=3,"
                f"scale={target_width}:{target_height}:flags=bicubic[bg];"
            )

        fg_filter = f"[in_fg]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease[fg_base];"
        if video_scale != 100:
            fg_filter += f"[fg_base]scale=iw*{video_scale}/100:ih*{video_scale}/100[fg];"
        else:
            fg_filter += f"[fg_base]copy[fg];"
            
        v_filter = bg_filter + fg_filter + f"[bg][fg]overlay=(W-w)/2:(H-h)/2"

        if self.limit_30fps and not outro_file:
            v_filter += f",fps=30"
        
        if outro_file:
            v_filter += f",setsar=1,fps=30[main_v];"
            v_filter += (
                f"[{outro_idx}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[outro_v];"
            )
        else:
            v_filter += f"[main_v];"
            
        if icon_set and icon_set.get("path"):
            scale_str = f"iw*{icon_set['scale']/100}:ih*{icon_set['scale']/100}"
            v_filter += f"[{icon_idx}:v]scale={scale_str}[icon];"
            v_filter += f"[main_v][icon]overlay={icon_set['x']}:{icon_set['y']}[main_v_icon];"
        else:
            v_filter += f"[main_v]copy[main_v_icon];"
            
        available = get_available_encoders()
        if self.selected_encoder and self.selected_encoder != "Tự động phát hiện" and self.selected_encoder in available:
            enc_name = self.selected_encoder
            enc_args = list(available[self.selected_encoder])
        else:
            enc_name, enc_args = detect_best_encoder()
            enc_args = list(enc_args)

        if outro_file:
            if has_a_main: main_a = "[0:a]"
            else:
                inputs.extend(self.silent_input(input_file))
                main_a = f"[{input_idx}:a]"; input_idx += 1
                
            if has_a_outro: outro_a = f"[{outro_idx}:a]"
            else:
                inputs.extend(self.silent_input(outro_file))
                outro_a = f"[{input_idx}:a]"; input_idx += 1
                
            filter_complex = v_filter + f"[main_v_icon]{main_a}[outro_v]{outro_a}concat=n=2:v=1:a=1[outv][outa]"
            cmd = [FFMPEG_CMD] + inputs + ['-filter_complex_threads', '0', '-filter_complex', filter_complex, '-map', '[outv]', '-map', '[outa]'] + enc_args + ['-c:a', 'aac', '-b:a', '192k', '-threads', '0', output_file]
        else:
            filter_complex = v_filter
            cmd = [FFMPEG_CMD] + inputs + ['-filter_complex_threads', '0', '-filter_complex', filter_complex, '-map', '[main_v_icon]'] + enc_args
            if has_a_main:
                cmd.extend(['-map', '0:a?', '-c:a', 'aac', '-b:a', '192k'])
            cmd.extend(['-threads', '0', output_file])
            
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        if sys.platform == 'win32' and hasattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS'):
            creationflags |= subprocess.BELOW_NORMAL_PRIORITY_CLASS

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
            self.log_signal.emit(f"  -> Xong: {os.path.basename(output_file)}")
            return True
        except (subprocess.CalledProcessError, OSError):
            # Fallback sang CPU nếu mã hóa GPU gặp trục trặc
            if 'GPU' in enc_name:
                self.log_signal.emit(f"  -> Tự động chuyển CPU dự phòng cho: {os.path.basename(output_file)}")
                if self.render_mode == "low_spec":
                    cpu_args = ['-c:v', 'libx264', '-preset', 'superfast', '-crf', '23', '-pix_fmt', 'yuv420p']
                else:
                    cpu_args = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p']
                if outro_file:
                    fallback_cmd = [FFMPEG_CMD] + inputs + ['-filter_complex_threads', '0', '-filter_complex', filter_complex, '-map', '[outv]', '-map', '[outa]'] + cpu_args + ['-c:a', 'aac', '-b:a', '192k', '-threads', '0', output_file]
                else:
                    fallback_cmd = [FFMPEG_CMD] + inputs + ['-filter_complex_threads', '0', '-filter_complex', filter_complex, '-map', '[main_v_icon]'] + cpu_args
                    if has_a_main:
                        fallback_cmd.extend(['-map', '0:a?', '-c:a', 'aac', '-b:a', '192k'])
                    fallback_cmd.extend(['-threads', '0', output_file])
                try:
                    subprocess.run(fallback_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
                    self.log_signal.emit(f"  -> Xong (CPU): {os.path.basename(output_file)}")
                    return True
                except (subprocess.CalledProcessError, OSError):
                    pass
            self.log_signal.emit(f"  -> Lỗi khi xử lý file ra kích thước {target_width}x{target_height}")
            return False

class PreviewDialog(QDialog):
    def __init__(self, image_path, target_width, target_height, icon_path, icon_x, icon_y, icon_scale, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.target_width = target_width
        self.target_height = target_height
        self.icon_path = icon_path
        self.icon_x = icon_x
        self.icon_y = icon_y
        self.icon_scale = icon_scale
        self.scale_factor = 1.0
        
        self.setWindowTitle("Xem trước Video (Kéo thả Icon để di chuyển)")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #0b1026; color: #f7f7f6;")
        
        layout = QVBoxLayout(self)
        self.view_container = QWidget()
        self.view_container.setStyleSheet("background-color: transparent;")
        layout.addWidget(self.view_container, alignment=Qt.AlignCenter)
        
        self.img_label = QLabel(self.view_container)
        self.img_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.icon_label = QLabel(self.view_container)
        self.icon_label.hide()
        
        self.dragging = False
        self.drag_offset = QPoint()
        
        self.load_image(image_path)

    def load_image(self, image_path):
        pixmap = QPixmap(image_path)
        if pixmap.width() > 1280 or pixmap.height() > 720:
            scaled_pixmap = pixmap.scaled(1280, 720, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.scale_factor = scaled_pixmap.width() / pixmap.width()
            pixmap = scaled_pixmap
        else:
            self.scale_factor = 1.0
            
        self.img_label.setPixmap(pixmap)
        self.img_label.resize(pixmap.size())
        self.view_container.setFixedSize(pixmap.size())
        
        self.update_icon()

    def update_icon(self):
        if self.icon_path and isinstance(self.icon_path, str) and os.path.exists(self.icon_path):
            icon_pixmap = QPixmap(self.icon_path)
            w = int(icon_pixmap.width() * (self.icon_scale / 100.0) * self.scale_factor)
            h = int(icon_pixmap.height() * (self.icon_scale / 100.0) * self.scale_factor)
            
            if w > 0 and h > 0:
                icon_pixmap = icon_pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_label.setPixmap(icon_pixmap)
                self.icon_label.resize(icon_pixmap.size())
                
                ix = int(self.icon_x * self.scale_factor)
                iy = int(self.icon_y * self.scale_factor)
                self.icon_label.move(ix, iy)
                self.icon_label.show()
            else:
                self.icon_label.hide()
        else:
            self.icon_label.hide()

    def update_image_and_icon(self, image_path, target_width, target_height, icon_path, icon_x, icon_y, icon_scale):
        self.target_width = target_width
        self.target_height = target_height
        self.icon_path = icon_path
        self.icon_x = icon_x
        self.icon_y = icon_y
        self.icon_scale = icon_scale
        self.load_image(image_path)

    def mousePressEvent(self, event):
        if self.icon_label.isVisible() and event.button() == Qt.LeftButton:
            pos = event.pos()
            mapped_pos = self.view_container.mapFrom(self, pos)
            if self.icon_label.geometry().contains(mapped_pos):
                self.dragging = True
                self.drag_offset = mapped_pos - self.icon_label.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.icon_label.isVisible():
            pos = event.pos()
            mapped_pos = self.view_container.mapFrom(self, pos)
            new_pos = mapped_pos - self.drag_offset
            
            max_x = self.view_container.width() - self.icon_label.width()
            max_y = self.view_container.height() - self.icon_label.height()
            
            new_pos.setX(max(0, min(new_pos.x(), max_x)))
            new_pos.setY(max(0, min(new_pos.y(), max_y)))
            
            self.icon_label.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            
            if self.scale_factor > 0:
                new_x = int(self.icon_label.pos().x() / self.scale_factor)
                new_y = int(self.icon_label.pos().y() / self.scale_factor)
                
                self.main_app.spin_x.blockSignals(True)
                self.main_app.spin_y.blockSignals(True)
                
                self.main_app.spin_x.setValue(new_x)
                self.main_app.spin_y.setValue(new_y)
                
                self.main_app.spin_x.blockSignals(False)
                self.main_app.spin_y.blockSignals(False)
                self.main_app.on_icon_setting_changed()

class VideoResizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Resizer Pro")
        self.resize(800, 760)
        self.setStyleSheet("background-color: #242424; color: white;")
        
        self.input_files = []
        self.video_scales = {}
        self.icon_settings = {}
        self.copied_video_scale = None
        self.copied_icon_settings = None
        self.outro_square = None
        self.outro_horizontal = None
        self.outro_vertical = None
        self.icon_path = None # Kept for profile compatibility if needed
        self.output_dir = None
        self.worker = None
        self.preview_dlg = None
        self.is_processing = False
        self.output_plan = []
        self._ui_ready = False
        self.thumbnail_worker = None
        self.thumbnail_pending = False
        self.thumbnail_pixmap = QPixmap()
        self.thumbnail_timer = QTimer(self)
        self.thumbnail_timer.setSingleShot(True)
        self.thumbnail_timer.timeout.connect(self.update_thumbnail)
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.generate_preview)

        if getattr(sys, 'frozen', False) and sys.platform == 'win32':
            # Keep user settings writable and separate from installer upgrades.
            app_dir = os.path.join(QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation), "VideoResizer")
            os.makedirs(app_dir, exist_ok=True)
        elif getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        self.profiles_file = os.path.join(app_dir, "profiles.json")
        self.profiles = {}

        self.setup_ui()
        self.load_profiles()
        enc_name, _ = detect_best_encoder()
        self.log(f"⚡ Tăng tốc render: {enc_name}")
        self.log("🚀 Sẵn sàng xử lý! Đã hỗ trợ tối ưu hóa render cho máy cấu hình yếu.")
        
        if not self.check_ffmpeg():
            self.log("LỖI: Không tìm thấy FFmpeg. Hãy đảm bảo FFmpeg đã được cài đặt và cấu hình PATH.")
            self.btn_start.setEnabled(False)

    def check_ffmpeg(self):
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run([FFMPEG_CMD, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
            return True
        except FileNotFoundError:
            return False

    def setup_ui(self):
        build_ui(self, get_available_encoders())
        self._ui_ready = True
        self.refresh_output_plan()
        self.set_step(0)

    def selected_formats(self):
        return [size for size, checkbox in zip(FORMATS, [self.chk_sq, self.chk_hz, self.chk_vt]) if checkbox.isChecked()]

    def naming_settings(self):
        return {"template": self.name_template.text(), "start": self.number_start.value(),
                "padding": self.number_padding.currentData()}

    def refresh_output_plan(self, *args):
        if not self._ui_ready or self.is_processing:
            return
        self.numbering_options.setVisible(any(match[1] == 'N' for match in re.finditer(r'%([FNSD%])', self.name_template.text())))
        error = ""
        try:
            self.output_plan = plan_outputs(self.input_files, self.output_dir, self.selected_formats(), **self.naming_settings())
        except ValueError as exc:
            self.output_plan = []
            error = str(exc)
        self.naming_error.setText(error)
        self.naming_error.setVisible(bool(error))
        self.review_error.setText(error)
        self.review_error.setVisible(bool(error))
        self.output_table.setRowCount(len(self.output_plan))
        for index, row in enumerate(self.output_plan):
            values = [os.path.basename(row["input"]), os.path.basename(row["output"]), row["ratio"].replace("x", ":"),
                      "Đã tránh trùng" if row["renamed"] else "Sẵn sàng"]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(row["output"] if col else row["input"])
                self.output_table.setItem(index, col, item)
            self.output_table.setRowHeight(index, 48)
        self.name_preview.setPlainText("\n".join(os.path.basename(row["output"]) for row in self.output_plan[:3])
                                       or ("Thêm video ở bước 1 để xem tên đầu ra." if not error else ""))
        self.output_summary.setText(f"{len(self.output_plan)} file đầu ra · {len(self.input_files)} video × {len(self.selected_formats())} tỉ lệ")
        self.btn_start.setText(f"Xuất {len(self.output_plan)} file")
        self.btn_start.setEnabled(bool(self.output_plan) and not self.is_processing)
        self.source_count.setText(f"{len(self.input_files)} video")
        step = self.steps.currentIndex()
        self.btn_next.setEnabled(bool(self.input_files) if step == 0 else bool(self.output_plan))
        self.btn_remove.setEnabled(bool(self.listbox.selectedItems()))
        self.btn_edit_video.setEnabled(bool(self.listbox.selectedItems()))
        if any(row["renamed"] for row in self.output_plan):
            self.review_error.setText("Đã thêm hậu tố cho tên trùng. Kiểm tra cột tên file trước khi xuất.")
            self.review_error.show()

    def set_step(self, step):
        if self.is_processing:
            return
        if step > 0 and not self.input_files:
            self.ui_status.setText("Thêm ít nhất một video để tiếp tục.")
            step = 0
        elif step == 2 and not self.output_plan:
            self.ui_status.setText("Kiểm tra tỉ lệ và mẫu tên trước khi tiếp tục.")
            step = 1
        step = max(0, min(step, 2))
        self.steps.setCurrentIndex(step)
        for i, btn in enumerate(self.step_buttons):
            btn.setChecked(i == step)
        self.btn_back.setVisible(step > 0)
        self.btn_next.setVisible(step < 2)
        self.btn_next.setText("Tiếp tục: Thiết lập" if step == 0 else "Tiếp tục: Kiểm tra")
        self.btn_start.setVisible(step == 2)
        self.step_guidance.setText([
            "Thêm video, chọn mục rồi mở Chỉnh video nếu cần logo hoặc phóng hình.",
            "Chọn tỉ lệ và tên file. Kiểm tra ví dụ bên dưới rồi tiếp tục.",
            "Xem lại danh sách và thư mục lưu trước khi xuất."
        ][step])
        self.refresh_output_plan()

    def add_video_paths(self, paths):
        if self.is_processing:
            return
        from resizer_ui import VIDEO_EXTENSIONS
        known = {os.path.abspath(path).casefold() for path in self.input_files}
        for path in paths:
            if os.path.splitext(path)[1].lower() not in VIDEO_EXTENSIONS or os.path.isdir(path):
                continue
            key = os.path.abspath(path).casefold()
            if key not in known:
                known.add(key)
                self.input_files.append(path)
                self.video_scales[path] = self.spin_video_scale.value()
                self.icon_settings[path] = {"path": self.icon_path, "x": self.spin_x.value(),
                                            "y": self.spin_y.value(), "scale": self.spin_scale.value()}
        self.update_listbox()
        self.ui_status.setText(f"Đã chọn {len(self.input_files)} video · Chọn Thiết lập xuất để tiếp tục.")

    def remove_selected_video(self):
        if self.is_processing:
            return
        for row in sorted([self.listbox.row(item) for item in self.listbox.selectedItems()], reverse=True):
            source = self.input_files.pop(row)
            self.video_scales.pop(source, None)
            self.icon_settings.pop(source, None)
        self.update_listbox()

    def open_video_editor(self):
        if self.is_processing or not self.listbox.selectedItems():
            return
        self.video_editor.show()
        self.video_editor.raise_()
        self.video_editor.activateWindow()

    def select_output_preview(self, row, column):
        if row < len(self.output_plan):
            output = self.output_plan[row]
            self.listbox.setCurrentRow(self.input_files.index(output["input"]))
            index = self.preview_ratio.findData((output["width"], output["height"]))
            self.preview_ratio.setCurrentIndex(index)
            self.request_thumbnail()

    def set_processing_state(self, busy):
        self.is_processing = busy
        if busy:
            self.video_editor.close()
        for control in [self.steps.widget(0), self.steps.widget(1), self.sidebar_scroll, self.video_editor, self.btn_profile_menu,
                        self.cb_profiles, self.btn_save_profile, self.btn_new_profile, self.btn_delete_profile,
                        self.btn_output, self.btn_back, self.btn_next] + self.step_buttons:
            control.setEnabled(not busy)
        self.btn_start.setEnabled(not busy and bool(self.output_plan))
        if busy:
            self.btn_start.setText("Đang xuất…")
            self.ui_status.setText("Đang xử lý · Giữ ứng dụng mở đến khi hoàn tất.")
        else:
            self.btn_start.setText(f"Xuất {len(self.output_plan)} file")

    def mark_output_finished(self, row, ok):
        if row < self.output_table.rowCount():
            self.output_table.setItem(row, 3, QTableWidgetItem("Hoàn tất" if ok else "Lỗi · xem nhật ký"))

    def request_thumbnail(self, *args):
        if not self._ui_ready:
            return
        self.thumbnail_pending = True
        self.thumbnail_timer.start(180)

    def update_thumbnail(self):
        if self.thumbnail_worker and self.thumbnail_worker.isRunning():
            return
        self.thumbnail_pending = False
        row = self.listbox.currentRow()
        if not 0 <= row < len(self.input_files):
            self.thumbnail_pixmap = QPixmap()
            self.thumbnail.clear()
            self.thumbnail.setText("Chọn video để xem trước")
            self.selected_video.setText("Chưa có video")
            return
        source = self.input_files[row]
        self.selected_video.setText(os.path.basename(source))
        if not os.path.isfile(source):
            self.thumbnail.clear()
            self.thumbnail.setText("Không tìm thấy video nguồn")
            return
        size = self.preview_ratio.currentData()
        self.preview_caption.setText(f"{size[0]} × {size[1]} · Ảnh xem trước đầu video")
        self.thumbnail_worker = ThumbnailWorker(FFMPEG_CMD, source, size, self.video_scales.get(source, 100),
                                               self.icon_settings.get(source, {}).copy(),
                                               self.cb_render_mode.currentData(), self)
        self.thumbnail_worker.finished.connect(self.thumbnail_finished)
        self.thumbnail_worker.start()

    def thumbnail_finished(self):
        worker = self.thumbnail_worker
        if not self.thumbnail_pending:
            if worker.data:
                self.thumbnail_pixmap.loadFromData(worker.data)
                self.thumbnail.setPixmap(self.thumbnail_pixmap.scaled(260, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.thumbnail.clear()
                self.thumbnail.setText(worker.error)
        self.thumbnail_worker = None
        worker.deleteLater()
        if self.thumbnail_pending:
            self.thumbnail_timer.start(50)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Đang xử lý", "Hãy chờ render hoàn tất trước khi đóng để tránh hỏng file đầu ra.")
            event.ignore()
            return
        self.video_editor.close()
        self.thumbnail_timer.stop()
        if self.thumbnail_worker:
            self.thumbnail_worker.wait(22000)
        if self.preview_dlg:
            self.preview_dlg.close()
        super().closeEvent(event)

    def log(self, message):
        self.log_box.append(message)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def load_profiles(self):
        self.profiles = {}
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.profiles = data.get("profiles", {})
            except Exception as e:
                self.log(f"Lỗi khi tải hồ sơ: {e}")
        
        self.cb_profiles.blockSignals(True)
        self.cb_profiles.clear()
        if self.profiles:
            self.cb_profiles.addItems(list(self.profiles.keys()))
        else:
            self.cb_profiles.addItem("Mặc định")
            self.profiles["Mặc định"] = {"outro_square": None, "outro_horizontal": None, "outro_vertical": None, "icon_path": None, "icon_x": 10, "icon_y": 10, "icon_scale": 100, "video_scale": 100}
        self.cb_profiles.blockSignals(False)
        self.on_profile_changed()

    def save_profiles_to_disk(self):
        try:
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump({"profiles": self.profiles}, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.log(f"Lỗi khi lưu hồ sơ: {e}")

    def profile_settings(self):
        return {
            "outro_square": self.outro_square, "outro_horizontal": self.outro_horizontal,
            "outro_vertical": self.outro_vertical, "icon_path": self.icon_path,
            "icon_x": self.spin_x.value(), "icon_y": self.spin_y.value(), "icon_scale": self.spin_scale.value(),
            "video_scale": self.spin_video_scale.value(), "render_mode": self.cb_render_mode.currentData() or "balanced",
            "limit_fps": self.chk_limit_fps.isChecked(), "encoder": self.cb_encoder.currentText(),
            "naming": self.naming_settings(), "formats": [list(size) for size in self.selected_formats()]
        }

    def save_profile(self):
        current_profile = self.cb_profiles.currentText()
        if not current_profile:
            return
        self.profiles[current_profile] = self.profile_settings()
        self.save_profiles_to_disk()
        self.log(f"Đã lưu mẫu '{current_profile}'")
        self.ui_status.setText(f"Đã lưu mẫu '{current_profile}' · Bao gồm tên file và tỉ lệ xuất.")

    def new_profile(self):
        text, ok = QInputDialog.getText(self, "Hồ sơ mới", "Nhập tên hồ sơ:")
        if ok and text:
            text = text.strip()
            if not text:
                return
            if text in self.profiles:
                QMessageBox.warning(self, "Lỗi", "Tên hồ sơ đã tồn tại!")
                return
            self.profiles[text] = self.profile_settings()
            self.cb_profiles.blockSignals(True)
            self.cb_profiles.addItem(text)
            self.cb_profiles.setCurrentText(text)
            self.cb_profiles.blockSignals(False)
            self.save_profiles_to_disk()
            self.log(f"Đã tạo hồ sơ '{text}'")

    def delete_profile(self):
        current_profile = self.cb_profiles.currentText()
        if not current_profile:
            return
        reply = QMessageBox.question(self, 'Xác nhận xoá', f"Bạn có chắc muốn xoá hồ sơ '{current_profile}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if current_profile in self.profiles:
                del self.profiles[current_profile]
            
            if not self.profiles:
                self.profiles["Mặc định"] = {"outro_square": None, "outro_horizontal": None, "outro_vertical": None, "icon_path": None, "icon_x": 10, "icon_y": 10, "icon_scale": 100, "video_scale": 100}
                
            self.save_profiles_to_disk()
            
            self.cb_profiles.blockSignals(True)
            self.cb_profiles.clear()
            self.cb_profiles.addItems(list(self.profiles.keys()))
            self.cb_profiles.blockSignals(False)
            self.on_profile_changed()
            self.log(f"Đã xoá hồ sơ '{current_profile}'")

    def on_profile_changed(self):
        current_profile = self.cb_profiles.currentText()
        if current_profile in self.profiles:
            data = self.profiles[current_profile]
            controls = [self.spin_x, self.spin_y, self.spin_scale, self.spin_video_scale, self.cb_render_mode,
                        self.cb_encoder, self.chk_limit_fps, self.name_template, self.number_start,
                        self.number_padding, self.chk_sq, self.chk_hz, self.chk_vt]
            for control in controls:
                control.blockSignals(True)
            self.outro_square = data.get("outro_square")
            self.outro_horizontal = data.get("outro_horizontal")
            self.outro_vertical = data.get("outro_vertical")
            self.icon_path = data.get("icon_path")
            self.spin_x.setValue(data.get("icon_x", 10))
            self.spin_y.setValue(data.get("icon_y", 10))
            self.spin_scale.setValue(data.get("icon_scale", 100))
            self.spin_video_scale.setValue(data.get("video_scale", 100))
            
            r_mode = data.get("render_mode", "balanced")
            idx = self.cb_render_mode.findData(r_mode)
            if idx >= 0:
                self.cb_render_mode.setCurrentIndex(idx)
                
            enc = data.get("encoder", "Tự động phát hiện")
            e_idx = self.cb_encoder.findText(enc)
            if e_idx >= 0:
                self.cb_encoder.setCurrentIndex(e_idx)
                
            self.chk_limit_fps.setChecked(data.get("limit_fps", False))
            
            self.lbl_icon.setText(os.path.basename(self.icon_path) if self.icon_path else "Không có Icon")
            self.lbl_icon.setStyleSheet("color: white;" if self.icon_path else "color: #AAAAAA;")
            
            self.lbl_outro_sq.setText(os.path.basename(self.outro_square) if self.outro_square else "Không có Outro")
            self.lbl_outro_sq.setStyleSheet("color: white;" if self.outro_square else "color: #AAAAAA;")
            
            self.lbl_outro_hz.setText(os.path.basename(self.outro_horizontal) if self.outro_horizontal else "Không có Outro")
            self.lbl_outro_hz.setStyleSheet("color: white;" if self.outro_horizontal else "color: #AAAAAA;")
            
            self.lbl_outro_vt.setText(os.path.basename(self.outro_vertical) if self.outro_vertical else "Không có Outro")
            self.lbl_outro_vt.setStyleSheet("color: white;" if self.outro_vertical else "color: #AAAAAA;")

            naming = data.get("naming") or {}
            self.name_template.setText(naming.get("template", DEFAULT_TEMPLATE))
            self.number_start.setValue(naming.get("start", 1))
            index = self.number_padding.findData(naming.get("padding", 3))
            self.number_padding.setCurrentIndex(index if index >= 0 else 2)
            formats = data.get("formats", [list(size) for size in FORMATS])
            for checkbox, size in zip([self.chk_sq, self.chk_hz, self.chk_vt], FORMATS):
                checkbox.setChecked(list(size) in formats)
            for control in controls:
                control.blockSignals(False)
            for source in self.input_files:
                self.video_scales[source] = self.spin_video_scale.value()
                self.icon_settings[source] = {"path": self.icon_path, "x": self.spin_x.value(),
                                              "y": self.spin_y.value(), "scale": self.spin_scale.value()}
            self.on_listbox_selection_changed()
            self.refresh_output_plan()

    def on_render_mode_changed(self):
        mode = self.cb_render_mode.currentData()
        if mode == "low_spec":
            self.chk_limit_fps.setChecked(True)
            self.log("🚀 Đã kích hoạt Chế độ Tối ưu Máy Yếu (Render siêu tốc, giảm tải CPU tối đa).")
        elif mode == "high_quality":
            self.chk_limit_fps.setChecked(False)
            self.log("💎 Đã chọn Chế độ Chất Lượng Cao (Render đầy đủ độ nét, phù hợp máy mạnh).")
        else:
            self.log("⚖️ Đã chọn Chế độ Cân Bằng (Tối ưu mượt mà và chất lượng).")
        self.on_spin_changed()

    def select_outro(self, size_type):
        file, _ = QFileDialog.getOpenFileName(self, f"Chọn Outro cho {size_type}", "", "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*.*)")
        if file:
            filename = os.path.basename(file)
            if size_type == "square":
                self.outro_square = file
                self.lbl_outro_sq.setText(filename)
                self.lbl_outro_sq.setStyleSheet("color: white; background-color: transparent;")
            elif size_type == "horizontal":
                self.outro_horizontal = file
                self.lbl_outro_hz.setText(filename)
                self.lbl_outro_hz.setStyleSheet("color: white; background-color: transparent;")
            elif size_type == "vertical":
                self.outro_vertical = file
                self.lbl_outro_vt.setText(filename)
                self.lbl_outro_vt.setStyleSheet("color: white; background-color: transparent;")

    def clear_outro(self, size_type):
        if size_type == "square":
            self.outro_square = None
            self.lbl_outro_sq.setText("Không có Outro")
            self.lbl_outro_sq.setStyleSheet("color: #AAAAAA; background-color: transparent;")
        elif size_type == "horizontal":
            self.outro_horizontal = None
            self.lbl_outro_hz.setText("Không có Outro")
            self.lbl_outro_hz.setStyleSheet("color: #AAAAAA; background-color: transparent;")
        elif size_type == "vertical":
            self.outro_vertical = None
            self.lbl_outro_vt.setText("Không có Outro")
            self.lbl_outro_vt.setStyleSheet("color: #AAAAAA; background-color: transparent;")

    def select_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file Logo/Icon", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if file_path:
            self.icon_path = file_path # for profile save
            self.lbl_icon.setText(os.path.basename(file_path))
            self.lbl_icon.setStyleSheet("color: white; background-color: transparent;")
            selected_row = self.listbox.currentRow()
            if selected_row >= 0 and selected_row < len(self.input_files):
                input_file = self.input_files[selected_row]
                if input_file in self.icon_settings:
                    self.icon_settings[input_file]["path"] = file_path
            self.on_spin_changed()

    def clear_icon(self):
        self.icon_path = None
        self.lbl_icon.setText("Chưa chọn logo")
        self.lbl_icon.setStyleSheet("color: #AAAAAA; background-color: transparent;")
        
        selected_row = self.listbox.currentRow()
        if selected_row >= 0 and selected_row < len(self.input_files):
            input_file = self.input_files[selected_row]
            if input_file in self.icon_settings:
                self.icon_settings[input_file]["path"] = None
            self.log(f"Đã xóa Icon khỏi video: {os.path.basename(input_file)}")
        else:
            for f in self.input_files:
                if f in self.icon_settings:
                    self.icon_settings[f]["path"] = None
            self.log("Đã xóa Icon.")
            
        if self.preview_dlg and self.preview_dlg.isVisible():
            self.preview_dlg.icon_path = None
            self.preview_dlg.update_icon()
        self.on_spin_changed()

    def apply_icon_all(self):
        selected_row = self.listbox.currentRow()
        if selected_row >= 0 and selected_row < len(self.input_files):
            input_file = self.input_files[selected_row]
            icon_set = self.icon_settings.get(input_file)
            if icon_set:
                for f in self.input_files:
                    self.icon_settings[f] = icon_set.copy()
                self.log("Đã áp dụng Icon hiện tại cho tất cả các video.")
                QMessageBox.information(self, "Thành công", "Đã áp dụng thông số Icon cho tất cả video!")
        else:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một video trong danh sách để lấy thông số Icon.")

    def select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Lưu Video Mới")
        if folder:
            self.output_dir = folder
            self.lbl_output.setText(folder)
            self.lbl_output.setToolTip(folder)
            self.refresh_output_plan()

    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn video", "", "Video (*.mp4 *.mov *.avi *.mkv *.webm)")
        self.add_video_paths(files)

    def clear_list(self):
        self.input_files.clear()
        self.video_scales.clear()
        self.icon_settings.clear()
        self.update_listbox()
        self.log("Đã xoá danh sách file.")

    def update_listbox(self):
        selected = self.listbox.currentRow()
        self.listbox.blockSignals(True)
        self.listbox.clear()
        for i, f in enumerate(self.input_files, 1):
            scale = self.video_scales.get(f, 100)
            self.listbox.addItem(f"{i}. {os.path.basename(f)} (Scale: {scale}%)")
        self.listbox.blockSignals(False)
        if self.input_files:
            self.listbox.setCurrentRow(max(0, min(selected, len(self.input_files) - 1)))
        else:
            self.on_listbox_selection_changed()
        self.lbl_progress.setText(f"0/{len(self.input_files)} video")
        self.refresh_output_plan()

    def start_processing(self):
        if not self.input_files:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất 1 video.")
            return
            
        do_sq = self.chk_sq.isChecked()
        do_hz = self.chk_hz.isChecked()
        do_vt = self.chk_vt.isChecked()
        
        if not do_sq and not do_hz and not do_vt:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất 1 định dạng xuất ra.")
            return

        reviewed = [row["output"] for row in self.output_plan]
        self.refresh_output_plan()
        if reviewed != [row["output"] for row in self.output_plan] and self.steps.currentIndex() == 2:
            self.ui_status.setText("Đã cập nhật tên do có file mới trong thư mục. Kiểm tra danh sách rồi nhấn Xuất lần nữa.")
            return
        if not self.output_plan:
            self.set_step(1)
            return
        for source in self.input_files:
            if not os.path.isfile(source):
                QMessageBox.warning(self, "Thiếu nguồn", f"Không tìm thấy video: {source}")
                return
        for path in [self.outro_square if do_sq else None, self.outro_horizontal if do_hz else None,
                     self.outro_vertical if do_vt else None] + [item.get("path") for item in self.icon_settings.values()]:
            if path and not os.path.isfile(path):
                QMessageBox.warning(self, "Thiếu tài nguyên", f"Không tìm thấy outro hoặc logo: {path}")
                return
        self.set_step(2)
        self.set_processing_state(True)
        self.progress_bar.setValue(0)
        self.log("Bắt đầu xử lý...")
        
        render_mode = self.cb_render_mode.currentData() or "balanced"
        encoder_choice = self.cb_encoder.currentText()
        limit_30fps = self.chk_limit_fps.isChecked()
        
        self.worker = WorkerThread(self.input_files, self.output_dir, do_sq, do_hz, do_vt,
                                   self.outro_square, self.outro_horizontal, self.outro_vertical,
                                   self.icon_settings, self.video_scales,
                                   render_mode=render_mode, selected_encoder=encoder_choice, limit_30fps=limit_30fps,
                                   output_plan=[row.copy() for row in self.output_plan])
        self.worker.output_signal.connect(self.mark_output_finished)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.finish_processing)
        self.worker.start()

    def on_spin_changed(self):
        self.request_thumbnail()
        if self.preview_dlg and self.preview_dlg.isVisible():
            self.preview_timer.start(500)

    def on_listbox_selection_changed(self):
        selected_row = self.listbox.currentRow()
        if selected_row >= 0 and selected_row < len(self.input_files):
            input_file = self.input_files[selected_row]
            scale = self.video_scales.get(input_file, 100)
            self.spin_video_scale.blockSignals(True)
            self.spin_video_scale.setValue(scale)
            self.spin_video_scale.blockSignals(False)
            
            icon_set = self.icon_settings.get(input_file, {"path": None, "x": 0, "y": 0, "scale": 100})
            self.spin_x.blockSignals(True)
            self.spin_y.blockSignals(True)
            self.spin_scale.blockSignals(True)
            
            self.spin_x.setValue(icon_set["x"])
            self.spin_y.setValue(icon_set["y"])
            self.spin_scale.setValue(icon_set["scale"])
            
            self.spin_x.blockSignals(False)
            self.spin_y.blockSignals(False)
            self.spin_scale.blockSignals(False)
            
            video_icon_path = icon_set.get("path")
            if video_icon_path and os.path.exists(video_icon_path):
                self.lbl_icon.setText(os.path.basename(video_icon_path))
                self.lbl_icon.setStyleSheet("color: white; background-color: transparent;")
                self.icon_path = video_icon_path
            else:
                self.lbl_icon.setText("Chưa chọn logo")
                self.lbl_icon.setStyleSheet("color: #AAAAAA; background-color: transparent;")
                self.icon_path = None
                
        self.selected_video.setText(os.path.basename(self.input_files[selected_row]) if 0 <= selected_row < len(self.input_files) else "Chưa có video")
        self.btn_remove.setEnabled(bool(self.listbox.selectedItems()) and not self.is_processing)
        self.btn_edit_video.setEnabled(bool(self.listbox.selectedItems()) and not self.is_processing)
        if not self.listbox.selectedItems():
            self.video_editor.close()
        self.on_spin_changed()

    def on_icon_setting_changed(self):
        selected_row = self.listbox.currentRow()
        if selected_row >= 0 and selected_row < len(self.input_files):
            input_file = self.input_files[selected_row]
            if input_file in self.icon_settings:
                self.icon_settings[input_file]["x"] = self.spin_x.value()
                self.icon_settings[input_file]["y"] = self.spin_y.value()
                self.icon_settings[input_file]["scale"] = self.spin_scale.value()
        self.on_spin_changed()

    def on_video_scale_changed(self):
        selected_row = self.listbox.currentRow()
        if selected_row >= 0 and selected_row < len(self.input_files):
            input_file = self.input_files[selected_row]
            new_scale = self.spin_video_scale.value()
            self.video_scales[input_file] = new_scale
            item = self.listbox.item(selected_row)
            if item:
                item.setText(f"{selected_row + 1}. {os.path.basename(input_file)} (Scale: {new_scale}%)")
        self.on_spin_changed()

    def copy_scale(self):
        self.copied_video_scale = self.spin_video_scale.value()
        self.log(f"Đã sao chép Scale: {self.copied_video_scale}%")
        QMessageBox.information(self, "Đã Copy", f"Đã sao chép thông số Scale: {self.copied_video_scale}%")

    def paste_scale(self):
        if self.copied_video_scale is not None:
            self.spin_video_scale.setValue(self.copied_video_scale)
            self.log(f"Đã dán Scale: {self.copied_video_scale}%")

    def copy_icon(self):
        selected_row = self.listbox.currentRow()
        if selected_row >= 0 and selected_row < len(self.input_files):
            input_file = self.input_files[selected_row]
        elif self.input_files:
            input_file = self.input_files[0]
        else:
            return
            
        self.copied_icon_settings = self.icon_settings.get(input_file, {"path": None, "x": 0, "y": 0, "scale": 100}).copy()
        self.log("Đã sao chép thông số Icon")
        QMessageBox.information(self, "Đã Copy", "Đã sao chép thông số Icon của video hiện tại.")

    def paste_icon(self):
        if self.copied_icon_settings is None:
            return
            
        selected_row = self.listbox.currentRow()
        if selected_row >= 0 and selected_row < len(self.input_files):
            input_file = self.input_files[selected_row]
        elif self.input_files:
            input_file = self.input_files[0]
        else:
            return
            
        self.icon_settings[input_file] = self.copied_icon_settings.copy()
        icon_path = self.copied_icon_settings["path"]
        self.lbl_icon.setText(os.path.basename(icon_path) if icon_path else "Chưa chọn logo")
        
        self.spin_x.blockSignals(True)
        self.spin_y.blockSignals(True)
        self.spin_scale.blockSignals(True)
        
        self.spin_x.setValue(self.copied_icon_settings["x"])
        self.spin_y.setValue(self.copied_icon_settings["y"])
        self.spin_scale.setValue(self.copied_icon_settings["scale"])
        
        self.spin_x.blockSignals(False)
        self.spin_y.blockSignals(False)
        self.spin_scale.blockSignals(False)
        
        self.log("Đã dán thông số Icon")
        self.on_spin_changed()

    def update_progress(self, current, total):
        self.progress_bar.setValue(int((current / total) * 100))
        self.lbl_progress.setText(f"{current}/{total} video")

    def generate_preview(self):
        if not self.input_files:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất 1 video để xem trước.")
            return
            
        selected_row = self.listbox.currentRow()
        if selected_row >= 0 and selected_row < len(self.input_files):
            input_file = self.input_files[selected_row]
        else:
            input_file = self.input_files[0]
            
        current_scale = self.video_scales.get(input_file, 100)
        icon_set = self.icon_settings.get(input_file, {"path": None, "x": 0, "y": 0, "scale": 100})
        temp_img = os.path.join(tempfile.gettempdir(), f"video_resizer_preview_{os.getpid()}.jpg")
        
        target_width, target_height = self.preview_ratio.currentData()
        inputs = ['-y', '-threads', '0', '-i', input_file]

        # Tối ưu hoá blur nền cho preview (render tức thì < 0.2s với Bicubic Spline)
        bg_w = max(16, (target_width // 4) & ~1)
        bg_h = max(16, (target_height // 4) & ~1)
        v_filter = (
            f"[0:v]split=2[in_bg][in_fg];"
            f"[in_bg]scale={bg_w}:{bg_h}:force_original_aspect_ratio=increase,"
            f"crop={bg_w}:{bg_h},"
            f"boxblur=luma_radius=10:luma_power=3:chroma_radius=10:chroma_power=3,"
            f"scale={target_width}:{target_height}:flags=bicubic[bg];"
            f"[in_fg]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease[fg_base];"
        )
        if current_scale != 100:
            v_filter += f"[fg_base]scale=iw*{current_scale}/100:ih*{current_scale}/100[fg];"
        else:
            v_filter += f"[fg_base]copy[fg];"
            
        v_filter += f"[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
            
        cmd = [FFMPEG_CMD] + inputs + ['-filter_complex_threads', '0', '-filter_complex', v_filter, '-map', '[outv]', '-vframes', '1', temp_img]
        
        try:
            self.log("Đang tạo ảnh xem trước...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
            QApplication.restoreOverrideCursor()
            
            if os.path.exists(temp_img):
                if self.preview_dlg is None or not self.preview_dlg.isVisible():
                    self.preview_dlg = PreviewDialog(
                        temp_img, target_width, target_height,
                        icon_set["path"], icon_set["x"], icon_set["y"], icon_set["scale"],
                        self, self
                    )
                    self.preview_dlg.show()
                else:
                    self.preview_dlg.update_image_and_icon(
                        temp_img, target_width, target_height,
                        icon_set["path"], icon_set["x"], icon_set["y"], icon_set["scale"]
                    )
        except subprocess.CalledProcessError:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Lỗi", "Không thể tạo ảnh xem trước. Video có thể bị lỗi hoặc FFmpeg gặp vấn đề.")

    def finish_processing(self, success_count, total_files, save_dir):
        self.set_processing_state(False)
        self.ui_status.setText(f"Hoàn tất · {success_count}/{total_files} video thành công. Xem nhật ký nếu có lỗi.")
        self.log(f"HOÀN TẤT: Thành công {success_count}/{total_files} video.")
        QMessageBox.information(self, "Xong", f"Quá trình xử lý hoàn tất!\nThành công {success_count}/{total_files} video.")
        if save_dir and os.path.exists(save_dir):
            try:
                norm_dir = os.path.normpath(save_dir)
                if sys.platform == 'darwin': subprocess.run(['open', norm_dir])
                elif os.name == 'nt': os.startfile(norm_dir)
                else: subprocess.run(['xdg-open', norm_dir])
            except Exception as e:
                self.log(f"Lỗi khi mở thư mục: {e}")

if __name__ == "__main__":
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    window = VideoResizerApp()
    window.show()
    sys.exit(app.exec_())
