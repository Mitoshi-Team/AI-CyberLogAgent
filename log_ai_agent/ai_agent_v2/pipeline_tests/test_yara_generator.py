"""Tests for YARA rule generation (yara_generator.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.language_models import BaseLanguageModel

from log_ai_agent.ai_agent_v2.chains.yara_generator import (
    GeneratedYaraRule,
    YaraGenerator,
    _extract_rule_name,
    _sanitize_rule_name,
    _strip_yara_markers,
)
from log_ai_agent.ai_agent_v2.models_types import EventGroup, MITRETechnique

# ── Helpers ──────────────────────────────────────────────────────────────

_VALID_YARA_RULE = """rule Test_Rule
{
    meta:
        description = "Test rule"
        author = "test"
    strings:
        $s1 = "test" nocase
    condition:
        any of them
}"""

_BROKEN_YARA_RULE = """rule Broken_Rule
{
    strings:
        $s1 = "test"
    condition broken_syntax
}"""


def make_technique(
    technique_id: str = "T1001",
    name: str = "Test Technique",
    group_id: str | None = None,
) -> MITRETechnique:
    return MITRETechnique(
        technique_id=technique_id,
        name=name,
        group_id=group_id or "",
    )


def make_group(
    group_id: str = "g1",
    log_lines: list[str] | None = None,
) -> EventGroup:
    if log_lines is None:
        log_lines = ["line one", "line two"]
    return EventGroup(
        group_id=group_id,
        log_lines=log_lines,
    )


def create_mock_llm(*responses: str) -> MagicMock:
    """Return a mock LLM whose ainvoke yields the given responses in order."""
    mock = MagicMock(spec=BaseLanguageModel)
    mock.ainvoke = AsyncMock(side_effect=list(responses))
    return mock


def make_generator(llm_mock: MagicMock | None = None) -> YaraGenerator:
    if llm_mock is None:
        llm_mock = create_mock_llm(_VALID_YARA_RULE, "VALID")
    return YaraGenerator(llm=llm_mock)


# ── 1. GeneratedYaraRule ─────────────────────────────────────────────────


class TestGeneratedYaraRule:

    def test_to_dict(self):
        rule = GeneratedYaraRule(
            rule_name="TestRule",
            rule_content=_VALID_YARA_RULE,
            technique_id="T1001",
            technique_name="Test",
        )
        d = rule.to_dict()
        assert d["rule_name"] == "TestRule"
        assert d["rule_content"] == _VALID_YARA_RULE
        assert d["technique_id"] == "T1001"
        assert d["technique_name"] == "Test"


# ── 2. Helpers ───────────────────────────────────────────────────────────


class TestSanitizeRuleName:

    def test_basic(self):
        assert _sanitize_rule_name("T1001_Test") == "T1001_Test"

    def test_special_chars(self):
        assert _sanitize_rule_name("T1001_Test!!!@#$") == "T1001_Test"

    def test_spaces_replaced(self):
        assert _sanitize_rule_name("T1001 Test Rule") == "T1001_Test_Rule"

    def test_leading_digit_prefixed(self):
        assert _sanitize_rule_name("1001_test").startswith("rule_")

    def test_empty_returns_rule_prefix(self):
        # Empty input triggers "rule_" prefix fallback
        result = _sanitize_rule_name("")
        assert result.startswith("rule_")
        assert len(result) <= 64

    def test_max_length(self):
        long = "x" * 200
        assert len(_sanitize_rule_name(long)) <= 64


class TestExtractRuleName:

    def test_basic(self):
        assert _extract_rule_name("rule Foo_Bar { }") == "Foo_Bar"

    def test_multiline(self):
        content = "rule MultiLine\n{\n    strings:\n        $s = \"x\"\n}"
        assert _extract_rule_name(content) == "MultiLine"

    def test_no_rule_keyword(self):
        assert _extract_rule_name("just some text") is None

    def test_empty(self):
        assert _extract_rule_name("") is None


class TestStripYaraMarkers:

    def test_yara_marker(self):
        text = "```yara\nrule X { }\n```"
        assert _strip_yara_markers(text) == "rule X { }"

    def test_generic_marker(self):
        text = "```\nrule X { }\n```"
        assert _strip_yara_markers(text) == "rule X { }"

    def test_no_marker(self):
        text = "rule X { }"
        assert _strip_yara_markers(text) == "rule X { }"

    def test_empty(self):
        assert _strip_yara_markers("") == ""


# ── 3. Static methods (_compile_rule / _scan_logs) ───────────────────────


class TestCompileRule:

    def test_valid_rule(self):
        with patch(
            "log_ai_agent.ai_agent_v2.chains.yara_generator.yara.compile"
        ) as mock_compile:
            mock_compile.return_value = object()
            assert YaraGenerator._compile_rule("Test", _VALID_YARA_RULE) is True
            mock_compile.assert_called_once()

    def test_invalid_rule_raises_error(self):
        with patch(
            "log_ai_agent.ai_agent_v2.chains.yara_generator.yara.compile"
        ) as mock_compile:
            import yara

            mock_compile.side_effect = yara.Error("syntax error")
            assert YaraGenerator._compile_rule("Broken", _BROKEN_YARA_RULE) is False


class TestScanLogs:

    def test_match_found(self):
        mock_rules = MagicMock()
        mock_rules.match = MagicMock(return_value=["match"])
        with patch(
            "log_ai_agent.ai_agent_v2.chains.yara_generator.yara.compile",
            return_value=mock_rules,
        ):
            result = YaraGenerator._scan_logs(
                _VALID_YARA_RULE, "Test", ["test line"]
            )
            assert result is True

    def test_no_match(self):
        mock_rules = MagicMock()
        mock_rules.match = MagicMock(return_value=[])
        with patch(
            "log_ai_agent.ai_agent_v2.chains.yara_generator.yara.compile",
            return_value=mock_rules,
        ):
            result = YaraGenerator._scan_logs(
                _VALID_YARA_RULE, "Test", ["clean log"]
            )
            assert result is False

    def test_empty_logs(self):
        result = YaraGenerator._scan_logs(_VALID_YARA_RULE, "Test", [])
        assert result is False

    def test_compile_error_returns_false(self):
        import yara

        with patch(
            "log_ai_agent.ai_agent_v2.chains.yara_generator.yara.compile",
            side_effect=yara.Error("fail"),
        ):
            result = YaraGenerator._scan_logs("bad", "Bad", [])
            assert result is False


# ── 4. YaraGenerator.generate() ─────────────────────────────────────────


class TestYaraGeneratorGenerate:

    @pytest.mark.asyncio
    async def test_all_validations_pass(self):
        """Full success path: generate -> compile OK -> scan OK -> review OK."""
        gen = make_generator()
        with (
            patch.object(gen, "_compile_rule", return_value=True),
            patch.object(gen, "_scan_logs", return_value=True),
        ):
            rule = await gen.generate(
                technique=make_technique("T1001", "Test"),
                group=make_group("g1", ["test log line"]),
            )
        assert rule is not None
        assert isinstance(rule, GeneratedYaraRule)
        assert rule.technique_id == "T1001"
        assert rule.technique_name == "Test"

    @pytest.mark.asyncio
    async def test_no_log_lines_returns_none(self):
        """No events in group and no parsed_logs -> None."""
        gen = make_generator()
        group = make_group("g1", log_lines=[])
        rule = await gen.generate(
            technique=make_technique(),
            group=group,
            parsed_logs=[],
        )
        assert rule is None

    @pytest.mark.asyncio
    async def test_log_lines_from_group(self):
        """Log lines are sourced from group events, not parsed_logs."""
        gen = make_generator()
        group_logs = ["group specific log line"]
        group = make_group("g1", log_lines=group_logs)
        parsed_logs = [{"raw": "should not be used"}]

        with (
            patch.object(gen, "_compile_rule", return_value=True),
            patch.object(gen, "_scan_logs", return_value=True) as mock_scan,
        ):
            await gen.generate(
                technique=make_technique(group_id="g1"),
                group=group,
                parsed_logs=parsed_logs,
            )
        call_logs = mock_scan.call_args[0][2]
        assert call_logs == group_logs

    @pytest.mark.asyncio
    async def test_parsed_logs_fallback_when_no_group(self):
        """When group_id is empty, fall back to parsed_logs."""
        gen = make_generator()
        parsed_logs = [{"raw": "fallback line"}]

        with (
            patch.object(gen, "_compile_rule", return_value=True),
            patch.object(gen, "_scan_logs", return_value=True) as mock_scan,
        ):
            await gen.generate(
                technique=make_technique(group_id=""),
                group=None,
                parsed_logs=parsed_logs,
            )
        call_logs = mock_scan.call_args[0][2]
        assert "fallback line" in call_logs

    @pytest.mark.asyncio
    async def test_compilation_failure_then_retry_succeeds(self):
        """First attempt fails compilation, retry succeeds."""
        # Need 3 LLM responses: gen chain → RULE, fix chain → RULE, review → VALID
        llm = create_mock_llm(_VALID_YARA_RULE, _VALID_YARA_RULE, "VALID")
        gen = make_generator(llm)

        with (
            patch.object(
                gen, "_compile_rule", side_effect=[False, True]
            ) as mock_compile,
            patch.object(gen, "_scan_logs", return_value=True),
        ):
            rule = await gen.generate(
                technique=make_technique(),
                group=make_group(),
            )
        assert rule is not None
        assert mock_compile.call_count == 2

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_returns_none(self):
        """All generation+compilation retries fail -> None."""
        gen = make_generator()

        with patch.object(gen, "_compile_rule", return_value=False):
            rule = await gen.generate(
                technique=make_technique(),
                group=make_group(),
            )
        assert rule is None

    @pytest.mark.asyncio
    async def test_log_scan_fails_returns_none(self):
        """Rule compiles but doesn't match any log line -> None."""
        gen = make_generator()

        with (
            patch.object(gen, "_compile_rule", return_value=True),
            patch.object(gen, "_scan_logs", return_value=False),
        ):
            rule = await gen.generate(
                technique=make_technique(),
                group=make_group(),
            )
        assert rule is None

    @pytest.mark.asyncio
    async def test_llm_review_rejects_rule(self):
        """LLM review returns INVALID -> None."""
        # Attempt 0: gen → RULE, review → INVALID (continue)
        # Attempt 1: fix → RULE, compile=False → continue (short circuit)
        # Attempt 2: fix → RULE, compile=False → continue
        # → None
        llm = create_mock_llm(_VALID_YARA_RULE, "INVALID", _VALID_YARA_RULE, _VALID_YARA_RULE)
        gen = make_generator(llm)

        with (
            patch.object(gen, "_compile_rule", side_effect=[True, False, False]),
            patch.object(gen, "_scan_logs", return_value=True),
        ):
            rule = await gen.generate(
                technique=make_technique(),
                group=make_group(),
            )
        assert rule is None

    @pytest.mark.asyncio
    async def test_technique_description_from_chroma(self):
        """Technique description is fetched from ChromaDB when available."""
        chroma_mock = MagicMock()
        chroma_mock.is_initialized = True
        chroma_mock.search = MagicMock(
            return_value=[{"content": "passage: Some technique info"}]
        )
        gen = make_generator()
        gen.chroma_mgr = chroma_mock

        with (
            patch.object(gen, "_compile_rule", return_value=True),
            patch.object(gen, "_scan_logs", return_value=True),
        ):
            rule = await gen.generate(
                technique=make_technique("T1001"),
                group=make_group(),
            )
        assert rule is not None
        chroma_mock.search.assert_called_once()


