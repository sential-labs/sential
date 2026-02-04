"""
Comprehensive tests for the categorization module using pytest.

Tests cover:
- calculate_significance: scoring rules including universal context files, manifests,
  signals, path depth penalties, and ignored directory penalties across all
  supported languages.
- categorize_files: file categorization and grouping functionality.
"""

from pathlib import Path
import pytest

from core.categorization import calculate_significance, categorize_files
from core.models import FileCategory
from models import SupportedLanguage


# ============================================================================
# Tests for calculate_significance - Universal Context Files
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language",
    [
        ("README.md", SupportedLanguage.PY),
        ("readme.md", SupportedLanguage.JS),
        ("README.MD", SupportedLanguage.JAVA),
        ("README.txt", SupportedLanguage.GO),
        ("readme.rst", SupportedLanguage.CS),
        ("README", SupportedLanguage.CPP),
    ],
)
def test_readme_files(path, language):
    """README files should score 1000 at root level (no depth penalty)."""
    assert calculate_significance(Path(path), language).score == 1000


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language,expected_score",
    [
        ("CHANGELOG.md", SupportedLanguage.PY, 1000),  # depth=1: no penalty
        ("docs/guide.md", SupportedLanguage.JS, 995),  # depth=2: -5
        ("deep/nested/file.md", SupportedLanguage.JAVA, 990),  # depth=3: -10
    ],
)
def test_md_files(path, language, expected_score):
    """Any .md file should score 1000 minus depth penalty."""
    assert calculate_significance(Path(path), language).score == expected_score


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language",
    [
        (".cursorrules", SupportedLanguage.PY),
        ("architecture.md", SupportedLanguage.JS),
        ("dockerfile", SupportedLanguage.JAVA),
    ],
)
def test_universal_context_files(path, language):
    """Files in UNIVERSAL_CONTEXT_FILES should score 1000 at root."""
    assert calculate_significance(Path(path), language).score == 1000


# ============================================================================
# Tests for calculate_significance - Manifest Files
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language",
    [
        ("requirements.txt", SupportedLanguage.PY),
        ("package.json", SupportedLanguage.JS),
        ("pom.xml", SupportedLanguage.JAVA),
        ("MyProject.csproj", SupportedLanguage.CS),
        ("go.mod", SupportedLanguage.GO),
    ],
)
def test_manifest_files(path, language):
    """Manifest files should score 80 at root level (no depth penalty)."""
    assert calculate_significance(Path(path), language).score == 80


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language",
    [
        ("MyProject.csproj", SupportedLanguage.CS),
        ("Solution.sln", SupportedLanguage.CS),
    ],
)
def test_csharp_extension_manifests(path, language):
    """C# extension-based manifests should match by extension."""
    assert calculate_significance(Path(path), language).score == 80


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language,expected_score",
    [
        ("src/package.json", SupportedLanguage.JS, 75),  # depth=2: 80 - 5
        ("backend/api/requirements.txt", SupportedLanguage.PY, 70),  # depth=3: 80 - 10
    ],
)
def test_manifest_with_depth_penalty(path, language, expected_score):
    """Manifests in subdirectories should have depth penalty applied."""
    assert calculate_significance(Path(path), language).score == expected_score


# ============================================================================
# Tests for calculate_significance - Signal Files
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language",
    [
        ("main.py", SupportedLanguage.PY),
        ("index.js", SupportedLanguage.JS),
        ("Main.java", SupportedLanguage.JAVA),
        ("Program.cs", SupportedLanguage.CS),
        ("server.go", SupportedLanguage.GO),
    ],
)
def test_signal_files(path, language):
    """Signal files should score 60 at root level (no depth penalty)."""
    assert calculate_significance(Path(path), language).score == 60


@pytest.mark.unit
def test_signal_requires_matching_extension():
    """Signal names must have matching language extension."""
    # "main" is a signal, but .txt is not a Python extension
    assert calculate_significance(Path("main.txt"), SupportedLanguage.PY).score == 0


@pytest.mark.unit
def test_non_signal_source_files():
    """Non-signal files with correct extension get source file bonus."""
    # "utils" is not a signal, but .py is a source extension: 50 (no penalty at root)
    assert calculate_significance(Path("utils.py"), SupportedLanguage.PY).score == 50


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language,expected_score",
    [
        ("src/main.py", SupportedLanguage.PY, 55),  # depth=2: 60 - 5
        ("backend/api/index.ts", SupportedLanguage.JS, 50),  # depth=3: 60 - 10
    ],
)
def test_signal_with_depth_penalty(path, language, expected_score):
    """Signals in subdirectories should have depth penalty applied."""
    assert calculate_significance(Path(path), language).score == expected_score


