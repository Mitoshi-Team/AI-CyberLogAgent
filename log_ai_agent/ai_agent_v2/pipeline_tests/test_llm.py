#!/usr/bin/env python3
"""Tests for llm.py (LLM factory)."""

import pytest
from unittest.mock import patch, MagicMock

from log_ai_agent.ai_agent_v2.chains.llm import create_llm
from log_ai_agent.ai_agent_v2.config import LLMProvider


class TestCreateLLM:
    """Test create_llm factory function."""

    def test_create_llm_with_env_config(self):
        """Test that create_llm works with environment configuration."""
        with patch.dict("os.environ", {
            "OLLAMA_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "qwen2.5:7b",
            "LLM_TEMPERATURE": "0.3",
        }, clear=False):
            with patch("log_ai_agent.ai_agent_v2.chains.llm._create_llm_by_provider") as mock_create:
                mock_llm = MagicMock()
                mock_create.return_value = mock_llm

                result = create_llm()

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["provider"] == LLMProvider.OLLAMA
                assert call_kwargs["temperature"] == 0.3

    def test_create_llm_force_provider(self):
        """Test that create_llm respects forced provider."""
        with patch.dict("os.environ", {
            "OLLAMA_URL": "http://localhost:11434",
        }, clear=False):
            with patch("log_ai_agent.ai_agent_v2.chains.llm._create_llm_by_provider") as mock_create:
                mock_llm = MagicMock()
                mock_create.return_value = mock_llm

                result = create_llm(provider=LLMProvider.OLLAMA)

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["provider"] == LLMProvider.OLLAMA

    def test_create_llm_custom_temperature(self):
        """Test that create_llm accepts custom temperature."""
        with patch.dict("os.environ", {
            "OLLAMA_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "qwen2.5:7b",
        }, clear=False):
            with patch("log_ai_agent.ai_agent_v2.chains.llm._create_llm_by_provider") as mock_create:
                mock_llm = MagicMock()
                mock_create.return_value = mock_llm

                result = create_llm(temperature=0.9)

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["temperature"] == 0.9

    def test_create_llm_custom_max_tokens(self):
        """Test that create_llm accepts custom max_tokens."""
        with patch.dict("os.environ", {
            "OLLAMA_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "qwen2.5:7b",
        }, clear=False):
            with patch("log_ai_agent.ai_agent_v2.chains.llm._create_llm_by_provider") as mock_create:
                mock_llm = MagicMock()
                mock_create.return_value = mock_llm

                result = create_llm(max_tokens=8000)

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["max_tokens"] == 8000

    def test_create_llm_custom_timeout(self):
        """Test that create_llm accepts custom timeout."""
        with patch.dict("os.environ", {
            "OLLAMA_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "qwen2.5:7b",
        }, clear=False):
            with patch("log_ai_agent.ai_agent_v2.chains.llm._create_llm_by_provider") as mock_create:
                mock_llm = MagicMock()
                mock_create.return_value = mock_llm

                result = create_llm(timeout=120)

                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["timeout"] == 120

    def test_create_llm_returns_llm_instance(self):
        """Test that create_llm returns a LangChain model."""
        with patch.dict("os.environ", {
            "OLLAMA_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "qwen2.5:7b",
        }, clear=False):
            with patch("log_ai_agent.ai_agent_v2.chains.llm._create_llm_by_provider") as mock_create:
                mock_llm = MagicMock()
                mock_create.return_value = mock_llm

                result = create_llm()

                assert result is mock_llm

    def test_create_llm_no_provider_raises(self):
        """Test that create_llm raises when no provider configured."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="No LLM provider"):
                create_llm()


class TestLLMProviderEnum:
    """Test LLMProvider enum values."""

    def test_ollama_provider_exists(self):
        """Test that OLLAMA provider is defined."""
        assert LLMProvider.OLLAMA is not None
        assert LLMProvider.OLLAMA.value == "ollama"

    def test_provider_is_string_enum(self):
        """Test that LLMProvider is a string enum."""
        assert isinstance(LLMProvider.OLLAMA, str)
        assert LLMProvider.OLLAMA == "ollama"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])