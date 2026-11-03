import unittest
import test_modmanager as fixture
import setup_checks


class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.ManagerTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_missing_build_tools_keep_manager_available(self):
        result = setup_checks.check(self.case.repo)
        self.assertTrue(result["manager_ready"])
        self.assertFalse(result["skin_ready"])
        self.assertIn("Builddateien", " ".join(result["warnings"]))

    def test_missing_header_has_actionable_explanation(self):
        log = self.case.repo / "opensmash_mods/logs/arcropolis-build.log"
        log.write_text("fatal error: 'string.h' file not found")
        result = setup_checks.explain_build_error(
            self.case.repo,
            ValueError("ARCropolis-Einrichtung fehlgeschlagen (Code 1)."),
        )
        self.assertIn("Windows 10/11 SDK", result)
        self.assertIn("Code 1", result)

    def test_other_build_error_is_preserved(self):
        self.assertEqual(
            "different error",
            setup_checks.explain_build_error(
                self.case.repo, ValueError("different error")
            ),
        )