# ============================================================================
# Tests for calculate_significance - Path Depth Penalty
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,expected_score",
    [
        ("file.py", 50),  # depth=1: no penalty
        ("src/file.py", 45),  # depth=2: 50-5
        ("src/utils/file.py", 40),  # depth=3: 50-10
        ("src/utils/helpers/file.py", 35),  # depth=4: 50-15
    ],
)
def test_depth_penalty_applied(path, expected_score):
    """Deeper files have larger penalties applied (root has no penalty)."""
    assert calculate_significance(Path(path), SupportedLanguage.PY).score == expected_score


@pytest.mark.unit
def test_absolute_paths():
    """Absolute paths should calculate depth correctly."""
    abs_path = Path("/Users/user/project/src/main.py")
    meta = calculate_significance(abs_path, SupportedLanguage.PY)
    # Should have signal (base: 60) minus depth penalty
    assert meta.score < 60


# ============================================================================
# Tests for calculate_significance - Ignored Directories
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language,expected_score",
    [
        ("tests/main.py", SupportedLanguage.PY, -45),  # Signal (+60) - depth (5) - ignored (-100)
        ("tests/index.js", SupportedLanguage.JS, -45),
        ("mocks/utils.py", SupportedLanguage.PY, -55),  # Source (+50) - depth (5) - ignored (-100)
    ],
)
def test_ignored_directory_penalty(path, language, expected_score):
    """Files in ignored directories should get -100 penalty."""
    assert calculate_significance(Path(path), language).score == expected_score


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language,expected_score",
    [
        ("src/tests/main.py", SupportedLanguage.PY, -50),  # depth=3: 60-10-100
        ("backend/tests/unit/app.ts", SupportedLanguage.JS, -55),  # depth=4: 60-15-100
    ],
)
def test_nested_ignored_dirs(path, language, expected_score):
    """Files in nested ignored directories should still get penalty."""
    assert calculate_significance(Path(path), language).score == expected_score


@pytest.mark.unit
def test_manifest_in_ignored_dir():
    """Manifests in ignored directories still get penalty."""
    # Manifest (+80) - depth penalty (5, depth=2) - ignored (-100) = -25
    assert (
        calculate_significance(Path("tests/package.json"), SupportedLanguage.JS).score == -25
    )


@pytest.mark.unit
def test_ignored_dir_case_insensitive():
    """Ignored directory matching should be case-insensitive."""
    assert (
        calculate_significance(Path("Tests/main.py"), SupportedLanguage.PY).score == -45
    )  # depth=2: 60-5-100


# ============================================================================
# Tests for calculate_significance - Combined Scoring
# ============================================================================


@pytest.mark.unit
def test_manifest_takes_precedence_over_signal():
    """Files matching both manifest and signal should use manifest category."""
    # "main.go" is both manifest and signal, manifest takes precedence: 80
    assert calculate_significance(Path("main.go"), SupportedLanguage.GO).score == 80


@pytest.mark.unit
def test_deep_manifest_in_ignored_dir():
    """Deep manifests in ignored directories accumulate penalties."""
    # Manifest (+80) - depth penalty (10, depth=3) - ignored (-100) = -30
    assert (
        calculate_significance(Path("src/tests/package.json"), SupportedLanguage.JS).score == -30
    )


# ============================================================================
# Tests for calculate_significance - Edge Cases
# ============================================================================


@pytest.mark.unit
def test_empty_path():
    """Empty path should still work."""
    meta = calculate_significance(Path(""), SupportedLanguage.PY)
    assert meta.score == 0


@pytest.mark.unit
def test_file_with_multiple_extensions():
    """Files with multiple extensions should use stem correctly."""
    # file.tar.gz -> stem is "file.tar", suffix is ".gz"
    meta = calculate_significance(Path("file.tar.gz"), SupportedLanguage.PY)
    # Should not match any signals (stem="file.tar" not in signals)
    assert meta.score < 60


@pytest.mark.unit
@pytest.mark.parametrize(
    "path,language,expected_score",
    [
        ("MAIN.PY", SupportedLanguage.PY, 60),
        ("Package.Json", SupportedLanguage.JS, 80),
        ("MyProject.CSProj", SupportedLanguage.CS, 80),
    ],
)
def test_case_insensitivity(path, language, expected_score):
    """Matching should be case-insensitive."""
    assert calculate_significance(Path(path), language).score == expected_score


