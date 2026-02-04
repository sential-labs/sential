"""
Comprehensive tests for the tokens module using pytest.

Tests cover:
- TokenLimits: default values and custom initialization
- TiktokenCounter: initialization with different models, fallback behavior, token counting
- PooledTokenBudget: budget allocation, spending, and affordability checks
"""

import pytest

from core.tokens import TokenLimits, TiktokenCounter, PooledTokenBudget
from core.models import FileCategory


# ============================================================================
# Tests for TokenLimits
# ============================================================================


@pytest.mark.unit
def test_token_limits_default_values():
    """TokenLimits should have correct default values."""
    limits = TokenLimits()
    
    assert limits.max_total == 200_000
    assert FileCategory.CONTEXT in limits.ratios
    assert FileCategory.MANIFEST in limits.ratios
    assert FileCategory.SIGNAL in limits.ratios
    assert FileCategory.SOURCE in limits.ratios
    assert limits.ratios[FileCategory.CONTEXT] == 0.1
    assert limits.ratios[FileCategory.MANIFEST] == 0.05
    assert limits.ratios[FileCategory.SIGNAL] == 0.05
    assert limits.ratios[FileCategory.SOURCE] == 0.4


@pytest.mark.unit
def test_token_limits_custom_max_total():
    """TokenLimits should accept custom max_total."""
    limits = TokenLimits(max_total=100_000)
    
    assert limits.max_total == 100_000
    assert limits.ratios[FileCategory.CONTEXT] == 0.1  # Default ratios preserved


@pytest.mark.unit
def test_token_limits_custom_ratios():
    """TokenLimits should accept custom ratios."""
    custom_ratios = {
        FileCategory.CONTEXT: 0.2,
        FileCategory.MANIFEST: 0.1,
        FileCategory.SIGNAL: 0.1,
        FileCategory.SOURCE: 0.5,
    }
    limits = TokenLimits(ratios=custom_ratios)
    
    assert limits.max_total == 200_000  # Default max_total preserved
    assert limits.ratios[FileCategory.CONTEXT] == 0.2
    assert limits.ratios[FileCategory.MANIFEST] == 0.1
    assert limits.ratios[FileCategory.SIGNAL] == 0.1
    assert limits.ratios[FileCategory.SOURCE] == 0.5


@pytest.mark.unit
def test_token_limits_immutable():
    """TokenLimits should be immutable (frozen dataclass)."""
    from dataclasses import FrozenInstanceError
    
    limits = TokenLimits()
    
    with pytest.raises(FrozenInstanceError):
        limits.max_total = 300_000


# ============================================================================
# Tests for TiktokenCounter
# ============================================================================


@pytest.mark.unit
def test_tiktoken_counter_default_model():
    """TiktokenCounter should initialize with default model 'gpt-4o'."""
    counter = TiktokenCounter()
    
    assert counter.encoder is not None
    # Verify it can count tokens
    assert counter.count("hello world") > 0


@pytest.mark.unit
def test_tiktoken_counter_specific_model():
    """TiktokenCounter should initialize with specified model."""
    counter = TiktokenCounter(model_name="gpt-4")
    
    assert counter.encoder is not None
    assert counter.count("test") > 0


@pytest.mark.unit
def test_tiktoken_counter_unknown_model_fallback():
    """TiktokenCounter should fall back to cl100k_base for unknown models."""
    counter = TiktokenCounter(model_name="unknown-model-xyz")
    
    assert counter.encoder is not None
    # Should still work with fallback encoding
    assert counter.count("test") > 0
    # Verify it's using cl100k_base by checking encoding name
    assert counter.encoder.name == "cl100k_base"


@pytest.mark.unit
def test_tiktoken_counter_count_none():
    """TiktokenCounter.count should return 0 for None input."""
    counter = TiktokenCounter()
    
    assert counter.count(None) == 0


@pytest.mark.unit
def test_tiktoken_counter_count_empty_string():
    """TiktokenCounter.count should return 0 for empty string."""
    counter = TiktokenCounter()
    
    assert counter.count("") == 0


