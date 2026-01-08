"""
Comprehensive tests for the calculate_significance function.

Tests cover all scoring rules including universal context files, manifests,
signals, path depth penalties, and ignored directory penalties across all
supported languages.

Run with: python -m unittest tests.test_refactor
"""

import unittest
from pathlib import Path

from core.refactor import calculate_significance
from models import SupportedLanguage


class TestUniversalContextFiles(unittest.TestCase):
    """Test universal context file detection (highest priority, score: 1000 - (depth * 5))."""

    def test_readme_md(self):
        """README.md should return 1000 minus depth penalty."""
        # Root level (depth=1): 1000 - 5 = 995
        assert calculate_significance(Path("README.md"), SupportedLanguage.PY).score == 995
        assert calculate_significance(Path("readme.md"), SupportedLanguage.JS).score == 995
        assert calculate_significance(Path("README.MD"), SupportedLanguage.JAVA).score == 995

    def test_readme_variants(self):
        """Files starting with 'readme' should return 1000 minus depth penalty."""
        # Root level (depth=1): 1000 - 5 = 995
        assert calculate_significance(Path("README.txt"), SupportedLanguage.PY).score == 995
        assert calculate_significance(Path("readme.rst"), SupportedLanguage.GO).score == 995
        assert calculate_significance(Path("README"), SupportedLanguage.CS).score == 995

    def test_any_md_file(self):
        """Any .md file should return 1000 minus depth penalty."""
        # Depth=2 (docs + guide.md): 1000 - 10 = 990
        assert (
            calculate_significance(Path("docs/guide.md"), SupportedLanguage.PY).score == 990
        )
        # Root level (depth=1): 1000 - 5 = 995
        assert (
            calculate_significance(Path("CHANGELOG.md"), SupportedLanguage.JS).score == 995
        )
        # Depth=3 (deep + nested + file.md): 1000 - 15 = 985
        assert (
            calculate_significance(Path("deep/nested/file.md"), SupportedLanguage.CPP).score
            == 985
        )

    def test_universal_context_files(self):
        """Files in UNIVERSAL_CONTEXT_FILES should return 1000 minus depth penalty."""
        # Root level (depth=1): 1000 - 5 = 995
        assert (
            calculate_significance(Path(".cursorrules"), SupportedLanguage.PY).score == 995
        )
        # Root level (depth=1): 1000 - 5 = 995
        assert (
            calculate_significance(Path("architecture.md"), SupportedLanguage.JS).score
            == 995
        )
        # Root level (depth=1): 1000 - 5 = 995
        assert (
            calculate_significance(Path("dockerfile"), SupportedLanguage.JAVA).score == 995
        )