@pytest.mark.unit
@pytest.mark.parametrize("language", list(SupportedLanguage))
def test_all_languages_supported(language):
    """Verify all supported languages work without errors."""
    test_path = Path("main.py")
    meta = calculate_significance(test_path, language)
    assert isinstance(meta.score, int)
    assert meta.score >= -1000  # Reasonable score range


# ============================================================================
# Tests for categorize_files
# ============================================================================


@pytest.mark.unit
def test_categorizes_files_correctly(progress_display):
    """Files should be categorized into correct buckets."""
    file_paths = [
        Path("README.md"),  # CONTEXT
        Path("package.json"),  # MANIFEST
        Path("index.js"),  # SIGNAL
        Path("helper.js"),  # SOURCE
        Path("random.txt"),  # UNKNOWN
    ]
    result = categorize_files(
        file_paths,
        total_files=5,
        language=SupportedLanguage.JS,
        progress_display=progress_display,
    )

    # All categories should be present
    assert FileCategory.CONTEXT in result
    assert FileCategory.MANIFEST in result
    assert FileCategory.SIGNAL in result
    assert FileCategory.SOURCE in result
    assert FileCategory.UNKNOWN in result

    # Check correct categorization
    assert len(result[FileCategory.CONTEXT]) == 1
    assert result[FileCategory.CONTEXT][0].file_path == Path("README.md")

    assert len(result[FileCategory.MANIFEST]) == 1
    assert result[FileCategory.MANIFEST][0].file_path == Path("package.json")

    assert len(result[FileCategory.SIGNAL]) == 1
    assert result[FileCategory.SIGNAL][0].file_path == Path("index.js")

    assert len(result[FileCategory.SOURCE]) == 1
    assert result[FileCategory.SOURCE][0].file_path == Path("helper.js")

    assert len(result[FileCategory.UNKNOWN]) == 1
    assert result[FileCategory.UNKNOWN][0].file_path == Path("random.txt")


@pytest.mark.unit
def test_empty_file_list(progress_display):
    """Empty file list should return empty categories."""
    result = categorize_files(
        [],
        total_files=0,
        language=SupportedLanguage.PY,
        progress_display=progress_display,
    )

    # All categories should be present but empty
    for category in FileCategory:
        assert category in result
        assert len(result[category]) == 0


@pytest.mark.unit
def test_multiple_files_same_category(progress_display):
    """Multiple files in the same category should all be included."""
    file_paths = [
        Path("README.md"),
        Path("CHANGELOG.md"),
        Path("docs/guide.md"),
    ]
    result = categorize_files(
        file_paths,
        total_files=3,
        language=SupportedLanguage.PY,
        progress_display=progress_display,
    )

    assert len(result[FileCategory.CONTEXT]) == 3
    paths = {meta.file_path for meta in result[FileCategory.CONTEXT]}
    assert paths == {Path("README.md"), Path("CHANGELOG.md"), Path("docs/guide.md")}


@pytest.mark.unit
def test_python_language_heuristics(progress_display):
    """Python-specific files should be categorized correctly."""
    file_paths = [
        Path("requirements.txt"),  # MANIFEST
        Path("main.py"),  # SIGNAL
        Path("__init__.py"),  # SIGNAL
        Path("utils.py"),  # SOURCE
    ]
    result = categorize_files(
        file_paths,
        total_files=4,
        language=SupportedLanguage.PY,
        progress_display=progress_display,
    )

    assert len(result[FileCategory.MANIFEST]) == 1
    assert len(result[FileCategory.SIGNAL]) == 2
    assert len(result[FileCategory.SOURCE]) == 1


@pytest.mark.unit
def test_javascript_language_heuristics(progress_display):
    """JavaScript-specific files should be categorized correctly."""
    file_paths = [
        Path("package.json"),  # MANIFEST
        Path("index.js"),  # SIGNAL
        Path("app.tsx"),  # SIGNAL
        Path("helper.ts"),  # SOURCE
    ]
    result = categorize_files(
        file_paths,
        total_files=4,
        language=SupportedLanguage.JS,
        progress_display=progress_display,
    )

    assert len(result[FileCategory.MANIFEST]) == 1
    assert len(result[FileCategory.SIGNAL]) == 2
    assert len(result[FileCategory.SOURCE]) == 1


@pytest.mark.unit
def test_csharp_extension_manifests_categorization(progress_display):
    """C# extension-based manifests should be recognized."""
    file_paths = [
        Path("MyProject.csproj"),  # MANIFEST (by extension)
        Path("Solution.sln"),  # MANIFEST (by extension)
        Path("Program.cs"),  # SIGNAL
    ]
    result = categorize_files(
        file_paths,
        total_files=3,
        language=SupportedLanguage.CS,
        progress_display=progress_display,
    )

    assert len(result[FileCategory.MANIFEST]) == 2
    assert len(result[FileCategory.SIGNAL]) == 1


