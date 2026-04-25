"""
Unit tests for the MarketProducer streaming class.
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'streaming'))


@pytest.mark.unit
class TestMarketProducer:
    """Test MarketProducer class."""

    @patch.dict(os.environ, {
        'KAFKA_BROKER': 'localhost:9092',
        'KAFKA_TOPIC': 'test-topic',
        'TICKERS': 'TEST.KL',
        'FINNHUB_API_KEY': '',
    })
    def test_simulation_mode_when_no_key(self):
        from producer import MarketProducer
        producer = MarketProducer()
        assert producer.use_simulation is True

    @patch.dict(os.environ, {
        'KAFKA_BROKER': 'localhost:9092',
        'KAFKA_TOPIC': 'test-topic',
        'TICKERS': 'TEST.KL',
        'FINNHUB_API_KEY': 'real_key_123',
    })
    def test_live_mode_with_key(self):
        from producer import MarketProducer
        producer = MarketProducer()
        assert producer.use_simulation is False

    @patch.dict(os.environ, {
        'KAFKA_BROKER': 'localhost:9092',
        'KAFKA_TOPIC': 'test-topic',
        'TICKERS': '1155.KL,BINANCE:BTCUSDT',
        'FINNHUB_API_KEY': '',
    })
    def test_tickers_parsed(self):
        from producer import MarketProducer
        producer = MarketProducer()
        assert len(producer.tickers) == 2
        assert '1155.KL' in producer.tickers

    @patch.dict(os.environ, {
        'KAFKA_BROKER': 'localhost:9092',
        'KAFKA_TOPIC': 'test-topic',
        'TICKERS': 'TEST.KL',
        'FINNHUB_API_KEY': 'your_finnhub_api_key_here',
    })
    def test_placeholder_key_triggers_simulation(self):
        from producer import MarketProducer
        producer = MarketProducer()
        assert producer.use_simulation is True

    @patch.dict(os.environ, {
        'KAFKA_BROKER': 'localhost:9092',
        'KAFKA_TOPIC': 'test-topic',
        'TICKERS': 'TEST.KL',
        'FINNHUB_API_KEY': '',
    })
    def test_kafka_producer_retry_on_failure(self):
        from producer import MarketProducer
        producer = MarketProducer()

        with pytest.raises(ConnectionError):
            producer._create_kafka_producer(max_retries=1)
