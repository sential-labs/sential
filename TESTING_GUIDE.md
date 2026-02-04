# Testing Guide: Writing Testable Code and Tests

This guide documents the testing conventions, patterns, and best practices used in the Sential codebase. It serves as a reference for writing new code that is testable and for writing tests that follow established conventions.

## Table of Contents

1. [Design Principles for Testability](#design-principles-for-testability)
2. [Protocol-Based Dependency Injection](#protocol-based-dependency-injection)
3. [Mock and No-Op Implementations](#mock-and-no-op-implementations)
4. [Test Organization and Structure](#test-organization-and-structure)
5. [Fixtures and Test Data](#fixtures-and-test-data)
6. [Writing Tests](#writing-tests)
7. [Common Patterns](#common-patterns)
8. [Best Practices](#best-practices)

---

## Design Principles for Testability

### 1. Dependency Injection

**Principle**: External dependencies (I/O, subprocess, UI, token counting) should be injected rather than hardcoded.

**Why**: Allows tests to replace dependencies with mocks or no-op implementations.

**Example**:
```python
# ✅ Good: Accepts dependencies as parameters
def extract_ctags_for_source_files(
    root: Path,
    files: list[FileMetadata],
    counter: TokenCounter,  # Injected
    token_budget: TokenBudget,  # Injected
    status: CategoryProcessedFiles,
    progress_display: ProgressDisplay | None = None,  # Optional, injectable
) -> None:
    ...

# ❌ Bad: Hardcoded dependencies
def extract_ctags_for_source_files(root: Path, files: list[FileMetadata]) -> None:
    counter = TiktokenCounter()  # Hardcoded - can't test without tiktoken
    budget = PooledTokenBudget(...)  # Hardcoded - can't control behavior
    ...
```

### 2. Protocol-Based Interfaces

**Principle**: Use `Protocol` classes to define interfaces, allowing multiple implementations (production, test, mock).

**Why**: 
- Enables dependency injection without tight coupling
- Makes it clear what methods are required
- Allows easy swapping of implementations

**Example**:
```python
from typing import Protocol

class TokenCounter(Protocol):
    """Protocol for counting tokens in text."""
    def count(self, text: str | None) -> int:
        """Count tokens in the given text."""

# Production implementation
class TiktokenCounter:
    def count(self, text: str | None) -> int:
        ...

# Test implementation
class NoOpTokenCounter:
    def count(self, text: str | None) -> int:
        return 100  # Fixed value for testing
```

### 3. Optional UI/External Dependencies

**Principle**: UI components and external dependencies should be optional parameters with sensible defaults.

**Why**: Tests can pass no-op implementations, production code gets rich UI by default.

**Example**:
```python
def categorize_files(
    file_paths: list[Path],
    total_files: int,
    language: SupportedLanguage,
    progress_display: ProgressDisplay | None = None,  # Optional
) -> dict[FileCategory, list[FileMetadata]]:
    rich_progress_display = (
        progress_display if progress_display is not None else RichProgressDisplay()
    )
    # Use rich_progress_display...
```

### 4. Factory Functions for External Operations

**Principle**: Operations that create external resources (subprocess, file I/O) should accept factory functions.

**Why**: Tests can inject mock factories to control behavior.

**Example**:
```python
def _run_ctags(
    root: Path,
    files: list[FileMetadata],
    start: int = 0,
    popen_factory: Callable | None = None,  # Factory function
) -> tuple[list[ProcessedFile] | None, int]:
    popen = popen_factory if popen_factory else subprocess.Popen
    # Use popen...
```

---

## Protocol-Based Dependency Injection

### Creating Protocols

When creating a new dependency that needs to be testable:

1. **Define a Protocol**:
```python
from typing import Protocol

class MyDependency(Protocol):
    """Protocol for [description of what this dependency does]."""
    
    def method1(self, arg: str) -> int:
        """Description of what method1 does."""
    
    def method2(self) -> None:
        """Description of what method2 does."""
```

2. **Create Production Implementation**:
```python
class ProductionMyDependency:
    """Production implementation of MyDependency."""
    
    def method1(self, arg: str) -> int:
        # Real implementation
        ...
    
    def method2(self) -> None:
        # Real implementation
        ...
```

3. **Create No-Op Test Implementation**:
```python
class NoOpMyDependency:
    """No-op implementation of MyDependency for testing."""
    
    def method1(self, arg: str) -> int:
        return 0  # Or some sensible default
    
    def method2(self) -> None:
        pass  # Do nothing
```

4. **Create Mock Implementation (if call tracking needed)**:
```python
class MockMyDependency:
    """Mock implementation that tracks calls for testing."""
    
    def __init__(self):
        self.method1_calls: list[str] = []
        self.method2_calls: list[None] = []
    
    def method1(self, arg: str) -> int:
        self.method1_calls.append(arg)
        return 42  # Or configurable return value
    
    def method2(self) -> None:
        self.method2_calls.append(None)
```

### Using Protocols in Functions

```python
def my_function(
    dependency: MyDependency,  # Use Protocol type
    other_args: str,
) -> int:
    result = dependency.method1(other_args)
    dependency.method2()
    return result
```

---

## Mock and No-Op Implementations

### No-Op Implementations

**Use when**: You need a dependency that does nothing and returns sensible defaults.

**Characteristics**:
- Simple, minimal implementation
- Returns fixed or configurable values
- No side effects
- No call tracking

**Example**: `NoOpTokenCounter`, `NoOpProgressDisplay`

```python
class NoOpTokenCounter:
    """No-op implementation of TokenCounter for testing."""
    
    def __init__(self, return_value: int | None = None):
        self.return_value = return_value
    
    def count(self, text: str | None) -> int:
        if self.return_value is not None:
            return self.return_value
        return 0
```

### Mock Implementations

**Use when**: You need to verify that methods were called with specific arguments.

**Characteristics**:
- Tracks all method calls
- Stores arguments for verification
- May have configurable return values
- Allows test assertions on interactions

**Example**: `MockTokenBudget`, `TrackingProgressDisplay`

```python
class MockTokenBudget:
    """Mock implementation of TokenBudget for testing."""
    
    def __init__(self, can_afford_return: bool | None = None):
        self.can_afford_return = can_afford_return
        # Track calls for verification
        self.start_category_calls: list[FileCategory] = []
        self.can_afford_calls: list[int] = []
        self.spend_calls: list[int] = []
    
    def start_category(self, category: FileCategory) -> None:
        self.start_category_calls.append(category)
    
    def can_afford(self, count: int) -> bool:
        self.can_afford_calls.append(count)
        if self.can_afford_return is not None:
            return self.can_afford_return
        return True
    
    def spend(self, count: int) -> None:
        self.spend_calls.append(count)
```

### Factory Functions for External Operations

**Use when**: You need to mock subprocess, file I/O, or other external operations.

**Pattern**:
```python
def my_function(
    popen_factory: Callable | None = None,
) -> Result:
    factory = popen_factory if popen_factory else subprocess.Popen
    with factory(...) as process:
        # Use process...
```

**Test Usage**:
```python
def mock_popen_factory(stdout_lines):
    def _factory(*_args, **_kwargs):
        mock_process = MagicMock()
        mock_process.stdout = iter(stdout_lines)
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=None)
        return mock_process
    return _factory

# In test:
mock_popen = mock_popen_factory(['line1\n', 'line2\n'])
result = my_function(popen_factory=mock_popen)
```

---

## Test Organization and Structure

### File Organization

- Tests live in `tests/` directory mirroring source structure
- `tests/core/test_<module>.py` tests `core/<module>.py`
- Shared fixtures in `tests/core/conftest.py`

### Test File Structure

```python
"""
Comprehensive tests for the <module> module using pytest.

Tests cover:
- function1: description of what's tested
- function2: description of what's tested
- ...
"""

from pathlib import Path
import pytest

from core.module import function1, function2
from core.models import FileCategory

# ============================================================================
# Tests for function1
# ============================================================================

@pytest.mark.unit
def test_function1_basic_case():
    """Basic functionality should work correctly."""
    ...

@pytest.mark.unit
@pytest.mark.parametrize("input,expected", [...])
def test_function1_multiple_cases(input, expected):
    """Should handle various inputs correctly."""
    ...

# ============================================================================
# Tests for function2
# ============================================================================

@pytest.mark.unit
def test_function2_edge_case():
    """Edge cases should be handled correctly."""
    ...
```

### Test Markers

Use pytest markers to categorize tests:

- `@pytest.mark.unit`: Unit tests (fast, isolated)
- `@pytest.mark.mock`: Tests that use mocks
- `@pytest.mark.integration`: Integration tests (slower, may use real dependencies)

### Section Headers

Use clear section headers with `===` to organize tests by function:

```python
# ============================================================================
# Tests for calculate_significance - Universal Context Files
# ============================================================================
```

---

## Fixtures and Test Data

### Shared Fixtures in conftest.py

**Location**: `tests/core/conftest.py`

**Purpose**: Provide reusable test objects, factories, and mocks for all tests in the module.

**Common Fixtures**:

1. **Project Root**:
```python
@pytest.fixture
def project_root(tmp_path):
    """Create a temporary project root for testing."""
    return tmp_path / "project"
```

2. **Sample Data Objects**:
```python
@pytest.fixture
def sample_file_metadata():
    """Sample FileMetadata for testing."""
    return FileMetadata(Path("file.py"), FileCategory.SOURCE)
```

3. **Mock Factories**:
```python
@pytest.fixture
def mock_popen_factory():
    """Factory for creating mock Popen instances."""
    def _factory(stdout_lines):
        def mock_popen(*_args, **_kwargs):
            mock_process = MagicMock()
            mock_process.stdout = iter(stdout_lines)
            mock_process.__enter__ = MagicMock(return_value=mock_process)
            mock_process.__exit__ = MagicMock(return_value=None)
            return mock_process
        return mock_popen
    return _factory
```

4. **No-Op Dependencies**:
```python
@pytest.fixture
def token_counter():
    """Token counter for testing."""
    return NoOpTokenCounter(return_value=100)

@pytest.fixture
def progress_display():
    """Progress display for testing."""
    return NoOpProgressDisplay()
```

5. **Mock Dependencies**:
```python
@pytest.fixture
def token_budget():
    """Token budget for testing."""
    return MockTokenBudget(can_afford_return=True)
```

6. **Factory Fixtures**:
```python
@pytest.fixture
def processed_file_factory():
    """Factory for creating ProcessedFile instances."""
    def _factory(path="file.py", content="function foo"):
        return ProcessedFile(path, FileCategory.SOURCE.value, content)
    return _factory
```

### Using Fixtures in Tests

```python
def test_my_function(
    project_root,  # Use fixture
    sample_file_metadata,  # Use fixture
    token_counter,  # Use fixture
    progress_display,  # Use fixture
):
    result = my_function(
        root=project_root,
        file=sample_file_metadata,
        counter=token_counter,
        progress=progress_display,
    )
    assert result is not None
```

---

## Writing Tests

### Test Function Naming

**Pattern**: `test_<function_name>_<scenario>`

**Examples**:
- `test_calculate_significance_readme_files`
- `test_extract_ctags_successful_single_batch`
- `test_parse_tag_line_invalid`

### Test Documentation

Every test should have a docstring describing what it tests:

```python
def test_calculate_significance_readme_files(path, language):
    """README files should score 1000 at root level (no depth penalty)."""
    assert calculate_significance(Path(path), language).score == 1000
```

### Parametrization

Use `@pytest.mark.parametrize` for testing multiple similar cases:

```python
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
```

### Testing Success Paths

```python
@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_successful_single_batch(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Should extract tags and process files successfully."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    assert len(category_status.files) == 1
    assert category_status.files[0].path == "file.py"
```

### Testing Error Paths

```python
@pytest.mark.unit
@pytest.mark.mock
def test_run_ctags_subprocess_error(project_root, sample_file_metadata):
    """OSError/SubprocessError should return (None, current_index)."""
    files = [sample_file_metadata]

    def mock_popen(*_args, **_kwargs):
        raise OSError("Subprocess failed")

    result, next_index = _run_ctags(
        root=project_root,
        files=files,
        start=0,
        popen_factory=mock_popen,
    )

    assert result is None
    assert next_index == 0
```

### Testing Edge Cases

```python
@pytest.mark.unit
def test_empty_path():
    """Empty path should still work."""
    meta = calculate_significance(Path(""), SupportedLanguage.PY)
    assert meta.score == 0
```

### Testing Integration

```python
@pytest.mark.unit
def test_progress_display_integration(tracking_progress_display):
    """Progress display should be called during processing."""
    file_paths = [Path(f"file{i}.py") for i in range(20)]

    categorize_files(
        file_paths,
        total_files=20,
        language=SupportedLanguage.PY,
        progress_display=tracking_progress_display,
    )

    # Verify calls were made
    assert any(call[0] == "start" for call in tracking_progress_display.calls)
    assert any(call[0] == "update" for call in tracking_progress_display.calls)
    assert any(call[0] == "complete" for call in tracking_progress_display.calls)
```

### Verifying Mock Interactions

```python
@pytest.mark.unit
@pytest.mark.mock
def test_extract_ctags_token_budget_start_category(
    project_root,
    sample_file_metadata,
    token_counter,
    token_budget,
    category_status,
    processed_file_factory,
    progress_display,
    mocker,
):
    """Budget start_category should be called with SOURCE."""
    files = [sample_file_metadata]
    processed_file = processed_file_factory()

    mock_run = mocker.patch("core.ctags_extraction._run_ctags")
    mock_run.return_value = ([processed_file], 1)

    extract_ctags_for_source_files(
        root=project_root,
        files=files,
        counter=token_counter,
        token_budget=token_budget,
        status=category_status,
        progress_display=progress_display,
    )

    # Verify mock was called correctly
    assert len(token_budget.start_category_calls) == 1
    assert token_budget.start_category_calls[0] == FileCategory.SOURCE
```

---

## Common Patterns

### Pattern 1: Testing with Mocks (pytest-mock)

```python
@pytest.mark.unit
@pytest.mark.mock
def test_my_function(mocker):
    """Test using mocker fixture from pytest-mock."""
    mock_dependency = mocker.patch("module.dependency")
    mock_dependency.return_value = expected_value
    
    result = my_function()
    
    assert result == expected_result
    mock_dependency.assert_called_once()
```

### Pattern 2: Testing with Factory Functions

```python
@pytest.mark.unit
@pytest.mark.mock
def test_my_function_with_factory(mock_popen_factory):
    """Test using factory function for subprocess."""
    stdout_lines = ['line1\n', 'line2\n']
    mock_popen = mock_popen_factory(stdout_lines)
    
    result = my_function(popen_factory=mock_popen)
    
    assert result is not None
```

### Pattern 3: Testing Multiple Batches/Iterations

```python
@pytest.mark.unit
@pytest.mark.mock
def test_multiple_batches(mocker):
    """Multiple batches should call function multiple times."""
    mock_run = mocker.patch("module._run_internal")
    mock_run.side_effect = [
        (result1, 1),
        (result2, 2),
    ]
    
    my_function(...)
    
    assert mock_run.call_count == 2
```

### Pattern 4: Testing Error Handling

```python
@pytest.mark.unit
def test_error_handling():
    """Should handle errors gracefully."""
    def failing_operation():
        raise ValueError("Operation failed")
    
    with pytest.raises(ValueError, match="Operation failed"):
        failing_operation()
```

### Pattern 5: Testing Context Managers

```python
@pytest.mark.unit
def test_context_manager():
    """Context manager should work correctly."""
    with MyContextManager() as cm:
        assert cm.is_active()
    # Verify cleanup happened
    assert not cm.is_active()
```

---

## Best Practices

### 1. Test Isolation

- Each test should be independent
- Don't rely on test execution order
- Use fixtures for setup/teardown
- Don't modify shared state

### 2. Test Coverage

- Test success paths
- Test error paths
- Test edge cases (empty inputs, None values, boundary conditions)
- Test integration between components

### 3. Test Readability

- Use descriptive test names
- Include docstrings explaining what's tested
- Use clear variable names
- Group related tests with section headers

### 4. Test Performance

- Keep unit tests fast (< 1 second each)
- Use mocks for slow operations (network, file I/O, subprocess)
- Mark slow tests appropriately (`@pytest.mark.slow`)

### 5. Test Maintainability

- Use fixtures for common setup
- Use parametrization for similar test cases
- Keep tests DRY (Don't Repeat Yourself)
- Update tests when code changes

### 6. Assertions

- Use specific assertions (not just `assert result`)
- Verify both return values and side effects
- Check mock call counts and arguments
- Use appropriate assertion messages

### 7. Code Design for Testing

- Keep functions small and focused
- Prefer pure functions (no side effects)
- Use dependency injection
- Separate business logic from I/O

### 8. Documentation

- Document test purpose in docstrings
- Explain complex test setups
- Comment on why certain mocks are needed
- Document expected behavior in assertions

---

## Summary Checklist

When writing new code, ensure:

- [ ] Dependencies are injected (not hardcoded)
- [ ] Protocols are defined for testable interfaces
- [ ] No-op implementations exist for testing
- [ ] Factory functions are used for external operations
- [ ] Optional parameters have sensible defaults

When writing new tests, ensure:

- [ ] Tests are organized by function with section headers
- [ ] Tests have descriptive names and docstrings
- [ ] Parametrization is used for similar cases
- [ ] Fixtures are used for common setup
- [ ] Both success and error paths are tested
- [ ] Edge cases are covered
- [ ] Mock interactions are verified
- [ ] Tests are fast and isolated

---

## Examples Reference

For concrete examples, see:

- **Fixtures**: `tests/core/conftest.py`
- **Unit Tests**: `tests/core/test_categorization.py`
- **Mock Tests**: `tests/core/test_ctags_extraction.py`
- **Protocols**: `core/tokens.py`, `ui/progress_display.py`
- **No-Op Implementations**: `core/tokens.py`, `ui/progress_display.py`
- **Mock Implementations**: `core/tokens.py`, `tests/core/conftest.py`
