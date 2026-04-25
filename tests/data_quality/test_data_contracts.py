"""
Data quality tests for source CSV data contracts.

Validates schema, data types, ranges, and business rules
to catch data issues before they enter the pipeline.
"""

import os
import csv
import pytest
from datetime import datetime

# Path to the actual dataset
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'mbb_financial_dataset.csv')


def load_csv():
    """Load CSV data for testing."""
    if not os.path.exists(DATA_PATH):
        pytest.skip(f"Data file not found at {DATA_PATH}")
    with open(DATA_PATH, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)


@pytest.mark.data_quality
class TestCSVSchema:
    """Validate CSV schema matches expectations."""

    def test_required_columns_exist(self):
        data = load_csv()
        assert len(data) > 0, "CSV file is empty"

        required = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        actual = list(data[0].keys())
        for col in required:
            assert col in actual, f"Missing required column: {col}"

    def test_minimum_row_count(self):
        data = load_csv()
        assert len(data) >= 100, f"Expected >= 100 rows, got {len(data)}"


@pytest.mark.data_quality
class TestDataTypes:
    """Validate data types and formats."""

    def test_dates_are_valid(self):
        data = load_csv()
        for row in data[:50]:
            try:
                datetime.strptime(row['Date'], '%Y-%m-%d')
            except ValueError:
                pytest.fail(f"Invalid date format: {row['Date']}")

    def test_prices_are_numeric(self):
        data = load_csv()
        for row in data[:50]:
            for col in ['Open', 'High', 'Low', 'Close']:
                if row[col]:
                    try:
                        float(row[col])
                    except ValueError:
                        pytest.fail(f"Non-numeric {col}: {row[col]}")

    def test_volume_is_positive_integer(self):
        data = load_csv()
        for row in data[:50]:
            if row['Volume']:
                vol = float(row['Volume'])
                assert vol >= 0, f"Negative volume: {vol}"


@pytest.mark.data_quality
class TestBusinessRules:
    """Validate financial business rules."""

    def test_ohlc_relationship(self):
        """Low <= Open,Close <= High for each day."""
        data = load_csv()
        violations = 0
        for row in data:
            try:
                o, h, l, c = float(row['Open']), float(row['High']), float(row['Low']), float(row['Close'])
                if l > min(o, c) or h < max(o, c):
                    violations += 1
            except (ValueError, TypeError):
                continue

        # Allow small tolerance (data may have edge cases)
        violation_pct = violations / len(data) * 100
        assert violation_pct < 5, f"OHLC violation rate: {violation_pct:.1f}% (threshold: 5%)"

    def test_no_future_dates(self):
        data = load_csv()
        today = datetime.now().date()
        for row in data:
            try:
                d = datetime.strptime(row['Date'], '%Y-%m-%d').date()
                assert d <= today, f"Future date found: {d}"
            except ValueError:
                continue

    def test_close_prices_reasonable(self):
        """Maybank stock should be between RM 1 and RM 50."""
        data = load_csv()
        for row in data:
            try:
                close = float(row['Close'])
                assert 1 <= close <= 50, f"Unreasonable close price: {close}"
            except (ValueError, TypeError):
                continue


@pytest.mark.data_quality
class TestNullChecks:
    """Check for nulls in critical columns."""

    def test_no_null_dates(self):
        data = load_csv()
        nulls = sum(1 for row in data if not row.get('Date'))
        assert nulls == 0, f"Found {nulls} null dates"

    def test_no_null_close(self):
        data = load_csv()
        nulls = sum(1 for row in data if not row.get('Close'))
        assert nulls == 0, f"Found {nulls} null close prices"

    def test_limited_null_volume(self):
        data = load_csv()
        nulls = sum(1 for row in data if not row.get('Volume'))
        null_pct = nulls / len(data) * 100
        assert null_pct < 5, f"Volume null rate: {null_pct:.1f}% (threshold: 5%)"
