import tempfile
import unittest
from pathlib import Path


class OutputNamingTests(unittest.TestCase):
    def plan(self, *args, **kwargs):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("output_naming"), "Output planner is not implemented")
        import output_naming
        return output_naming.plan_outputs(*args, **kwargs)

    def test_tokens_number_every_output_and_preserve_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = self.plan([str(Path(folder) / "Nguồn.mov")], folder,
                             [(1080, 1920), (1080, 1080)], "%F_%N_%S_%D_%%", 7, 3, "20261106")
            self.assertEqual([Path(x['output']).name for x in rows],
                             ["Nguồn_007_9x16_20261106_%.mov", "Nguồn_008_1x1_20261106_%.mov"])

    def test_collisions_never_overwrite_inputs_or_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "clip.mp4"
            source.write_bytes(b"original")
            (Path(folder) / "clip-2.mp4").write_bytes(b"existing")
            rows = self.plan([str(source), str(Path(folder) / "other" / "CLIP.mp4")], folder,
                             [(1080, 1080)], "%F", 1, 1)
            self.assertEqual([Path(x['output']).name for x in rows], ["clip-3.mp4", "CLIP-4.mp4"])
            self.assertEqual(source.read_bytes(), b"original")

    def test_duplicate_custom_names_are_resolved_without_changing_numbering(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = self.plan([str(Path(folder) / "a.mp4")], folder,
                             [(1080, 1080), (1920, 1080)], "Campaign", 1, 1)
            self.assertEqual([Path(x['output']).name for x in rows], ["Campaign.mp4", "Campaign-2.mp4"])
            self.assertTrue(rows[1]['renamed'])

    def test_invalid_windows_names_and_tokens_are_rejected(self):
        for template in ["", "../bad", "bad:name", "CON", "nul.txt", "trailing.", "bad\nname", "%Q", "abc%", "x" * 256]:
            with self.subTest(template=template), self.assertRaises(ValueError):
                self.plan(["source.mp4"], ".", [(1080, 1080)], template, 1, 3)

    def test_number_settings_and_empty_format_are_validated(self):
        for formats, start, padding in [([], 1, 3), ([(1080,1080)], 0, 3), ([(1080,1080)], 1, 7)]:
            with self.assertRaises(ValueError):
                self.plan(["source.mp4"], ".", formats, "%F_%N", start, padding)

    def test_original_stem_tokens_are_not_expanded(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = self.plan([str(Path(folder) / "clip%N.mp4")], folder, [(1080,1080)], "%F_%N", 1, 1)
            self.assertEqual(Path(rows[0]['output']).name, "clip%N_1.mp4")


if __name__ == "__main__":
    unittest.main()
