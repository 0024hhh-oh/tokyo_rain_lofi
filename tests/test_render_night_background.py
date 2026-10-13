"""Exercise the video branch without downloading dependencies or uploading."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/render_night_background.sh"
FAKE_TOOL = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

tool = Path(sys.argv[0]).name
args = sys.argv[1:]
if tool == "ffmpeg":
    Path(args[-1]).write_bytes(b"video-fixture")
elif tool == "ffprobe":
    if "format=duration" in args:
        print("30.0")
    elif "stream=index" in args and os.environ.get("TEST_AUDIO") == "1":
        print("0")
elif tool == "node":
    analysis = json.loads(os.environ["TEST_ANALYSIS"])
    if args[0] == "scripts/prepare_remotion_background.mjs":
        Path("src/generated-light-zones.json").write_text(json.dumps(analysis))
    elif args[0] == "-p":
        print(str(analysis["animate"]).lower())
    elif args[0] == "-e":
        safe = [z for z in analysis["zones"]
                if z["hasLightCore"] and z["warmth"] >= .4 and z["y"] < .72]
        print(min(3, len(safe)))
    else:
        sys.exit(2)
elif tool == "npx":
    Path("render-args.json").write_text(json.dumps(args))
    if os.environ.get("TEST_RENDER_FAIL") == "1":
        sys.exit(9)
    Path(args[4]).write_bytes(b"rendered-video")
else:
    sys.exit(2)
'''


class NightBackgroundTests(unittest.TestCase):
    def run_video_branch(self, count, animate=True, **overrides):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("video_assets", "node_modules", "src", "bin"):
                (root / name).mkdir()
            (root / "video_assets/background.mp4").write_bytes(b"source-video")
            binary = root / "bin/fake-tool"
            binary.write_text(FAKE_TOOL)
            binary.chmod(0o755)
            for name in ("ffmpeg", "ffprobe", "node", "npx"):
                (root / "bin" / name).symlink_to(binary)
            # The production script calls python for source-duration validation.
            (root / "bin/python").symlink_to(shutil.which("python3"))
            zones = [{"hasLightCore": True, "warmth": .8, "y": .3}
                     for _ in range(count)]
            env = dict(os.environ, PATH=f"{root / 'bin'}:{os.environ['PATH']}",
                       ASSET_DIR="video_assets",
                       TEST_ANALYSIS=json.dumps({"animate": animate, "zones": zones}),
                       **overrides)
            result = subprocess.run(["bash", str(SCRIPT)], cwd=root, env=env,
                                    text=True, capture_output=True)
            rendered = (root / "video_assets/background.mp4").exists()
            args_file = root / "render-args.json"
            render_args = json.loads(args_file.read_text()) if args_file.exists() else None
            return result, rendered, render_args

    def test_sparse_and_dense_scenes_continue_to_render(self):
        for count in (0, 1, 2, 3, 7):
            with self.subTest(count=count):
                result, rendered, args = self.run_video_branch(count, animate=count > 0)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(rendered)
                self.assertIn("NightVideoLightingLoop", args)
                self.assertIn("--muted", args)
                self.assertIn("--frames=0-899", args)

    def test_bright_scene_continues_without_lighting(self):
        result, rendered, _ = self.run_video_branch(7, animate=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(rendered)

    def test_render_failure_still_fails_the_batch(self):
        result, rendered, _ = self.run_video_branch(2, TEST_RENDER_FAIL="1")
        self.assertEqual(result.returncode, 9)
        self.assertFalse(rendered)

    def test_audio_stream_in_rendered_background_is_rejected(self):
        result, _, _ = self.run_video_branch(2, TEST_AUDIO="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not contain audio", result.stderr)


if __name__ == "__main__":
    unittest.main()