class TestManifestFiles(unittest.TestCase):
    """Test manifest file detection (score: +80)."""

    def test_python_manifests(self):
        """Python manifest files should score +80."""
        # Root level (depth=1): 80 - 5 = 75
        assert (
            calculate_significance(Path("requirements.txt"), SupportedLanguage.PY).score == 75
        )
        assert (
            calculate_significance(Path("pyproject.toml"), SupportedLanguage.PY).score == 75
        )
        assert calculate_significance(Path("setup.py"), SupportedLanguage.PY).score == 75

    def test_js_manifests(self):
        """JavaScript manifest files should score +80."""
        assert calculate_significance(Path("package.json"), SupportedLanguage.JS).score == 75
        assert calculate_significance(Path("tsconfig.json"), SupportedLanguage.JS).score == 75
        assert calculate_significance(Path("deno.json"), SupportedLanguage.JS).score == 75

    def test_java_manifests(self):
        """Java manifest files should score +80."""
        assert calculate_significance(Path("pom.xml"), SupportedLanguage.JAVA).score == 75
        assert (
            calculate_significance(Path("build.gradle"), SupportedLanguage.JAVA).score == 75
        )
        assert (
            calculate_significance(Path("build.gradle.kts"), SupportedLanguage.JAVA).score
            == 75
        )

    def test_csharp_extension_manifests(self):
        """C# extension-based manifests (.csproj, .sln) should score +80."""
        # Root level: 80 - 5 = 75
        assert (
            calculate_significance(Path("MyProject.csproj"), SupportedLanguage.CS).score == 75
        )
        assert calculate_significance(Path("Solution.sln"), SupportedLanguage.CS).score == 75
        assert calculate_significance(Path("App.fsproj"), SupportedLanguage.CS).score == 75
        assert calculate_significance(Path("Legacy.vbproj"), SupportedLanguage.CS).score == 75

    def test_csharp_filename_manifests(self):
        """C# filename-based manifests should score +80."""
        assert calculate_significance(Path("global.json"), SupportedLanguage.CS).score == 75
        assert calculate_significance(Path("nuget.config"), SupportedLanguage.CS).score == 75

    def test_go_manifests(self):
        """Go manifest files should score +80."""
        assert calculate_significance(Path("go.mod"), SupportedLanguage.GO).score == 75
        assert calculate_significance(Path("go.sum"), SupportedLanguage.GO).score == 75

    def test_manifest_with_depth_penalty(self):
        """Manifests in subdirectories should have depth penalty applied."""
        # Depth=2: 80 - 10 = 70
        assert (
            calculate_significance(Path("src/package.json"), SupportedLanguage.JS).score == 70
        )
        # Depth=3: 80 - 15 = 65
        assert (
            calculate_significance(
                Path("backend/api/requirements.txt"), SupportedLanguage.PY
            ).score
            == 65
        )


class TestSignalFiles(unittest.TestCase):
    """Test signal file detection (score: +60)."""

    def test_python_signals(self):
        """Python signal files should score +60."""
        # Root level file (depth=1): 60 - 5 = 55
        assert calculate_significance(Path("main.py"), SupportedLanguage.PY).score == 55
        assert calculate_significance(Path("app.py"), SupportedLanguage.PY).score == 55
        assert calculate_significance(Path("__init__.py"), SupportedLanguage.PY).score == 55
        assert calculate_significance(Path("__main__.py"), SupportedLanguage.PY).score == 55

    def test_js_signals(self):
        """JavaScript signal files should score +60."""
        # Root level (depth=1): 60 - 5 = 55
        assert calculate_significance(Path("index.js"), SupportedLanguage.JS).score == 55
        assert calculate_significance(Path("main.ts"), SupportedLanguage.JS).score == 55
        assert calculate_significance(Path("app.tsx"), SupportedLanguage.JS).score == 55
        assert calculate_significance(Path("server.js"), SupportedLanguage.JS).score == 55

    def test_java_signals(self):
        """Java signal files should score +60."""
        # Root level (depth=1): 60 - 5 = 55
        assert calculate_significance(Path("Main.java"), SupportedLanguage.JAVA).score == 55
        assert (
            calculate_significance(Path("Application.java"), SupportedLanguage.JAVA).score
            == 55
        )

    def test_csharp_signals(self):
        """C# signal files should score +60."""
        # Root level (depth=1): 60 - 5 = 55
        assert calculate_significance(Path("Program.cs"), SupportedLanguage.CS).score == 55
        assert calculate_significance(Path("Startup.cs"), SupportedLanguage.CS).score == 55
        assert calculate_significance(Path("App.cs"), SupportedLanguage.CS).score == 55

    def test_go_signals(self):
        """Go signal files should score +60."""
        # "main.go" is both a manifest and signal, so manifest takes precedence: 80 - 5 = 75
        assert calculate_significance(Path("main.go"), SupportedLanguage.GO).score == 75
        # "server.go" is only a signal: 60 - 5 = 55
        assert calculate_significance(Path("server.go"), SupportedLanguage.GO).score == 55

    def test_signal_with_wrong_extension(self):
        """Signal names with wrong extensions should not match."""
        # "main" is a signal, but .txt is not a Python extension
        assert calculate_significance(Path("main.txt"), SupportedLanguage.PY).score == -5

    def test_signal_with_wrong_stem(self):
        """Non-signal files with correct extension should get source file bonus."""
        # "utils" is not a signal, but .py is a source extension: +50 - 5 = 45
        assert calculate_significance(Path("utils.py"), SupportedLanguage.PY).score == 45

    def test_signal_with_depth_penalty(self):
        """Signals in subdirectories should have depth penalty applied."""
        # Depth=2 (src + main.py): 60 - 10 = 50
        assert calculate_significance(Path("src/main.py"), SupportedLanguage.PY).score == 50
        # Depth=3 (backend + api + index.ts): 60 - 15 = 45
        assert (
            calculate_significance(Path("backend/api/index.ts"), SupportedLanguage.JS).score
            == 45
        )


