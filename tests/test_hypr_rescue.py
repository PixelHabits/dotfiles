"""Run recovery checks with a fake hyprctl; never contact the live compositor."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "dot_local/bin/executable_hypr-rescue"


class RescueTests(unittest.TestCase):
    def run_rescue(self, args=(), instances=None, signature="", failure="", instance_exit="0"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "calls"
            tool = root / "hyprctl"
            tool.write_text("""#!/usr/bin/env python3
import json, os, sys
with open(os.environ['CALLS'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1:] == ['-j', 'instances']:
    print(os.environ['INSTANCES'])
    sys.exit(int(os.environ['INSTANCE_EXIT']))
command = ' '.join(sys.argv[3:])
print('error: rejected' if command == os.environ['FAILURE'] else 'ok')
""")
            tool.chmod(0o755)
            env = os.environ | {
                "PATH": f"{root}:/usr/bin:/bin",
                "CALLS": str(log),
                "INSTANCES": json.dumps([{"instance": "mine"}] if instances is None else instances),
                "INSTANCE_EXIT": instance_exit,
                "HYPRLAND_INSTANCE_SIGNATURE": signature,
                "FAILURE": failure,
            }
            result = subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True)
            calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, calls

    def test_single_instance_restores_without_session_or_process_mutation(self):
        result, calls = self.run_rescue()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [["-j", "instances"], ["-i", "mine", "reload"], ["-i", "mine", "dispatch", "dpms", "on"]])

    def test_multiple_instances_require_selection(self):
        result, calls = self.run_rescue(instances=[{"instance": "a"}, {"instance": "b"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_explicit_selection_overrides_inherited_session(self):
        result, calls = self.run_rescue(["b"], instances=[{"instance": "a"}, {"instance": "b"}], signature="a")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1], ["-i", "b", "reload"])

    def test_invalid_or_stale_instance_never_mutates(self):
        for instances, signature in [([], ""), ([{"instance": "mine"}], "stale"), ({}, ""), ([{"instance": None}], "")]:
            with self.subTest(instances=instances, signature=signature):
                result, calls = self.run_rescue(instances=instances, signature=signature)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(calls), 1)

    def test_failed_listing_never_mutates(self):
        result, calls = self.run_rescue(instance_exit="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_protocol_error_stops_before_waking_outputs(self):
        result, calls = self.run_rescue(failure="reload")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("restore requested", result.stdout)

    def test_dpms_error_is_not_reported_as_success(self):
        result, calls = self.run_rescue(failure="dispatch dpms on")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 3)

    def test_help_does_not_contact_compositor(self):
        result, calls = self.run_rescue(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