@pytest.mark.unit
def test_tiktoken_counter_count_simple_text():
    """TiktokenCounter.count should return correct token count for simple text."""
    counter = TiktokenCounter()
    
    # Simple text should have positive token count
    count = counter.count("hello world")
    assert count > 0
    assert isinstance(count, int)


@pytest.mark.unit
def test_tiktoken_counter_count_multiline_text():
    """TiktokenCounter.count should handle multiline text correctly."""
    counter = TiktokenCounter()
    
    text = "line 1\nline 2\nline 3"
    count = counter.count(text)
    assert count > 0


@pytest.mark.unit
def test_tiktoken_counter_count_unicode():
    """TiktokenCounter.count should handle unicode characters."""
    counter = TiktokenCounter()
    
    text = "Hello 世界 🌍"
    count = counter.count(text)
    assert count > 0


@pytest.mark.unit
def test_tiktoken_counter_count_large_text():
    """TiktokenCounter.count should handle large text."""
    counter = TiktokenCounter()
    
    text = "word " * 1000
    count = counter.count(text)
    assert count > 0
    # Should be roughly proportional to input size
    assert count > 100


@pytest.mark.unit
def test_tiktoken_counter_count_consistency():
    """TiktokenCounter.count should return consistent results for same input."""
    counter = TiktokenCounter()
    
    text = "consistent test text"
    count1 = counter.count(text)
    count2 = counter.count(text)
    
    assert count1 == count2


@pytest.mark.unit
def test_tiktoken_counter_different_models_different_counts():
    """Different models may produce different token counts."""
    counter1 = TiktokenCounter(model_name="gpt-4o")
    counter2 = TiktokenCounter(model_name="gpt-3.5-turbo")
    
    text = "hello world"
    count1 = counter1.count(text)
    count2 = counter2.count(text)
    
    # Both should return valid counts (may or may not be equal)
    assert count1 > 0
    assert count2 > 0


# ============================================================================
# Tests for PooledTokenBudget
# ============================================================================


@pytest.mark.unit
def test_pooled_token_budget_initialization_default_limits():
    """PooledTokenBudget should initialize with default TokenLimits."""
    budget = PooledTokenBudget(TokenLimits())
    
    assert budget.limits.max_total == 200_000
    assert budget.pool == 0
    assert FileCategory.CONTEXT in budget.initial_allocations
    assert FileCategory.MANIFEST in budget.initial_allocations
    assert FileCategory.SIGNAL in budget.initial_allocations
    assert FileCategory.SOURCE in budget.initial_allocations


@pytest.mark.unit
def test_pooled_token_budget_initial_allocations():
    """PooledTokenBudget should compute correct initial allocations from ratios."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    # Verify allocations are computed correctly
    assert budget.initial_allocations[FileCategory.CONTEXT] == 10_000  # 0.1 * 100_000
    assert budget.initial_allocations[FileCategory.MANIFEST] == 5_000  # 0.05 * 100_000
    assert budget.initial_allocations[FileCategory.SIGNAL] == 5_000  # 0.05 * 100_000
    assert budget.initial_allocations[FileCategory.SOURCE] == 40_000  # 0.4 * 100_000


@pytest.mark.unit
def test_pooled_token_budget_start_category_adds_to_pool():
    """start_category should add category's allocation to the pool."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    assert budget.pool == 0
    
    budget.start_category(FileCategory.CONTEXT)
    assert budget.pool == 10_000  # 0.1 * 100_000
    
    budget.start_category(FileCategory.MANIFEST)
    assert budget.pool == 15_000  # 10_000 + 5_000


@pytest.mark.unit
def test_pooled_token_budget_start_category_unknown_category():
    """start_category with unknown category should add 0 to pool."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    initial_pool = budget.pool
    budget.start_category(FileCategory.UNKNOWN)
    
    # UNKNOWN is not in ratios, so should add 0
    assert budget.pool == initial_pool


@pytest.mark.unit
def test_pooled_token_budget_start_category_multiple_times():
    """start_category can be called multiple times, accumulating allocations."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    budget.start_category(FileCategory.CONTEXT)
    assert budget.pool == 10_000
    
    budget.start_category(FileCategory.CONTEXT)
    assert budget.pool == 20_000  # Accumulates