class TestPathDepthPenalty(unittest.TestCase):
    """Test path depth penalty (score: -5 per directory level)."""

    def test_root_level_file(self):
        """Root level files have depth=1, penalty=-5."""
        # Source file (+50) - depth penalty (-5) = 45
        assert calculate_significance(Path("utils.py"), SupportedLanguage.PY).score == 45

    def test_nested_files(self):
        """Deeper files have larger penalties applied to source file bonus."""
        # Source file (+50) - depth penalty
        # Depth=1: 50 - 5 = 45
        assert calculate_significance(Path("file.py"), SupportedLanguage.PY).score == 45
        # Depth=2: 50 - 10 = 40
        assert calculate_significance(Path("src/file.py"), SupportedLanguage.PY).score == 40
        # Depth=3: 50 - 15 = 35
        assert (
            calculate_significance(Path("src/utils/file.py"), SupportedLanguage.PY).score
            == 35
        )
        # Depth=4: 50 - 20 = 30
        assert (
            calculate_significance(
                Path("src/utils/helpers/file.py"), SupportedLanguage.PY
            ).score
            == 30
        )

    def test_absolute_paths(self):
        """Absolute paths should calculate depth correctly."""
        abs_path = Path("/Users/user/project/src/main.py")
        # Depth includes all parts, so this will be deeper
        meta = calculate_significance(abs_path, SupportedLanguage.PY)
        # Should have signal (+60) minus depth penalty
        assert meta.score < 60  # Depth penalty reduces the score


class TestIgnoredDirectories(unittest.TestCase):
    """Test ignored directory penalty (score: -100)."""

    def test_python_ignored_dirs(self):
        """Files in Python ignored directories should get -100 penalty."""
        # Signal files: Signal (+60) - depth (10, depth=2) - ignored (-100) = -50
        assert (
            calculate_significance(Path("tests/main.py"), SupportedLanguage.PY).score == -50
        )
        assert calculate_significance(Path("test/app.py"), SupportedLanguage.PY).score == -50
        # Non-signal source files: Source (+50) - depth (10, depth=2) - ignored (-100) = -60
        assert (
            calculate_significance(Path("mocks/utils.py"), SupportedLanguage.PY).score == -60
        )
        assert (
            calculate_significance(Path("examples/demo.py"), SupportedLanguage.PY).score
            == -60
        )

    def test_js_ignored_dirs(self):
        """Files in JS ignored directories should get -100 penalty."""
        # Signal (+60) - depth (10, depth=2) - ignored (-100) = -50
        assert (
            calculate_significance(Path("tests/index.js"), SupportedLanguage.JS).score == -50
        )
        # Depth=2: 60 - 10 - 100 = -50
        assert (
            calculate_significance(Path("__tests__/main.ts"), SupportedLanguage.JS).score
            == -50
        )
        assert calculate_significance(Path("spec/app.tsx"), SupportedLanguage.JS).score == -50

    def test_nested_ignored_dirs(self):
        """Files in nested ignored directories should still get penalty."""
        # Depth=3 (src + tests + main.py): 60 - 15 - 100 = -55
        assert (
            calculate_significance(Path("src/tests/main.py"), SupportedLanguage.PY).score
            == -55
        )
        # Depth=4 (backend + tests + unit + app.ts): 60 - 20 - 100 = -60
        assert (
            calculate_significance(
                Path("backend/tests/unit/app.ts"), SupportedLanguage.JS
            ).score
            == -60
        )

    def test_manifest_in_ignored_dir(self):
        """Manifests in ignored directories still get penalty."""
        # Manifest (+80) - depth (10) - ignored (-100) = -30
        assert (
            calculate_significance(Path("tests/package.json"), SupportedLanguage.JS).score
            == -30
        )

    def test_ignored_dir_case_insensitive(self):
        """Ignored directory matching should be case-insensitive."""
        # "Tests" should match "tests" pattern (depth=2: 60 - 10 - 100 = -50)
        assert (
            calculate_significance(Path("Tests/main.py"), SupportedLanguage.PY).score == -50
        )


