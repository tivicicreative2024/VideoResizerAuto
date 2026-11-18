from pathlib import Path
import os
import subprocess
import sys

from PyQt5.QtCore import Qt, QSize, QThread
from PyQt5.QtGui import QFont, QFontDatabase, QIcon
from PyQt5.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QStackedWidget, QListWidget, QAbstractItemView, QCheckBox,
    QComboBox, QSpinBox, QLineEdit, QTableWidget, QHeaderView, QProgressBar, QTextEdit, QApplication, QDialog, QMenu)

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets'
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}


class VideoList(QListWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setMinimumHeight(165)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self.window.is_processing:
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        if not self.window.is_processing:
            self.window.add_video_paths([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
            event.acceptProposedAction()


class ThumbnailWorker(QThread):
    def __init__(self, ffmpeg, source, size, scale, icon, mode, parent):
        super().__init__(parent)
        self.ffmpeg, self.source, self.size = ffmpeg, source, size
        self.scale, self.icon, self.mode = scale, icon, mode
        self.data = b''
        self.error = ''

    def run(self):
        width, height = self.size
        divisor = 4 if self.mode == 'low_spec' else 1 if self.mode == 'high_quality' else 3
        radius = 10 if divisor == 4 else 40 if divisor == 1 else 13
        bw, bh = (width // divisor) & ~1, (height // divisor) & ~1
        filters = (f'[0:v]split=2[a][b];[a]scale={bw}:{bh}:force_original_aspect_ratio=increase,'
                   f'crop={bw}:{bh},boxblur={radius}:3,scale={width}:{height}:flags=bicubic[bg];'
                   f'[b]scale={width}:{height}:force_original_aspect_ratio=decrease,'
                   f'scale=iw*{self.scale}/100:ih*{self.scale}/100[fg];'
                   '[bg][fg]overlay=(W-w)/2:(H-h)/2[base]')
        inputs = ['-i', self.source]
        if self.icon.get('path'):
            inputs += ['-i', self.icon['path']]
            filters += (f";[1:v]scale=iw*{self.icon['scale']}/100:ih*{self.icon['scale']}/100[logo];"
                        f"[base][logo]overlay={self.icon['x']}:{self.icon['y']}[result]")
            output = '[result]'
        else:
            output = '[base]'
        try:
            result = subprocess.run([self.ffmpeg, '-v', 'error'] + inputs + [
                '-filter_complex_threads', '1', '-filter_complex', filters, '-map', output,
                '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                capture_output=True, timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if result.returncode or not result.stdout:
                self.error = 'Không đọc được khung hình. Kiểm tra video và logo.'
            else:
                self.data = result.stdout
        except (OSError, subprocess.TimeoutExpired) as error:
            self.error = str(error)


def build_ui(w, encoders):
    for font in ASSETS.glob('*.ttf'):
        QFontDatabase.addApplicationFont(str(font))
    w.setFont(QFont('Be Vietnam Pro', 9))
    w.setWindowIcon(QIcon(str(ASSETS / 'brand.png')))
    w.resize(1180, 800)
    w.setMinimumSize(1040, 700)
    w.setStyleSheet('')
    QApplication.instance().setStyleSheet((ASSETS.parent / 'ui_theme.qss').read_text(encoding='utf-8-sig').replace('@ASSETS@', ASSETS.as_posix()))
    root = QWidget()
    root.setObjectName('appRoot')
    w.setCentralWidget(root)
    main = QVBoxLayout(root)
    main.setContentsMargins(0, 0, 0, 0)
    main.setSpacing(0)

    def text(value, role='caption'):
        label = QLabel(value)
        label.setProperty('role', role)
        label.setWordWrap(True)
        return label

    def button(name, label, handler, kind='secondary', icon=None):
        btn = QPushButton(label)
        btn.setProperty('kind', kind)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(34)
        if icon:
            btn.setIcon(QIcon(str(ASSETS / icon)))
            btn.setIconSize(QSize(16, 16))
        btn.clicked.connect(handler)
        setattr(w, name, btn)
        return btn

    def card(layout, title, subtitle=None):
        frame = QFrame()
        frame.setObjectName('card')
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(12)
        inner.addWidget(text(title, 'section'))
        if subtitle:
            inner.addWidget(text(subtitle))
        layout.addWidget(frame)
        return inner

    def disclosure(layout, name, title):
        toggle = QPushButton('▸  ' + title)
        toggle.setProperty('kind', 'disclosure')
        toggle.setCheckable(True)
        toggle.setCursor(Qt.PointingHandCursor)
        toggle.setMinimumHeight(36)
        content = QWidget()
        inner = QVBoxLayout(content)
        inner.setContentsMargins(0, 8, 0, 8)
        inner.setSpacing(12)
        content.hide()
        toggle.toggled.connect(content.setVisible)
        toggle.toggled.connect(lambda opened: toggle.setText(('▾  ' if opened else '▸  ') + title))
        setattr(w, name + '_options', content)
        setattr(w, 'btn_' + name, toggle)
        layout.addWidget(toggle)
        layout.addWidget(content)
        return inner

    def scroll(content):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(content)
        return area

    header = QFrame()
    header.setObjectName('header')
    h = QHBoxLayout(header)
    h.setContentsMargins(24, 10, 24, 10)
    logo = QLabel()
    logo.setPixmap(QIcon(str(ASSETS / 'brand.png')).pixmap(28, 28))
    h.addWidget(logo)
    brand = QVBoxLayout()
    brand.setSpacing(2)
    brand.addWidget(text('Video Resizer', 'brand'))
    tagline = text('Resize video hàng loạt')
    tagline.setWordWrap(False)
    brand.addWidget(tagline)
    h.addLayout(brand, 1)
    h.addStretch()
    w.cb_profiles = QComboBox()
    w.cb_profiles.setMinimumWidth(160)
    w.cb_profiles.currentIndexChanged.connect(w.on_profile_changed)
    h.addWidget(w.cb_profiles)
    h.addWidget(button('btn_save_profile', 'Lưu mẫu', w.save_profile))
    w.btn_profile_menu = QPushButton('Mẫu khác')
    menu = QMenu(w.btn_profile_menu)
    w.btn_new_profile = menu.addAction('Lưu thành mẫu mới…', w.new_profile)
    w.btn_delete_profile = menu.addAction('Xóa mẫu đang chọn…', w.delete_profile)
    w.btn_profile_menu.setMenu(menu)
    h.addWidget(w.btn_profile_menu)
    main.addWidget(header)
    nav = QHBoxLayout()
    nav.setContentsMargins(24, 6, 24, 4)
    nav.setSpacing(12)
    w.step_buttons = []
    for i, (title, subtitle) in enumerate([('Nguồn video', 'Nhập & quản lý nguồn'),
                                          ('Thiết lập xuất', 'Tỉ lệ, hiệu năng & tên file'),
                                          ('Kiểm tra đầu ra', 'Xem lại trước khi xuất')]):
        btn = QPushButton(f'{i+1}   {title}')
        btn.setProperty('kind', 'step')
        btn.setCheckable(True)
        btn.setMinimumHeight(38)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked=False, step=i: w.set_step(step))
        nav.addWidget(btn, 1)
        w.step_buttons.append(btn)
    main.addLayout(nav)
    w.step_guidance = text('', 'guidance')
    main.addWidget(w.step_guidance)
    body = QHBoxLayout()
    body.setSpacing(0)
    w.steps = QStackedWidget()
    body.addWidget(w.steps, 1)
    pages = []
    for i in range(3):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        pages.append(layout)
        w.steps.addWidget(scroll(page))

    sources = card(pages[0], '1  Nguồn video', 'Kéo video vào danh sách bên dưới hoặc chọn file từ máy tính.')
    sources.addWidget(button('btn_add', 'Kéo thả video vào danh sách  ·  Chọn video…', w.add_videos, icon='upload.svg'))
    w.listbox = VideoList(w)
    w.listbox.itemSelectionChanged.connect(w.on_listbox_selection_changed)
    sources.addWidget(w.listbox)
    source_actions = QHBoxLayout()
    source_actions.addWidget(button('btn_edit_video', 'Chỉnh video…', w.open_video_editor))
    source_actions.addWidget(button('btn_remove', 'Xóa mục chọn', w.remove_selected_video, 'danger'))
    source_actions.addWidget(button('btn_clear', 'Xóa danh sách', w.clear_list, 'danger'))
    source_actions.addStretch()
    w.source_count = text('0 video', 'micro')
    source_actions.addWidget(w.source_count)
    sources.addLayout(source_actions)
    sources.addWidget(text('Chọn một video để chỉnh tỉ lệ phóng và logo riêng. File gốc luôn được giữ nguyên.'))
    outros = disclosure(pages[0], 'outro', 'Thêm outro (tùy chọn)')
    for key, label, tag in [('square', 'Vuông 1:1', 'sq'), ('horizontal', 'Ngang 16:9', 'hz'), ('vertical', 'Dọc 9:16', 'vt')]:
        row = QHBoxLayout()
        row.addWidget(text(label, 'strong'))
        name = text('Không có Outro')
        name.setMinimumWidth(80)
        setattr(w, 'lbl_outro_' + tag, name)
        row.addWidget(name, 1)
        row.addWidget(button('btn_outro_' + tag, 'Chọn…', lambda checked=False, k=key: w.select_outro(k), icon='file-video.svg'))
        row.addWidget(button('btn_del_outro_' + tag, 'Xóa', lambda checked=False, k=key: w.clear_outro(k), 'danger'))
        outros.addLayout(row)
    pages[0].addStretch()

    formats = card(pages[1], 'Tỉ lệ xuất')
    ratio_row = QHBoxLayout()
    for name, label in [('chk_vt', 'Dọc 9:16\n1080 × 1920'),
                        ('chk_hz', 'Ngang 16:9\n1920 × 1080'),
                        ('chk_sq', 'Vuông 1:1\n1080 × 1080')]:
        checkbox = QCheckBox(label)
        checkbox.setProperty('kind', 'format')
        checkbox.setChecked(True)
        checkbox.setMinimumHeight(60)
        checkbox.toggled.connect(w.refresh_output_plan)
        setattr(w, name, checkbox)
        ratio_row.addWidget(checkbox, 1)
    formats.addLayout(ratio_row)
    naming = card(pages[1], 'Tên file đầu ra')
    field = QHBoxLayout()
    w.name_template = QLineEdit('%F_%S')
    w.name_template.setPlaceholderText('Ví dụ: Team_CuongNM_%N_%S')
    w.name_template.setToolTip('Đuôi file giữ theo video nguồn. %F: tên gốc; %N: số thứ tự; %S: tỉ lệ; %D: ngày YYYYMMDD; %%: dấu %.')
    w.name_template.textChanged.connect(w.refresh_output_plan)
    field.addWidget(w.name_template, 1)
    insert_token = QPushButton('Chèn mã')
    tokens = QMenu(insert_token)
    for token, label in [('%F', 'Tên gốc'), ('%N', 'Số thứ tự'), ('%S', 'Tỉ lệ'), ('%D', 'Ngày')]:
        tokens.addAction(label + '  ' + token, lambda checked=False, t=token: w.name_template.insert(t))
    insert_token.setMenu(tokens)
    field.addWidget(insert_token)
    naming.addLayout(field)
    w.numbering_options = QWidget()
    numbering = QGridLayout(w.numbering_options)
    numbering.setContentsMargins(0, 0, 0, 0)
    numbering.addWidget(text('Bắt đầu từ'), 0, 0)
    numbering.addWidget(text('Định dạng số'), 0, 1)
    w.number_start = QSpinBox()
    w.number_start.setRange(1, 999999999)
    w.number_start.valueChanged.connect(w.refresh_output_plan)
    w.number_padding = QComboBox()
    for digits in range(1, 7):
        w.number_padding.addItem(f"{str(1).zfill(digits)}, {str(2).zfill(digits)}, {str(3).zfill(digits)}…", digits)
    w.number_padding.setCurrentIndex(2)
    w.number_padding.currentIndexChanged.connect(w.refresh_output_plan)
    numbering.addWidget(w.number_start, 1, 0)
    numbering.addWidget(w.number_padding, 1, 1)
    naming.addWidget(w.numbering_options)
    w.naming_error = text('', 'error')
    naming.addWidget(w.naming_error)
    w.name_preview = QTextEdit()
    w.name_preview.setObjectName('namePreview')
    w.name_preview.setReadOnly(True)
    w.name_preview.setFixedHeight(76)
    naming.addWidget(w.name_preview)
    naming.addWidget(text('Tên trùng tự thêm hậu tố · File gốc được giữ nguyên.', 'micro'))
    perf = disclosure(pages[1], 'performance', 'Hiệu năng & mã hóa (nâng cao)')
    perf.addWidget(text('Chế độ xử lý', 'strong'))
    w.cb_render_mode = QComboBox()
    for label, value in [('Máy yếu · Ưu tiên tốc độ', 'low_spec'), ('Cân bằng · Khuyên dùng', 'balanced'), ('Chất lượng cao', 'high_quality')]:
        w.cb_render_mode.addItem(label, value)
    w.cb_render_mode.setCurrentIndex(1)
    w.cb_render_mode.currentIndexChanged.connect(w.on_render_mode_changed)
    perf.addWidget(w.cb_render_mode)
    perf.addWidget(text('Bộ mã hóa', 'strong'))
    w.cb_encoder = QComboBox()
    w.cb_encoder.addItem('Tự động phát hiện', 'Auto')
    # Cached by the application; the UI does not run another GPU probe.
    for encoder in encoders:
        w.cb_encoder.addItem(encoder)
    perf.addWidget(w.cb_encoder)
    w.chk_limit_fps = QCheckBox('Giới hạn 30 FPS · Giảm tải khi nguồn là 60 FPS')
    perf.addWidget(w.chk_limit_fps)
    pages[1].addStretch()

    review = card(pages[2], '3  Kiểm tra đầu ra', 'Tên và đường dẫn dưới đây là kế hoạch sẽ dùng khi xuất.')
    w.output_table = QTableWidget(0, 4)
    w.output_table.setHorizontalHeaderLabels(['Nguồn', 'Tên file đầu ra', 'Tỉ lệ', 'Trạng thái'])
    w.output_table.verticalHeader().hide()
    w.output_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    w.output_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    w.output_table.setAlternatingRowColors(True)
    w.output_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
    w.output_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    w.output_table.setColumnWidth(0, 145)
    w.output_table.setColumnWidth(2, 65)
    w.output_table.setColumnWidth(3, 115)
    w.output_table.setMinimumHeight(235)
    w.output_table.cellClicked.connect(w.select_output_preview)
    review.addWidget(w.output_table)
    w.review_error = text('', 'error')
    review.addWidget(w.review_error)
    logs = card(pages[2], 'Tiến độ xử lý')
    progress = QHBoxLayout()
    w.progress_bar = QProgressBar()
    w.progress_bar.setValue(0)
    w.lbl_progress = text('0/0', 'micro')
    progress.addWidget(w.progress_bar, 1)
    progress.addWidget(w.lbl_progress)
    logs.addLayout(progress)
    w.log_box = QTextEdit()
    w.log_box.setReadOnly(True)
    w.log_box.setObjectName('log')
    w.log_box.setMinimumHeight(115)
    logs.addWidget(w.log_box)
    pages[2].addStretch()

    sidebar = QWidget()
    sidebar.setObjectName('sidebar')
    side = QVBoxLayout(sidebar)
    side.setContentsMargins(20, 20, 20, 24)
    side.setSpacing(14)
    side.addWidget(text('Xem trước', 'section'))
    w.preview_ratio = QComboBox()
    for label, size in [('Dọc · 9:16', (1080, 1920)), ('Ngang · 16:9', (1920, 1080)), ('Vuông · 1:1', (1080, 1080))]:
        w.preview_ratio.addItem(label, size)
    w.preview_ratio.currentIndexChanged.connect(w.request_thumbnail)
    side.addWidget(w.preview_ratio)
    w.thumbnail = QLabel('Chọn video để xem trước\n\nKhung hình & logo')
    w.thumbnail.setObjectName('thumbnail')
    w.thumbnail.setAlignment(Qt.AlignCenter)
    w.thumbnail.setMinimumHeight(240)
    w.thumbnail.setFixedHeight(240)
    side.addWidget(w.thumbnail)
    w.preview_caption = text('1080 × 1920 · Xem trước độc lập với tỉ lệ xuất', 'micro')
    side.addWidget(w.preview_caption)
    side.addWidget(button('btn_preview', 'Mở lớn', w.generate_preview, icon='film.svg'))
    w.video_editor = QDialog(w)
    w.video_editor.setObjectName('videoEditor')
    w.video_editor.setWindowTitle('Chỉnh video · Phóng & logo')
    w.video_editor.resize(500, 610)
    w.video_editor.setMinimumSize(460, 560)
    editor = QVBoxLayout(w.video_editor)
    editor.setContentsMargins(24, 24, 24, 24)
    editor.setSpacing(20)
    scale = card(editor, 'Video đang chọn')
    w.selected_video = text('Chưa có video', 'micro')
    scale.addWidget(w.selected_video)
    scale.addWidget(text('Phóng video chính (%)'))
    w.spin_video_scale = QSpinBox()
    w.spin_video_scale.setRange(10, 1000)
    w.spin_video_scale.setValue(100)
    w.spin_video_scale.valueChanged.connect(w.on_video_scale_changed)
    scale.addWidget(w.spin_video_scale)
    copies = QHBoxLayout()
    copies.addWidget(button('btn_copy_scale', 'Sao chép', w.copy_scale))
    copies.addWidget(button('btn_paste_scale', 'Dán', w.paste_scale))
    scale.addLayout(copies)
    logo_settings = card(editor, 'Logo / watermark', 'Áp dụng lên video chính; outro không phủ logo.')
    logo_settings.addWidget(button('btn_icon', 'Chọn logo…', w.select_icon, icon='overlay.svg'))
    w.lbl_icon = text('Chưa chọn logo', 'micro')
    logo_settings.addWidget(w.lbl_icon)
    position = QGridLayout()
    for col, (name, label, low, high, value) in enumerate([('spin_x', 'X (px)', 0, 4000, 0), ('spin_y', 'Y (px)', 0, 4000, 0), ('spin_scale', 'Cỡ (%)', 10, 500, 100)]):
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setValue(value)
        spin.valueChanged.connect(w.on_icon_setting_changed)
        setattr(w, name, spin)
        position.addWidget(text(label), 0, col)
        position.addWidget(spin, 1, col)
    logo_settings.addLayout(position)
    logo_settings.addWidget(button('btn_apply_icon_all', 'Áp dụng cho tất cả video', w.apply_icon_all))
    copies = QHBoxLayout()
    copies.addWidget(button('btn_copy_icon', 'Sao chép', w.copy_icon))
    copies.addWidget(button('btn_paste_icon', 'Dán', w.paste_icon))
    logo_settings.addLayout(copies)
    logo_settings.addWidget(button('btn_del_icon', 'Xóa logo', w.clear_icon, 'danger'))
    editor.addStretch()
    editor.addWidget(button('btn_finish_edit', 'Xong', w.video_editor.close, 'primary'))
    side.addStretch()
    w.sidebar_scroll = scroll(sidebar)
    w.sidebar_scroll.setFixedWidth(300)
    body.addWidget(w.sidebar_scroll)
    main.addLayout(body, 1)

    footer = QFrame()
    footer.setObjectName('footer')
    foot = QHBoxLayout(footer)
    foot.setContentsMargins(24, 12, 24, 12)
    summary = QVBoxLayout()
    w.output_summary = text('0 file đầu ra', 'section')
    w.lbl_output = text('Lưu cùng thư mục video nguồn', 'micro')
    w.lbl_output.setMaximumWidth(550)
    summary.addWidget(w.output_summary)
    summary.addWidget(w.lbl_output)
    foot.addLayout(summary, 1)
    foot.addWidget(button('btn_back', 'Quay lại', lambda: w.set_step(w.steps.currentIndex() - 1)))
    foot.addWidget(button('btn_output', 'Thư mục lưu', w.select_output_dir))
    foot.addWidget(button('btn_next', 'Tiếp tục: Thiết lập', lambda: w.set_step(w.steps.currentIndex() + 1), 'primary'))
    foot.addWidget(button('btn_start', 'Xuất video', w.start_processing, 'primary'))
    main.addWidget(footer)
    w.ui_status = text('Sẵn sàng · FFmpeg tích hợp · File gốc được giữ nguyên', 'status')
    main.addWidget(w.ui_status)