@pytest.mark.unit
def test_pooled_token_budget_can_afford_sufficient_pool():
    """can_afford should return True when pool has enough tokens."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    budget.start_category(FileCategory.CONTEXT)
    assert budget.pool == 10_000
    
    assert budget.can_afford(5_000) is True
    assert budget.can_afford(10_000) is True  # Exactly equal


@pytest.mark.unit
def test_pooled_token_budget_can_afford_insufficient_pool():
    """can_afford should return False when pool doesn't have enough tokens."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    budget.start_category(FileCategory.CONTEXT)
    assert budget.pool == 10_000
    
    assert budget.can_afford(10_001) is False
    assert budget.can_afford(50_000) is False


@pytest.mark.unit
def test_pooled_token_budget_can_afford_empty_pool():
    """can_afford should return False when pool is empty."""
    budget = PooledTokenBudget(TokenLimits())
    
    assert budget.pool == 0
    assert budget.can_afford(1) is False
    assert budget.can_afford(0) is True  # Can afford 0 tokens


@pytest.mark.unit
def test_pooled_token_budget_spend_reduces_pool():
    """spend should reduce the pool by the specified amount."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    budget.start_category(FileCategory.CONTEXT)
    assert budget.pool == 10_000
    
    budget.spend(3_000)
    assert budget.pool == 7_000
    
    budget.spend(2_000)
    assert budget.pool == 5_000


@pytest.mark.unit
def test_pooled_token_budget_spend_multiple_times():
    """spend can be called multiple times, reducing pool each time."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    budget.start_category(FileCategory.SOURCE)
    assert budget.pool == 40_000
    
    budget.spend(10_000)
    assert budget.pool == 30_000
    
    budget.spend(15_000)
    assert budget.pool == 15_000
    
    budget.spend(5_000)
    assert budget.pool == 10_000


@pytest.mark.unit
def test_pooled_token_budget_spend_zero():
    """spend(0) should not change the pool."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    budget.start_category(FileCategory.CONTEXT)
    initial_pool = budget.pool
    
    budget.spend(0)
    assert budget.pool == initial_pool


@pytest.mark.unit
def test_pooled_token_budget_integration_workflow():
    """Integration test: complete workflow of start_category, can_afford, and spend."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    # Start with CONTEXT category
    budget.start_category(FileCategory.CONTEXT)
    assert budget.pool == 10_000
    assert budget.can_afford(5_000) is True
    
    # Spend some tokens
    budget.spend(3_000)
    assert budget.pool == 7_000
    assert budget.can_afford(5_000) is True
    assert budget.can_afford(8_000) is False
    
    # Start another category
    budget.start_category(FileCategory.MANIFEST)
    assert budget.pool == 12_000  # 7_000 + 5_000
    
    # Spend more
    budget.spend(10_000)
    assert budget.pool == 2_000
    assert budget.can_afford(2_000) is True
    assert budget.can_afford(2_001) is False


@pytest.mark.unit
def test_pooled_token_budget_all_categories():
    """Test starting all categories and spending from combined pool."""
    limits = TokenLimits(max_total=100_000)
    budget = PooledTokenBudget(limits)
    
    # Start all categories
    budget.start_category(FileCategory.CONTEXT)
    budget.start_category(FileCategory.MANIFEST)
    budget.start_category(FileCategory.SIGNAL)
    budget.start_category(FileCategory.SOURCE)
    
    # Total should be sum of all allocations
    expected_total = (
        10_000 +  # CONTEXT: 0.1 * 100_000
        5_000 +   # MANIFEST: 0.05 * 100_000
        5_000 +   # SIGNAL: 0.05 * 100_000
        40_000    # SOURCE: 0.4 * 100_000
    )
    assert budget.pool == expected_total
    
    # Should be able to afford total
    assert budget.can_afford(expected_total) is True
    assert budget.can_afford(expected_total + 1) is False
    
    # Spend all
    budget.spend(expected_total)
    assert budget.pool == 0
    assert budget.can_afford(1) is False