# ── 5. YaraGenerator.generate_for_pipeline() ────────────────────────────


class TestGenerateForPipeline:

    def _make_pipeline_stages(
        self,
        mitre_techniques: list[MITRETechnique] | None = None,
        rules_matched: list[str] | None = None,
    ) -> dict:
        return {
            "agent2": {"mitre_techniques": mitre_techniques or []},
            "yara": {"rules_matched": rules_matched or []},
        }

    @pytest.mark.asyncio
    async def test_no_mitre_techniques(self):
        gen = make_generator()
        stages = self._make_pipeline_stages(mitre_techniques=[])
        result = await gen.generate_for_pipeline(
            pipeline_stages=stages, groups=[], parsed_logs=[]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_yara_already_matched_skips(self):
        gen = make_generator()
        stages = self._make_pipeline_stages(
            mitre_techniques=[make_technique()],
            rules_matched=["ExistingRule"],
        )
        result = await gen.generate_for_pipeline(
            pipeline_stages=stages, groups=[], parsed_logs=[]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_generates_for_uncovered_techniques(self):
        gen = make_generator()

        with (
            patch.object(gen, "generate", return_value=GeneratedYaraRule(
                rule_name="R1",
                rule_content=_VALID_YARA_RULE,
                technique_id="T1001",
                technique_name="T1",
            )),
        ):
            stages = self._make_pipeline_stages(
                mitre_techniques=[make_technique("T1001", "T1")],
                rules_matched=[],
            )
            result = await gen.generate_for_pipeline(
                pipeline_stages=stages,
                groups=[make_group("g1")],
                parsed_logs=[],
            )
        assert len(result) == 1
        assert result[0].technique_id == "T1001"

    @pytest.mark.asyncio
    async def test_generates_multiple_techniques(self):
        gen = make_generator()

        with (
            patch.object(gen, "generate", return_value=GeneratedYaraRule(
                rule_name="R",
                rule_content=_VALID_YARA_RULE,
                technique_id="T",
                technique_name="T",
            )),
        ):
            stages = self._make_pipeline_stages(
                mitre_techniques=[
                    make_technique("T1001", "T1"),
                    make_technique("T1002", "T2"),
                ],
                rules_matched=[],
            )
            result = await gen.generate_for_pipeline(
                pipeline_stages=stages,
                groups=[make_group("g1"), make_group("g2")],
                parsed_logs=[],
            )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_group_lookup_by_group_id(self):
        """Technique with group_id finds matching group."""
        gen = make_generator()

        with (
            patch.object(
                gen,
                "generate",
                return_value=GeneratedYaraRule(
                    rule_name="R", rule_content=_VALID_YARA_RULE,
                    technique_id="T1001", technique_name="T1",
                ),
            ) as mock_gen,
        ):
            stages = self._make_pipeline_stages(
                mitre_techniques=[make_technique("T1001", "T1", group_id="g1")],
                rules_matched=[],
            )
            groups = [
                make_group("g1", ["line from g1"]),
                make_group("g2", ["line from g2"]),
            ]
            await gen.generate_for_pipeline(
                pipeline_stages=stages,
                groups=groups,
                parsed_logs=[],
            )
        _, kwargs = mock_gen.call_args
        group = kwargs["group"]
        assert group is not None
        assert group["group_id"] == "g1"

    @pytest.mark.asyncio
    async def test_group_not_found_falls_back(self):
        """Technique has group_id but group not in list -> generate with None."""
        gen = make_generator()

        with (
            patch.object(
                gen,
                "generate",
                return_value=GeneratedYaraRule(
                    rule_name="R", rule_content=_VALID_YARA_RULE,
                    technique_id="T1001", technique_name="T1",
                ),
            ) as mock_gen,
        ):
            stages = self._make_pipeline_stages(
                mitre_techniques=[make_technique("T1001", "T1", group_id="missing")],
                rules_matched=[],
            )
            await gen.generate_for_pipeline(
                pipeline_stages=stages,
                groups=[make_group("g1")],
                parsed_logs=[],
            )
        _, kwargs = mock_gen.call_args
        assert kwargs["group"] is None


# ── 6. Integration in app_integration.py (analyze_log_v2) ────────────────


class TestAnalyzeLogV2Integration:

    @pytest.mark.asyncio
    async def test_analyze_log_v2_triggers_generation(self):
        """YARA generator runs when RAG found techniques but YARA didn't match."""
        import log_ai_agent.ai_agent_v2.app_integration as ai

        mock_pipeline = MagicMock()
        mock_pipeline.analyze = AsyncMock(return_value={
            "success": True,
            "stages": {
                "agent1": {"groups": [make_group("g1")]},
                "agent2": {"mitre_techniques": [make_technique("T1001")]},
                "agent3": {"final_report": "test", "severity_level_id": 2, "threat_type_id": 5, "mitre_techniques": []},
                "yara": {"rules_matched": []},
            },
        })

        mock_pipeline.chroma_mgr = MagicMock()
        mock_generator = MagicMock()
        mock_generator.generate_for_pipeline = AsyncMock(return_value=[
            GeneratedYaraRule("R1", _VALID_YARA_RULE, "T1001", "Test"),
        ])

        with (
            patch.object(ai, "_pipeline", None),
            patch.object(ai, "_agent_config", None),
            patch.object(ai, "create_pipeline", return_value=mock_pipeline),
            patch.object(ai, "YaraGenerator", return_value=mock_generator),
        ):
            result = await ai.analyze_log_v2("test log")
            assert result["description"] == "test"
            assert "generated_yara_rules" in result
            assert len(result["generated_yara_rules"]) == 1

    @pytest.mark.asyncio
    async def test_skips_when_yara_matched(self):
        """No generation if YARA rules already matched."""
        import log_ai_agent.ai_agent_v2.app_integration as ai

        mock_pipeline = MagicMock()
        mock_pipeline.chroma_mgr = MagicMock()
        mock_pipeline.analyze = AsyncMock(return_value={
            "success": True,
            "stages": {
                "agent1": {"groups": []},
                "agent2": {"mitre_techniques": [make_technique("T1001")]},
                "agent3": {"final_report": "test", "severity_level_id": 2, "threat_type_id": 5, "mitre_techniques": []},
                "yara": {"rules_matched": ["ExistingRule"]},
            },
        })

        mock_generator = MagicMock()
        mock_generator.generate_for_pipeline = AsyncMock(return_value=[])

        with (
            patch.object(ai, "_pipeline", None),
            patch.object(ai, "_agent_config", None),
            patch.object(ai, "create_pipeline", return_value=mock_pipeline),
            patch.object(ai, "YaraGenerator", return_value=mock_generator),
        ):
            result = await ai.analyze_log_v2("test log")
            assert "generated_yara_rules" not in result

    @pytest.mark.asyncio
    async def test_skips_when_no_mitre_techniques(self):
        """No generation if RAG found no MITRE techniques."""
        import log_ai_agent.ai_agent_v2.app_integration as ai

        mock_pipeline = MagicMock()
        mock_pipeline.chroma_mgr = MagicMock()
        mock_pipeline.analyze = AsyncMock(return_value={
            "success": True,
            "stages": {
                "agent1": {"groups": []},
                "agent2": {"mitre_techniques": []},
                "agent3": {"final_report": "test", "severity_level_id": 2, "threat_type_id": 5, "mitre_techniques": []},
                "yara": {"rules_matched": []},
            },
        })

        mock_generator = MagicMock()
        mock_generator.generate_for_pipeline = AsyncMock(return_value=[])

        with (
            patch.object(ai, "_pipeline", None),
            patch.object(ai, "_agent_config", None),
            patch.object(ai, "create_pipeline", return_value=mock_pipeline),
            patch.object(ai, "YaraGenerator", return_value=mock_generator),
        ):
            result = await ai.analyze_log_v2("test log")
            assert "generated_yara_rules" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
