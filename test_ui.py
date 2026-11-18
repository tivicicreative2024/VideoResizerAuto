import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import tempfile
import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication, QMessageBox
import video_resizer as vr

APP = QApplication.instance() or QApplication([])
CPU = 'CPU (libx264 - Cân bằng)'
vr.AVAILABLE_ENCODERS = {CPU: ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28', '-pix_fmt', 'yuv420p']}

class UiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.profile_dir = patch.object(vr.QStandardPaths, 'writableLocation', return_value=self.temp.name)
        self.frozen = patch.object(vr.sys, 'frozen', True, create=True)
        self.profile_dir.start()
        self.frozen.start()
        self.window = vr.VideoResizerApp()

    def tearDown(self):
        self.window.close()
        self.profile_dir.stop()
        self.frozen.stop()
        self.temp.cleanup()

    def test_navigation_and_live_names_match_review(self):
        w = self.window
        self.assertTrue(hasattr(w, 'steps'), 'Three-step navigation is missing')
        w.add_video_paths([str(Path(self.temp.name) / 'source.mp4')])
        w.name_template.setText('Campaign_%N_%S')
        w.number_start.setValue(7)
        w.set_step(1)
        self.assertEqual(w.steps.currentIndex(), 1)
        w.set_step(2)
        self.assertEqual(w.output_table.rowCount(), 3)
        self.assertEqual(w.output_table.item(0, 1).text(), 'Campaign_007_1x1.mp4')
        self.assertEqual(w.output_table.item(2, 1).text(), 'Campaign_009_9x16.mp4')
        self.assertEqual(Path(w.output_plan[0]['output']).name, w.output_table.item(0, 1).text())
        w.name_template.setText('../bad')
        self.assertFalse(w.btn_start.isEnabled())
        self.assertTrue(w.naming_error.text())

    def test_empty_batch_does_not_advance_and_removal_keeps_settings_aligned(self):
        w = self.window
        self.assertTrue(hasattr(w, 'steps'), 'Three-step navigation is missing')
        w.set_step(1)
        self.assertEqual(w.steps.currentIndex(), 0)
        files = [str(Path(self.temp.name) / name) for name in ['a.mp4', 'b.mp4']]
        w.add_video_paths(files)
        w.listbox.setCurrentRow(0)
        w.remove_selected_video()
        self.assertEqual(w.input_files, [files[1]])
        self.assertNotIn(files[0], w.icon_settings)
        self.assertEqual(w.listbox.currentRow(), 0)

    def test_naming_profile_round_trip_and_legacy_defaults(self):
        w = self.window
        self.assertTrue(hasattr(w, 'name_template'), 'Naming controls are missing')
        w.name_template.setText('Project_%N_%D')
        w.number_start.setValue(12)
        w.number_padding.setCurrentIndex(4)
        w.chk_sq.setChecked(False)
        with patch.object(QMessageBox, 'information'):
            w.save_profile()
        w.name_template.setText('Other')
        w.on_profile_changed()
        self.assertEqual(w.name_template.text(), 'Project_%N_%D')
        self.assertEqual(w.number_start.value(), 12)
        self.assertEqual(w.number_padding.currentData(), 5)
        self.assertFalse(w.chk_sq.isChecked())
        w.profiles[w.cb_profiles.currentText()] = {}
        w.on_profile_changed()
        self.assertEqual(w.name_template.text(), '%F_%S')
        self.assertTrue(w.chk_sq.isChecked())

    def test_theme_reaches_controls_inside_scroll_areas(self):
        w = self.window
        w.show()
        APP.processEvents()
        self.assertEqual(w.name_template.font().pixelSize(), w.cb_profiles.font().pixelSize())
        self.assertEqual(w.thumbnail.font().pixelSize(), w.cb_profiles.font().pixelSize())

    def test_switching_profile_applies_preset_to_loaded_sources(self):
        w = self.window
        source = str(Path(self.temp.name) / 'source.mp4')
        w.add_video_paths([source])
        w.profiles[w.cb_profiles.currentText()] = {'video_scale': 150, 'icon_path': 'logo.png', 'icon_x': 12, 'icon_y': 13, 'icon_scale': 60}
        w.on_profile_changed()
        self.assertEqual(w.video_scales[source], 150)
        self.assertEqual(w.icon_settings[source], {'path': 'logo.png', 'x': 12, 'y': 13, 'scale': 60})

    def test_real_export_uses_review_plan_and_restores_controls(self):
        w = self.window
        source = Path(self.temp.name) / 'nguồn.mp4'
        subprocess.run([vr.FFMPEG_CMD, '-v', 'error', '-n', '-f', 'lavfi', '-i',
                        'testsrc2=size=160x120:duration=0.12:rate=30', '-c:v', 'libx264', str(source)],
                       check=True, capture_output=True)
        w.add_video_paths([source.as_posix()])
        w.chk_hz.setChecked(False)
        w.chk_vt.setChecked(False)
        w.name_template.setText('Done_%N')
        w.set_step(2)
        reviewed = w.output_plan[0]['output']
        with patch.object(QMessageBox, 'information'), patch.object(vr.os, 'startfile', create=True):
            w.start_processing()
            self.assertTrue(w.is_processing)
            self.assertFalse(w.name_template.isEnabled())
            deadline = time.monotonic() + 20
            while w.is_processing and time.monotonic() < deadline:
                APP.processEvents()
                time.sleep(0.01)
            w.worker.wait(2000)
            APP.processEvents()
        self.assertFalse(w.is_processing)
        self.assertTrue(w.name_template.isEnabled())
        self.assertEqual(w.output_table.item(0, 3).text(), 'Hoàn tất')
        self.assertEqual(Path(reviewed).name, 'Done_001.mp4')
        self.assertTrue(Path(reviewed).exists())

    def test_numbering_is_shown_only_for_a_real_number_token(self):
        w = self.window
        self.assertTrue(hasattr(w, 'numbering_options'), 'Conditional numbering controls are missing')
        w.name_template.setText('%F_%S')
        self.assertTrue(w.numbering_options.isHidden())
        w.name_template.setText('Campaign_%N')
        self.assertFalse(w.numbering_options.isHidden())
        w.number_start.setValue(17)
        w.name_template.setText('Campaign_%%N')
        self.assertTrue(w.numbering_options.isHidden())
        w.name_template.setText('Campaign_%N')
        self.assertEqual(w.number_start.value(), 17)

    def test_video_editor_keeps_per_video_controls_and_locks_during_export(self):
        w = self.window
        self.assertTrue(hasattr(w, 'video_editor'), 'Separate video editor is missing')
        source = str(Path(self.temp.name) / 'source.mp4')
        w.add_video_paths([source])
        w.open_video_editor()
        self.assertTrue(w.video_editor.isVisible())
        self.assertTrue(w.video_editor.isAncestorOf(w.spin_video_scale))
        self.assertFalse(w.sidebar_scroll.isAncestorOf(w.spin_video_scale))
        w.spin_video_scale.setValue(140)
        self.assertEqual(w.video_scales[source], 140)
        w.set_processing_state(True)
        self.assertFalse(w.video_editor.isVisible())
        self.assertFalse(w.spin_video_scale.isEnabled())
        w.set_processing_state(False)
        w.open_video_editor()
        self.assertEqual(w.spin_video_scale.value(), 140)

    def test_optional_sections_are_collapsed_without_changing_values(self):
        w = self.window
        self.assertTrue(hasattr(w, 'performance_options'), 'Expandable performance section is missing')
        self.assertTrue(w.performance_options.isHidden())
        self.assertTrue(w.outro_options.isHidden())
        w.btn_performance.click()
        self.assertFalse(w.performance_options.isHidden())
        w.cb_render_mode.setCurrentIndex(0)
        w.btn_performance.click()
        self.assertTrue(w.performance_options.isHidden())
        self.assertEqual(w.cb_render_mode.currentData(), 'low_spec')

    def test_editor_closes_when_its_selection_is_removed(self):
        w = self.window
        w.add_video_paths([str(Path(self.temp.name) / 'source.mp4')])
        w.open_video_editor()
        w.listbox.clearSelection()
        self.assertFalse(w.btn_edit_video.isEnabled())
        self.assertFalse(w.video_editor.isVisible())
        w.listbox.setCurrentRow(0)
        w.open_video_editor()
        w.clear_list()
        self.assertFalse(w.video_editor.isVisible())

if __name__ == '__main__':
    unittest.main()
