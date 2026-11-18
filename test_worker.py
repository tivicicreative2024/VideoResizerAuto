import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import video_resizer as vr
from output_naming import plan_outputs


class WorkerTests(unittest.TestCase):
    def test_worker_writes_reviewed_paths_with_forward_slash_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'nguồn.mp4'
            subprocess.run([vr.FFMPEG_CMD, '-v', 'error', '-n', '-f', 'lavfi', '-i',
                            'testsrc2=size=160x120:rate=30:duration=0.12', '-c:v', 'libx264', str(source)],
                           check=True, capture_output=True)
            files = [source.as_posix()]
            plan = plan_outputs(files, folder, [(1080, 1080)], 'Campaign_%N', 7, 3)
            worker = vr.WorkerThread(files, folder, True, False, False, None, None, None,
                                     render_mode='low_spec', output_plan=plan,
                                     selected_encoder='CPU (libx264 - Cân bằng)')
            worker.run()
            self.assertTrue((Path(folder) / 'Campaign_007.mp4').is_file(), 'Worker skipped reviewed output')
            # A file created after the review must survive the FFmpeg -n boundary.
            output = Path(plan[0]['output'])
            before = output.read_bytes()
            worker.run()
            self.assertEqual(output.read_bytes(), before)

    def test_worker_snapshots_inputs_and_per_video_settings(self):
        files = ['source.mp4']
        settings = {'source.mp4': {'path': None, 'scale': 100, 'x': 1, 'y': 2}}
        scales = {'source.mp4': 100}
        worker = vr.WorkerThread(files, '.', True, False, False, None, None, None, settings, scales)
        files.append('other.mp4')
        settings['source.mp4']['x'] = 999
        scales['source.mp4'] = 50
        self.assertEqual(worker.input_files, ['source.mp4'])
        self.assertEqual(worker.icon_settings['source.mp4']['x'], 1)
        self.assertEqual(worker.video_scales['source.mp4'], 100)

    def test_failed_gpu_partial_is_replaced_by_real_cpu_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.mp4'
            subprocess.run([vr.FFMPEG_CMD, '-v', 'error', '-n', '-f', 'lavfi', '-i',
                            'testsrc2=size=160x120:rate=30:duration=0.12', '-c:v', 'libx264', str(source)],
                           check=True, capture_output=True)
            output = Path(folder) / 'fallback.mp4'
            worker = vr.WorkerThread([str(source)], folder, True, False, False, None, None, None,
                                     render_mode='low_spec', selected_encoder='GPU test')
            with patch.object(vr, 'AVAILABLE_ENCODERS', {'GPU test': ['-c:v', 'libx264', '-profile:v', 'INVALID']}):
                self.assertTrue(worker.run_ffmpeg(str(source), 1080, 1080, str(output)))
            self.assertGreater(output.stat().st_size, 100)
            result = subprocess.run([vr.FFMPEG_CMD, '-v', 'error', '-i', str(output), '-f', 'null', '-'], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_silent_source_and_outro_finish_with_bounded_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            source, outro = Path(folder) / 'source.mp4', Path(folder) / 'outro.mp4'
            for path in (source, outro):
                subprocess.run([vr.FFMPEG_CMD, '-v', 'error', '-n', '-f', 'lavfi', '-i',
                                'testsrc2=size=160x120:rate=30:duration=0.5', '-c:v', 'libx264', str(path)],
                               check=True, capture_output=True)
            output = Path(folder) / 'out.mp4'
            worker = vr.WorkerThread([str(source)], folder, True, False, False, str(outro), None, None,
                                     render_mode='low_spec', selected_encoder='CPU (libx264 - Cân bằng)')
            real_run = subprocess.run
            # Endless anullsrc used to hang FFmpeg; the timeout turns a regression into a failure.
            with patch.object(subprocess, 'run', lambda *a, **k: real_run(*a, timeout=60, **k)):
                self.assertTrue(worker.run_ffmpeg(str(source), 1080, 1080, str(output), str(outro)))
            self.assertAlmostEqual(worker.media_duration(str(output)), 1.0, delta=0.2)

if __name__ == '__main__':
    unittest.main()