@pytest.mark.unit
def test_ignored_directories_penalty(progress_display):
    """Files in ignored directories should still be categorized but with penalty."""
    file_paths = [
        Path("tests/main.py"),  # SIGNAL in ignored dir
        Path("mocks/utils.py"),  # SOURCE in ignored dir
        Path("src/main.py"),  # SIGNAL not in ignored dir
    ]
    result = categorize_files(
        file_paths,
        total_files=3,
        language=SupportedLanguage.PY,
        progress_display=progress_display,
    )

    # Files should still be categorized correctly
    assert len(result[FileCategory.SIGNAL]) == 2
    assert len(result[FileCategory.SOURCE]) == 1

    # But scores should reflect ignored directory penalty
    test_signal = next(
        m for m in result[FileCategory.SIGNAL] if m.file_path == Path("tests/main.py")
    )
    src_signal = next(
        m for m in result[FileCategory.SIGNAL] if m.file_path == Path("src/main.py")
    )
    assert test_signal.score < src_signal.score  # Ignored dir has penalty


@pytest.mark.unit
def test_progress_display_integration(tracking_progress_display):
    """Progress display should be called during processing."""
    file_paths = [Path(f"file{i}.py") for i in range(20)]  # 20 files for progress updates

    categorize_files(
        file_paths,
        total_files=20,
        language=SupportedLanguage.PY,
        progress_display=tracking_progress_display,
    )

    # Should have start, multiple updates, and complete calls
    assert any(call[0] == "start" for call in tracking_progress_display.calls)
    assert any(call[0] == "update" for call in tracking_progress_display.calls)
    assert any(call[0] == "complete" for call in tracking_progress_display.calls)


@pytest.mark.unit
def test_works_with_progress_display(progress_display):
    """Should work correctly when a progress display is provided."""
    file_paths = [Path("main.py"), Path("utils.py")]
    result = categorize_files(
        file_paths,
        total_files=2,
        language=SupportedLanguage.PY,
        progress_display=progress_display,
    )

    assert len(result[FileCategory.SIGNAL]) == 1
    assert len(result[FileCategory.SOURCE]) == 1


@pytest.mark.unit
def test_all_categories_present(progress_display):
    """Result should always contain all FileCategory values."""
    file_paths = [Path("main.py")]  # Only one category
    result = categorize_files(
        file_paths,
        total_files=1,
        language=SupportedLanguage.PY,
        progress_display=progress_display,
    )

    # All categories should be keys in the result
    for category in FileCategory:
        assert category in result
        assert isinstance(result[category], list)


@pytest.mark.unit
def test_file_metadata_preserved(progress_display):
    """FileMetadata objects should contain correct information."""
    file_paths = [Path("README.md"), Path("main.py")]
    result = categorize_files(
        file_paths,
        total_files=2,
        language=SupportedLanguage.PY,
        progress_display=progress_display,
    )

    context_meta = result[FileCategory.CONTEXT][0]
    assert context_meta.file_path == Path("README.md")
    assert context_meta.category == FileCategory.CONTEXT
    assert context_meta.score == 1000  # Root-level context file

    signal_meta = result[FileCategory.SIGNAL][0]
    assert signal_meta.file_path == Path("main.py")
    assert signal_meta.category == FileCategory.SIGNAL
    assert signal_meta.score == 60  # Root-level signal file


@pytest.mark.unit
def test_different_languages_use_different_heuristics(progress_display):
    """Language parameter determines which heuristics are used for categorization."""
    # Test with files that could match different languages
    file_paths = [Path("main.py"), Path("main.go")]

    py_result = categorize_files(
        file_paths,
        total_files=2,
        language=SupportedLanguage.PY,
        progress_display=progress_display,
    )

    go_result = categorize_files(
        file_paths,
        total_files=2,
        language=SupportedLanguage.GO,
        progress_display=progress_display,
    )

    # main.py is a signal for Python
    assert len(py_result[FileCategory.SIGNAL]) == 1
    assert py_result[FileCategory.SIGNAL][0].file_path == Path("main.py")
    # main.go is not recognized as a Python source file
    assert len(py_result[FileCategory.SOURCE]) == 0

    # main.go is both a manifest and signal for Go (manifest takes precedence)
    assert len(go_result[FileCategory.MANIFEST]) == 1
    assert go_result[FileCategory.MANIFEST][0].file_path == Path("main.go")
    # main.py is not recognized as a Go source file
    assert len(go_result[FileCategory.SOURCE]) == 0
