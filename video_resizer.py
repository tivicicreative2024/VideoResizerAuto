import sys
import os
import subprocess
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QCheckBox, QPushButton, QFileDialog, QListWidget, 
                             QProgressBar, QTextEdit, QMessageBox, QFrame, QComboBox, QInputDialog, QSpinBox, QDialog)
import imageio_ffmpeg

FFMPEG_CMD = imageio_ffmpeg.get_ffmpeg_exe()
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap

class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(int, int, str)

    def __init__(self, input_files, output_dir, do_square, do_horizontal, do_vertical, 
                 outro_square, outro_horizontal, outro_vertical, icon_settings=None, video_scales=None):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.do_square = do_square
        self.do_horizontal = do_horizontal
        self.do_vertical = do_vertical
        self.outro_square = outro_square
        self.outro_horizontal = outro_horizontal
        self.outro_vertical = outro_vertical
        self.icon_settings = icon_settings if icon_settings else {}
        self.video_scales = video_scales if video_scales else {}

    def run(self):
        total_files = len(self.input_files)
        success_count = 0
        final_save_dir = self.output_dir if self.output_dir else (os.path.dirname(self.input_files[0]) if total_files > 0 else "")
        
        for idx, input_file in enumerate(self.input_files, 1):
            input_dir = os.path.dirname(input_file)
            save_dir = self.output_dir if self.output_dir else input_dir
            input_name, input_ext = os.path.splitext(os.path.basename(input_file))
            
            out_square = os.path.join(save_dir, f"{input_name}_1080x1080{input_ext}")
            out_horizontal = os.path.join(save_dir, f"{input_name}_1920x1080{input_ext}")
            out_vertical = os.path.join(save_dir, f"{input_name}_1080x1920{input_ext}")
            
            self.log_signal.emit(f"[{idx}/{total_files}] Đang xử lý: {os.path.basename(input_file)}")
            
            current_scale = self.video_scales.get(input_file, 100)
            current_icon_set = self.icon_settings.get(input_file, None)
            
            success = True
            if self.do_square:
                if not self.run_ffmpeg(input_file, 1080, 1080, out_square, self.outro_square, current_scale, current_icon_set): success = False
            if self.do_horizontal:
                if not self.run_ffmpeg(input_file, 1920, 1080, out_horizontal, self.outro_horizontal, current_scale, current_icon_set): success = False
            if self.do_vertical:
                if not self.run_ffmpeg(input_file, 1080, 1920, out_vertical, self.outro_vertical, current_scale, current_icon_set): success = False
            
            if success:
                success_count += 1
                
            self.progress_signal.emit(idx, total_files)
            
        self.finished_signal.emit(success_count, total_files, final_save_dir)

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

    def run_ffmpeg(self, input_file, target_width, target_height, output_file, outro_file=None, video_scale=100, icon_set=None):
        inputs = ['-y', '-i', input_file]
        input_idx = 1
        
        has_a_main = self.has_audio(input_file)
        
        if outro_file:
            inputs.extend(['-i', outro_file])
            outro_idx = input_idx
            input_idx += 1
            has_a_outro = self.has_audio(outro_file)
        
        if icon_set and icon_set.get("path"):
            inputs.extend(['-i', icon_set["path"]])
            icon_idx = input_idx
            input_idx += 1
            
        v_filter = (
            f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height},"
            f"boxblur=luma_radius=40:luma_power=3:chroma_radius=40:chroma_power=3[bg];"
            f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease[fg_base];"
        )
        if video_scale != 100:
            v_filter += f"[fg_base]scale=iw*{video_scale}/100:ih*{video_scale}/100[fg];"
        else:
            v_filter += f"[fg_base]copy[fg];"
            
        v_filter += f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        
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
            
        if outro_file:
            if has_a_main: main_a = "[0:a]"
            else:
                inputs.extend(['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100'])
                main_a = f"[{input_idx}:a]"; input_idx += 1
                
            if has_a_outro: outro_a = f"[{outro_idx}:a]"
            else:
                inputs.extend(['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100'])
                outro_a = f"[{input_idx}:a]"; input_idx += 1
                
            filter_complex = v_filter + f"[main_v_icon]{main_a}[outro_v]{outro_a}concat=n=2:v=1:a=1[outv][outa]"
            cmd = [FFMPEG_CMD] + inputs + ['-filter_complex', filter_complex, '-map', '[outv]', '-map', '[outa]', output_file]
        else:
            filter_complex = v_filter
            # If no outro, we don't need to concat, just map the video and audio
            cmd = [FFMPEG_CMD] + inputs + ['-filter_complex', filter_complex, '-map', '[main_v_icon]']
            if has_a_main:
                cmd.extend(['-map', '0:a?'])
            cmd.append(output_file)
            
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
            self.log_signal.emit(f"  -> Xong: {os.path.basename(output_file)}")
            return True
        except subprocess.CalledProcessError:
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
        self.setStyleSheet("background-color: #242424;")
        
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

class VideoResizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Resizer Pro")
        self.resize(750, 700)
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
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.generate_preview)

        self.profiles_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles.json")
        self.profiles = {}

        self.setup_ui()
        self.load_profiles()
        self.log("Sẵn sàng!")
        
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
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. Title
        title = QLabel("Công cụ Resize Video Hàng Loạt")
        title.setFont(QFont("Helvetica", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Common Button Style
        btn_style = """
            QPushButton {
                background-color: #2980B9;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3498DB; }
            QPushButton:disabled { background-color: #555555; color: #888888; }
        """
        btn_danger_style = btn_style.replace("#2980B9", "#C0392B").replace("#3498DB", "#E74C3C")

        # 1.5 Profiles Block
        profile_frame = QFrame()
        profile_frame.setStyleSheet("QFrame { background-color: #2B2B2B; border-radius: 8px; }")
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setContentsMargins(15, 15, 15, 15)

        lbl_profile = QLabel("Hồ sơ Outro:")
        lbl_profile.setStyleSheet("font-size: 14px; font-weight: bold;")
        profile_layout.addWidget(lbl_profile)

        self.cb_profiles = QComboBox()
        self.cb_profiles.setStyleSheet("""
            QComboBox {
                background-color: #1E1E1E;
                color: white;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
                min-width: 150px;
            }
            QComboBox::drop-down { border: none; }
        """)
        self.cb_profiles.currentIndexChanged.connect(self.on_profile_changed)
        profile_layout.addWidget(self.cb_profiles, 1)

        self.btn_save_profile = QPushButton("Lưu")
        self.btn_save_profile.setStyleSheet(btn_style)
        self.btn_save_profile.clicked.connect(self.save_profile)
        profile_layout.addWidget(self.btn_save_profile)

        self.btn_new_profile = QPushButton("Thêm Mới")
        self.btn_new_profile.setStyleSheet(btn_style)
        self.btn_new_profile.clicked.connect(self.new_profile)
        profile_layout.addWidget(self.btn_new_profile)

        self.btn_delete_profile = QPushButton("Xoá")
        self.btn_delete_profile.setStyleSheet(btn_danger_style)
        self.btn_delete_profile.clicked.connect(self.delete_profile)
        profile_layout.addWidget(self.btn_delete_profile)

        main_layout.addWidget(profile_frame)

        # 2. Options Block
        opt_frame = QFrame()
        opt_frame.setStyleSheet("QFrame { background-color: #2B2B2B; border-radius: 8px; }")
        opt_layout = QVBoxLayout(opt_frame)
        opt_layout.setContentsMargins(15, 15, 15, 15)

        # Scale video chính
        h_scale = QHBoxLayout()
        lbl_v_scale = QLabel("Scale Video Chính (%):")
        self.spin_video_scale = QSpinBox()
        self.spin_video_scale.setRange(10, 1000)
        self.spin_video_scale.setValue(100)
        self.spin_video_scale.setStyleSheet("QSpinBox { background-color: #1E1E1E; color: white; border: 1px solid #333; padding: 2px; }")
        self.spin_video_scale.valueChanged.connect(self.on_video_scale_changed)
        
        self.btn_copy_scale = QPushButton("Copy")
        self.btn_copy_scale.setStyleSheet(btn_style)
        self.btn_copy_scale.clicked.connect(self.copy_scale)
        
        self.btn_paste_scale = QPushButton("Paste")
        self.btn_paste_scale.setStyleSheet(btn_style)
        self.btn_paste_scale.clicked.connect(self.paste_scale)
        
        h_scale.addWidget(lbl_v_scale)
        h_scale.addWidget(self.spin_video_scale)
        h_scale.addWidget(self.btn_copy_scale)
        h_scale.addWidget(self.btn_paste_scale)
        h_scale.addStretch()
        opt_layout.addLayout(h_scale)

        chk_style = """
            QCheckBox { font-size: 14px; background-color: transparent; }
            QCheckBox::indicator { width: 20px; height: 20px; }
        """

        # Vuông
        h_sq = QHBoxLayout()
        self.chk_sq = QCheckBox("Video Vuông (1080x1080)")
        self.chk_sq.setStyleSheet(chk_style)
        self.chk_sq.setChecked(True)
        self.chk_sq.setFixedWidth(220)
        h_sq.addWidget(self.chk_sq)
        
        self.btn_outro_sq = QPushButton("Chọn Outro")
        self.btn_outro_sq.setStyleSheet(btn_style)
        self.btn_outro_sq.clicked.connect(lambda: self.select_outro("square"))
        h_sq.addWidget(self.btn_outro_sq)

        self.btn_del_outro_sq = QPushButton("Xóa")
        self.btn_del_outro_sq.setStyleSheet(btn_danger_style)
        self.btn_del_outro_sq.clicked.connect(lambda: self.clear_outro("square"))
        h_sq.addWidget(self.btn_del_outro_sq)
        
        self.lbl_outro_sq = QLabel("Không có Outro")
        self.lbl_outro_sq.setStyleSheet("color: #AAAAAA; background-color: transparent;")
        h_sq.addWidget(self.lbl_outro_sq, 1)
        opt_layout.addLayout(h_sq)

        # Ngang
        h_hz = QHBoxLayout()
        self.chk_hz = QCheckBox("Video Ngang (1920x1080)")
        self.chk_hz.setStyleSheet(chk_style)
        self.chk_hz.setChecked(True)
        self.chk_hz.setFixedWidth(220)
        h_hz.addWidget(self.chk_hz)
        
        self.btn_outro_hz = QPushButton("Chọn Outro")
        self.btn_outro_hz.setStyleSheet(btn_style)
        self.btn_outro_hz.clicked.connect(lambda: self.select_outro("horizontal"))
        h_hz.addWidget(self.btn_outro_hz)

        self.btn_del_outro_hz = QPushButton("Xóa")
        self.btn_del_outro_hz.setStyleSheet(btn_danger_style)
        self.btn_del_outro_hz.clicked.connect(lambda: self.clear_outro("horizontal"))
        h_hz.addWidget(self.btn_del_outro_hz)
        
        self.lbl_outro_hz = QLabel("Không có Outro")
        self.lbl_outro_hz.setStyleSheet("color: #AAAAAA; background-color: transparent;")
        h_hz.addWidget(self.lbl_outro_hz, 1)
        opt_layout.addLayout(h_hz)

        # Dọc
        h_vt = QHBoxLayout()
        self.chk_vt = QCheckBox("Video Dọc (1080x1920)")
        self.chk_vt.setStyleSheet(chk_style)
        self.chk_vt.setChecked(True)
        self.chk_vt.setFixedWidth(220)
        h_vt.addWidget(self.chk_vt)
        
        self.btn_outro_vt = QPushButton("Chọn Outro")
        self.btn_outro_vt.setStyleSheet(btn_style)
        self.btn_outro_vt.clicked.connect(lambda: self.select_outro("vertical"))
        h_vt.addWidget(self.btn_outro_vt)

        self.btn_del_outro_vt = QPushButton("Xóa")
        self.btn_del_outro_vt.setStyleSheet(btn_danger_style)
        self.btn_del_outro_vt.clicked.connect(lambda: self.clear_outro("vertical"))
        h_vt.addWidget(self.btn_del_outro_vt)
        
        self.lbl_outro_vt = QLabel("Không có Outro")
        self.lbl_outro_vt.setStyleSheet("color: #AAAAAA; background-color: transparent;")
        h_vt.addWidget(self.lbl_outro_vt, 1)
        opt_layout.addLayout(h_vt)

        main_layout.addWidget(opt_frame)

        # 2.5 Icon/Watermark Block
        icon_frame = QFrame()
        icon_frame.setStyleSheet("QFrame { background-color: #2B2B2B; border-radius: 8px; }")
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(15, 15, 15, 15)
        
        h_icon = QHBoxLayout()
        self.btn_icon = QPushButton("Chọn Logo/Icon")
        self.btn_icon.setStyleSheet(btn_style)
        self.btn_icon.clicked.connect(self.select_icon)
        
        self.btn_apply_icon_all = QPushButton("Áp dụng Icon cho tất cả")
        self.btn_apply_icon_all.setStyleSheet(btn_style)
        self.btn_apply_icon_all.clicked.connect(self.apply_icon_all)
        
        self.lbl_icon = QLabel("Chưa chọn logo")
        self.lbl_icon.setStyleSheet("color: #AAA;")
        
        h_icon.addWidget(self.btn_icon)
        h_icon.addWidget(self.lbl_icon)
        h_icon.addWidget(self.btn_apply_icon_all)
        h_icon.addStretch()
        icon_layout.addLayout(h_icon)

        h_pos = QHBoxLayout()
        lbl_x = QLabel("X:")
        self.spin_x = QSpinBox()
        self.spin_x.setRange(0, 4000)
        self.spin_x.setStyleSheet("QSpinBox { background-color: #1E1E1E; color: white; border: 1px solid #333; padding: 2px; }")
        self.spin_x.valueChanged.connect(self.on_icon_setting_changed)
        
        lbl_y = QLabel("Y:")
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 4000)
        self.spin_y.setStyleSheet("QSpinBox { background-color: #1E1E1E; color: white; border: 1px solid #333; padding: 2px; }")
        self.spin_y.valueChanged.connect(self.on_icon_setting_changed)
        
        lbl_scale = QLabel("Scale (%):")
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(10, 500)
        self.spin_scale.setValue(100)
        self.spin_scale.setStyleSheet("QSpinBox { background-color: #1E1E1E; color: white; border: 1px solid #333; padding: 2px; }")
        self.spin_scale.valueChanged.connect(self.on_icon_setting_changed)
        
        h_pos.addWidget(lbl_x)
        h_pos.addWidget(self.spin_x)
        h_pos.addWidget(lbl_y)
        h_pos.addWidget(self.spin_y)
        h_pos.addWidget(lbl_scale)
        h_pos.addWidget(self.spin_scale)
        
        self.btn_copy_icon = QPushButton("Copy")
        self.btn_copy_icon.setStyleSheet(btn_style)
        self.btn_copy_icon.clicked.connect(self.copy_icon)
        
        self.btn_paste_icon = QPushButton("Paste")
        self.btn_paste_icon.setStyleSheet(btn_style)
        self.btn_paste_icon.clicked.connect(self.paste_icon)
        
        h_pos.addWidget(self.btn_copy_icon)
        h_pos.addWidget(self.btn_paste_icon)
        
        h_pos.addStretch()
        icon_layout.addLayout(h_pos)
        
        self.btn_preview = QPushButton("Xem Trước (Preview)")
        self.btn_preview.setStyleSheet(btn_style)
        self.btn_preview.clicked.connect(self.generate_preview)
        icon_layout.addWidget(self.btn_preview)
        
        main_layout.addWidget(icon_frame)
        
        # 3. Output Dir
        h_out = QHBoxLayout()
        self.btn_output = QPushButton("Chọn Thư Mục Lưu")
        self.btn_output.setStyleSheet(btn_style)
        self.btn_output.clicked.connect(self.select_output_dir)
        h_out.addWidget(self.btn_output)
        
        self.lbl_output = QLabel("Lưu cùng thư mục gốc (Mặc định)")
        self.lbl_output.setStyleSheet("font-size: 14px; color: white;")
        h_out.addWidget(self.lbl_output, 1)
        main_layout.addLayout(h_out)

        # 4. Add/Clear Buttons
        h_btns = QHBoxLayout()
        self.btn_add = QPushButton("Thêm Video")
        self.btn_add.setStyleSheet(btn_style)
        self.btn_add.clicked.connect(self.add_videos)
        h_btns.addWidget(self.btn_add)
        
        self.btn_clear = QPushButton("Xoá Danh Sách")
        self.btn_clear.setStyleSheet(btn_danger_style)
        self.btn_clear.clicked.connect(self.clear_list)
        h_btns.addWidget(self.btn_clear)
        h_btns.addStretch()
        main_layout.addLayout(h_btns)

        # 5. Listbox
        self.listbox = QListWidget()
        self.listbox.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                color: white;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.listbox.itemSelectionChanged.connect(self.on_listbox_selection_changed)
        main_layout.addWidget(self.listbox)

        # 6. Progress
        h_prog = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 5px;
                text-align: center;
                background-color: #1E1E1E;
            }
            QProgressBar::chunk {
                background-color: #2980B9;
            }
        """)
        self.progress_bar.setValue(0)
        h_prog.addWidget(self.progress_bar)
        
        self.lbl_progress = QLabel("0/0")
        self.lbl_progress.setStyleSheet("font-weight: bold; font-size: 14px;")
        h_prog.addWidget(self.lbl_progress)
        
        self.btn_start = QPushButton("BẮT ĐẦU XỬ LÝ")
        self.btn_start.setStyleSheet(btn_style)
        self.btn_start.clicked.connect(self.start_processing)
        h_prog.addWidget(self.btn_start)
        main_layout.addLayout(h_prog)

        # 7. Log Console
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #A5D6A7;
                border: 1px solid #333;
                border-radius: 5px;
                font-family: Consolas, Monaco, monospace;
                font-size: 13px;
                padding: 5px;
            }
        """)
        main_layout.addWidget(self.log_box)

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

    def save_profile(self):
        current_profile = self.cb_profiles.currentText()
        if not current_profile:
            return
        self.profiles[current_profile] = {
            "outro_square": self.outro_square,
            "outro_horizontal": self.outro_horizontal,
            "outro_vertical": self.outro_vertical,
            "icon_path": self.icon_path,
            "icon_x": self.spin_x.value(),
            "icon_y": self.spin_y.value(),
            "icon_scale": self.spin_scale.value(),
            "video_scale": self.spin_video_scale.value()
        }
        self.save_profiles_to_disk()
        self.log(f"Đã lưu hồ sơ '{current_profile}'")
        QMessageBox.information(self, "Thành công", f"Đã lưu hồ sơ '{current_profile}'")

    def new_profile(self):
        text, ok = QInputDialog.getText(self, "Hồ sơ mới", "Nhập tên hồ sơ:")
        if ok and text:
            text = text.strip()
            if not text:
                return
            if text in self.profiles:
                QMessageBox.warning(self, "Lỗi", "Tên hồ sơ đã tồn tại!")
                return
            self.profiles[text] = {
                "outro_square": self.outro_square,
                "outro_horizontal": self.outro_horizontal,
                "outro_vertical": self.outro_vertical
            }
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
            self.outro_square = data.get("outro_square")
            self.outro_horizontal = data.get("outro_horizontal")
            self.outro_vertical = data.get("outro_vertical")
            self.icon_path = data.get("icon_path")
            self.spin_x.setValue(data.get("icon_x", 10))
            self.spin_y.setValue(data.get("icon_y", 10))
            self.spin_scale.setValue(data.get("icon_scale", 100))
            self.spin_video_scale.setValue(data.get("video_scale", 100))
            
            self.lbl_icon.setText(os.path.basename(self.icon_path) if self.icon_path else "Không có Icon")
            self.lbl_icon.setStyleSheet("color: white;" if self.icon_path else "color: #AAAAAA;")
            
            self.lbl_outro_sq.setText(os.path.basename(self.outro_square) if self.outro_square else "Không có Outro")
            self.lbl_outro_sq.setStyleSheet("color: white;" if self.outro_square else "color: #AAAAAA;")
            
            self.lbl_outro_hz.setText(os.path.basename(self.outro_horizontal) if self.outro_horizontal else "Không có Outro")
            self.lbl_outro_hz.setStyleSheet("color: white;" if self.outro_horizontal else "color: #AAAAAA;")
            
            self.lbl_outro_vt.setText(os.path.basename(self.outro_vertical) if self.outro_vertical else "Không có Outro")
            self.lbl_outro_vt.setStyleSheet("color: white;" if self.outro_vertical else "color: #AAAAAA;")

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
            selected_row = self.listbox.currentRow()
            if selected_row >= 0 and selected_row < len(self.input_files):
                input_file = self.input_files[selected_row]
                if input_file in self.icon_settings:
                    self.icon_settings[input_file]["path"] = file_path
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

    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn Các Video", "", "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*.*)")
        if files:
            count = 0
            for f in files:
                if f not in self.input_files:
                    self.input_files.append(f)
                    self.video_scales[f] = 100
                    self.icon_settings[f] = {"path": None, "x": 0, "y": 0, "scale": 100}
                    count += 1
            self.update_listbox()
            if count > 0:
                self.log(f"Đã thêm {count} file.")

    def clear_list(self):
        self.input_files.clear()
        self.video_scales.clear()
        self.icon_settings.clear()
        self.update_listbox()
        self.log("Đã xoá danh sách file.")

    def update_listbox(self):
        self.listbox.clear()
        for i, f in enumerate(self.input_files, 1):
            scale = self.video_scales.get(f, 100)
            self.listbox.addItem(f"{i}. {os.path.basename(f)} (Scale: {scale}%)")
        self.lbl_progress.setText(f"0/{len(self.input_files)}")

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

        self.btn_start.setEnabled(False)
        self.btn_add.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.chk_sq.setEnabled(False)
        self.chk_hz.setEnabled(False)
        self.chk_vt.setEnabled(False)
        self.btn_output.setEnabled(False)
        self.btn_outro_sq.setEnabled(False)
        self.btn_outro_hz.setEnabled(False)
        self.btn_outro_vt.setEnabled(False)
        self.btn_del_outro_sq.setEnabled(False)
        self.btn_del_outro_hz.setEnabled(False)
        self.btn_del_outro_vt.setEnabled(False)
        self.btn_icon.setEnabled(False)
        self.btn_apply_icon_all.setEnabled(False)
        self.btn_preview.setEnabled(False)
        self.spin_x.setEnabled(False)
        self.spin_y.setEnabled(False)
        self.spin_scale.setEnabled(False)
        self.spin_video_scale.setEnabled(False)
        self.btn_copy_scale.setEnabled(False)
        self.btn_paste_scale.setEnabled(False)
        self.btn_copy_icon.setEnabled(False)
        self.btn_paste_icon.setEnabled(False)
        self.cb_profiles.setEnabled(False)
        self.btn_save_profile.setEnabled(False)
        self.btn_new_profile.setEnabled(False)
        self.btn_delete_profile.setEnabled(False)
        
        self.progress_bar.setValue(0)
        self.log("Bắt đầu xử lý...")
        
        self.worker = WorkerThread(self.input_files, self.output_dir, do_sq, do_hz, do_vt,
                                   self.outro_square, self.outro_horizontal, self.outro_vertical,
                                   self.icon_settings, self.video_scales)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.finish_processing)
        self.worker.start()

    def on_spin_changed(self):
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
            
            if self.icon_path:
                self.lbl_icon.setText(os.path.basename(self.icon_path))
                # Apply loaded profile to the selected video if any
                if selected_row >= 0 and selected_row < len(self.input_files):
                    input_file = self.input_files[selected_row]
                    if input_file in self.icon_settings:
                        self.icon_settings[input_file]["path"] = self.icon_path
                        self.icon_settings[input_file]["x"] = self.spin_x.value()
                        self.icon_settings[input_file]["y"] = self.spin_y.value()
                        self.icon_settings[input_file]["scale"] = self.spin_scale.value()
            else:
                self.lbl_icon.setText("Chưa chọn logo")
                
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
        self.lbl_progress.setText(f"{current}/{total}")

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
        temp_img = os.path.join(os.path.dirname(input_file), "preview_temp.jpg")
        
        # Decide format for preview based on checked boxes. Priority: Square -> Horizontal -> Vertical
        target_width, target_height = 1080, 1080
        if self.chk_hz.isChecked() and not self.chk_sq.isChecked():
            target_width, target_height = 1920, 1080
        elif self.chk_vt.isChecked() and not self.chk_sq.isChecked() and not self.chk_hz.isChecked():
            target_width, target_height = 1080, 1920
            
        inputs = ['-y', '-ss', '00:00:02', '-i', input_file]
        
        v_filter = (
            f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height},"
            f"boxblur=luma_radius=40:luma_power=3:chroma_radius=40:chroma_power=3[bg];"
            f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease[fg_base];"
        )
        if current_scale != 100:
            v_filter += f"[fg_base]scale=iw*{current_scale}/100:ih*{current_scale}/100[fg];"
        else:
            v_filter += f"[fg_base]copy[fg];"
            
        v_filter += f"[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
            
        cmd = [FFMPEG_CMD] + inputs + ['-filter_complex', v_filter, '-map', '[outv]', '-vframes', '1', temp_img]
        
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
        self.btn_start.setEnabled(True)
        self.btn_add.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.chk_sq.setEnabled(True)
        self.chk_hz.setEnabled(True)
        self.chk_vt.setEnabled(True)
        self.btn_output.setEnabled(True)
        self.btn_outro_sq.setEnabled(True)
        self.btn_outro_hz.setEnabled(True)
        self.btn_outro_vt.setEnabled(True)
        self.btn_del_outro_sq.setEnabled(True)
        self.btn_del_outro_hz.setEnabled(True)
        self.btn_del_outro_vt.setEnabled(True)
        self.btn_icon.setEnabled(True)
        self.btn_preview.setEnabled(True)
        self.spin_x.setEnabled(True)
        self.spin_y.setEnabled(True)
        self.spin_scale.setEnabled(True)
        self.spin_video_scale.setEnabled(True)
        self.btn_copy_scale.setEnabled(True)
        self.btn_paste_scale.setEnabled(True)
        self.btn_copy_icon.setEnabled(True)
        self.btn_paste_icon.setEnabled(True)
        self.cb_profiles.setEnabled(True)
        self.btn_save_profile.setEnabled(True)
        self.btn_new_profile.setEnabled(True)
        self.btn_delete_profile.setEnabled(True)
        
        self.log(f"HOÀN TẤT: Thành công {success_count}/{total_files} video.")
        QMessageBox.information(self, "Xong", f"Quá trình xử lý hoàn tất!\nThành công {success_count}/{total_files} video.")
        if save_dir and os.path.exists(save_dir):
            try:
                if sys.platform == 'darwin': subprocess.run(['open', save_dir])
                elif os.name == 'nt': os.startfile(save_dir)
                else: subprocess.run(['xdg-open', save_dir])
            except Exception as e:
                self.log(f"Lỗi khi mở thư mục: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoResizerApp()
    window.show()
    sys.exit(app.exec_())
