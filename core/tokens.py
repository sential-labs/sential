"""
Token counting and budget management for file extraction.

This module provides token counting implementations and budget management
for controlling token usage across different file categories during extraction.
It includes production implementations using tiktoken, test mocks, and protocols
for dependency injection.
"""

from dataclasses import dataclass, field
from typing import Callable, Protocol
import tiktoken

from core.models import FileCategory


@dataclass(frozen=True)
class TokenLimits:
    """Immutable policy defining the maximum allowed tokens per category."""

    max_total: int = 200_000
    ratios: dict[FileCategory, float] = field(
        default_factory=lambda: {
            FileCategory.CONTEXT: 0.1,
            FileCategory.MANIFEST: 0.05,
            FileCategory.SIGNAL: 0.05,
            FileCategory.SOURCE: 0.4,
        }
    )


class TokenCounter(Protocol):
    """Protocol for counting tokens in text."""

    def count(self, text: str | None) -> int:
        """Count tokens in the given text."""


class TiktokenCounter:
    """
    Production implementation of TokenCounter using tiktoken.

    Uses tiktoken to count tokens for a specific model. Falls back to
    cl100k_base encoding if the model name is not recognized.
    """

    def __init__(self, model_name: str = "gpt-4o"):
        """
        Initialize the token counter for the specified model.

        Args:
            model_name: The model name to use for token encoding. Defaults to "gpt-4o".
                If the model is not recognized, falls back to cl100k_base encoding.
        """
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str | None) -> int:
        """
        Count tokens in the given text.

        Args:
            text: The text to count tokens for. If None or empty, returns 0.

        Returns:
            The number of tokens in the text.
        """
        if not text:
            return 0
        return len(self.encoder.encode(text))


class NoOpTokenCounter:
    """
    No-op implementation of TokenCounter for testing.

    Returns configurable token counts, allowing tests to control token counting
    behavior without requiring tiktoken dependencies or actual token encoding.
    """

    def __init__(
        self,
        return_value: int | None = None,
        count_fn: Callable[[str | None], int] | None = None,
    ):
        """
        Initialize NoOpTokenCounter with configurable counting behavior.

        Args:
            return_value: If provided, always returns this value regardless of input.
                Takes precedence over count_fn if both are provided.
            count_fn: Optional callable that takes text and returns a token count.
                If return_value is None, this will be used. If both are None,
                defaults to returning 0.
        """
        self.return_value = return_value
        self.count_fn = count_fn

    def count(self, text: str | None) -> int:
        """Count tokens in the given text (returns configured value)."""
        if self.return_value is not None:
            return self.return_value
        if self.count_fn is not None:
            return self.count_fn(text)
        return 0


class TokenBudget(Protocol):
    """Protocol for managing token budgets."""

    def start_category(self, category: FileCategory) -> None:
        """Start processing a category, allocating budget."""

    def can_afford(self, count: int) -> bool:
        """Check if budget can afford the given token count."""

    def spend(self, count: int) -> None:
        """Spend tokens from the budget."""


class PooledTokenBudget:
    """
    Mutable state tracker for managing token budget during extraction.

    Maintains a pooled token budget that accumulates allocations as categories
    are processed. Budgets are allocated per category based on TokenLimits ratios,
    and tokens are spent from the pool as files are processed.
    """

    def __init__(self, limits: TokenLimits):
        """
        Initialize the pooled token budget with the given limits.

        Args:
            limits: TokenLimits instance defining max_total and category ratios.
                Initial allocations are computed from these ratios.
        """
        self.limits = limits
        self.pool = 0
        # Derived budgets
        self.initial_allocations: dict[FileCategory, int] = {
            cat: int(self.limits.max_total * ratio)
            for cat, ratio in limits.ratios.items()
        }

    def start_category(self, category: FileCategory) -> None:
        """
        Start processing a category, adding its allocated budget to the pool.

        Args:
            category: The file category being processed. The category's initial
                allocation (based on TokenLimits ratios) is added to the pool.
        """
        self.pool += self.initial_allocations.get(category, 0)

    def can_afford(self, count: int) -> bool:
        """
        Check if the current pool has enough tokens for the given count.

        Args:
            count: The number of tokens to check availability for.

        Returns:
            True if the pool has at least count tokens available, False otherwise.
        """
        return self.pool >= count

    def spend(self, count: int) -> None:
        """
        Spend tokens from the pool.

        Args:
            count: The number of tokens to spend. Should be checked with
                can_afford() before calling to avoid negative pool values.
        """
        self.pool -= count


class FixedTokenBudget:
    """
    A simple token budget with a fixed cap, resettable for each new "run"
    (e.g. per chapter). Use for limiting how much content is read in a single
    batch (e.g. chapter file content) so the total stays under context limits.
    """

    def __init__(self, max_tokens: int, ctx_ratio: float):
        """
        Initialize the budget with a cap.

        Args:
            max_tokens: Maximum tokens allowed for this run.
        """
        self.max = max_tokens
        self.ctx_ratio = ctx_ratio
        self.remaining = self.max * self.ctx_ratio

    def reset(
        self, max_tokens: int | None = None, ctx_ratio: float | None = None
    ) -> None:
        """
        Reset the budget. Optionally set a new cap and ratio.

        Args:
            max_tokens: If provided, set the cap to this value for future
                runs. If None, reset to the initial max_tokens from __init__.
            ctx_ratio: If provided, set the remaining value
        """
        if ctx_ratio:
            self.ctx_ratio = ctx_ratio
        if max_tokens:
            self.max = max_tokens
        self.remaining = self.max * self.ctx_ratio

    def can_afford(self, count: int) -> bool:
        """Return True if the remaining budget is at least count."""
        return self.remaining >= count

    def spend(self, count: int) -> None:
        """Decrease the remaining budget by count."""
        self.remaining -= count


class MockTokenBudget:
    """
    Mock implementation of TokenBudget for testing.

    Tracks all method calls and provides configurable behavior, allowing tests
    to verify budget interactions and control budget state without complex setup.
    """

    def __init__(
        self,
        can_afford_return: bool | None = None,
        can_afford_fn: Callable[[int], bool] | None = None,
    ):
        """
        Initialize MockTokenBudget with configurable behavior.

        Args:
            can_afford_return: If provided, always returns this value for can_afford().
                Takes precedence over can_afford_fn if both are provided.
            can_afford_fn: Optional callable that takes a count and returns bool.
                If can_afford_return is None, this will be used. If both are None,
                defaults to always returning True.

        Attributes (for test inspection):
            start_category_calls: List of categories passed to start_category()
            can_afford_calls: List of counts passed to can_afford()
            spend_calls: List of counts passed to spend()
        """
        self.can_afford_return = can_afford_return
        self.can_afford_fn = can_afford_fn

        # Track calls for test inspection
        self.start_category_calls: list[FileCategory] = []
        self.can_afford_calls: list[int] = []
        self.spend_calls: list[int] = []

    def start_category(self, category: FileCategory) -> None:
        """Start processing a category (tracks call)."""
        self.start_category_calls.append(category)

    def can_afford(self, count: int) -> bool:
        """Check if budget can afford the given token count (tracks call, returns configured value)."""
        self.can_afford_calls.append(count)
        if self.can_afford_return is not None:
            return self.can_afford_return
        if self.can_afford_fn is not None:
            return self.can_afford_fn(count)
        return True  # Default: always can afford

    def spend(self, count: int) -> None:
        """Spend tokens from the budget (tracks call)."""
        self.spend_calls.append(count)