class TestCombinedScoring(unittest.TestCase):
    """Test combinations of scoring rules."""

    def test_manifest_and_signal(self):
        """A file can match both manifest and signal (highest applies)."""
        # "main.go" is both a manifest and signal
        # Manifest: +80, Signal: +60, Depth: -5 = 75 (manifest takes precedence)
        assert calculate_significance(Path("main.go"), SupportedLanguage.GO).score == 75

    def test_signal_in_ignored_dir(self):
        """Signal files in ignored directories get both penalties."""
        # Signal (+60) - depth (10, depth=2) - ignored (-100) = -50
        assert (
            calculate_significance(Path("tests/main.py"), SupportedLanguage.PY).score == -50
        )

    def test_manifest_in_ignored_dir(self):
        """Manifest files in ignored directories get both penalties."""
        # Manifest (+80) - depth (10) - ignored (-100) = -30
        assert (
            calculate_significance(Path("tests/package.json"), SupportedLanguage.JS).score
            == -30
        )

    def test_deep_manifest_in_ignored_dir(self):
        """Deep manifests in ignored directories accumulate penalties."""
        # Manifest (+80) - depth (15) - ignored (-100) = -35
        assert (
            calculate_significance(Path("src/tests/package.json"), SupportedLanguage.JS).score
            == -35
        )


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_path(self):
        """Empty path should still work (depth=0)."""
        meta = calculate_significance(Path(""), SupportedLanguage.PY)
        # No matches, no depth penalty = 0
        assert meta.score == 0

    def test_file_with_multiple_extensions(self):
        """Files with multiple extensions should use stem correctly."""
        # file.tar.gz -> stem is "file.tar", suffix is ".gz"
        # This tests the comment in the code about multi-extension files
        path = Path("file.tar.gz")
        meta = calculate_significance(path, SupportedLanguage.PY)
        # Should not match any signals (stem="file.tar" not in signals)
        assert meta.score < 60

    def test_case_insensitivity(self):
        """Matching should be case-insensitive."""
        assert calculate_significance(Path("MAIN.PY"), SupportedLanguage.PY).score == 55
        assert calculate_significance(Path("Package.Json"), SupportedLanguage.JS).score == 75
        assert (
            calculate_significance(Path("MyProject.CSProj"), SupportedLanguage.CS).score == 75
        )

    def test_regular_source_file(self):
        """Regular source files should get source file bonus (+50) minus depth penalty."""
        # Source file (+50) - depth penalty (-5) = 45
        assert calculate_significance(Path("utils.py"), SupportedLanguage.PY).score == 45
        assert calculate_significance(Path("helper.ts"), SupportedLanguage.JS).score == 45
        assert (
            calculate_significance(Path("Service.java"), SupportedLanguage.JAVA).score == 45
        )

    def test_all_languages_supported(self):
        """Verify all supported languages work without errors."""
        test_path = Path("main.py")
        for language in SupportedLanguage:
            meta = calculate_significance(test_path, language)
            assert isinstance(meta.score, int)
            # Universal context check might return 1000 minus depth, otherwise should be reasonable
            assert meta.score >= -1000 or meta.score >= 990


if __name__ == "__main__":
    unittest.main()
