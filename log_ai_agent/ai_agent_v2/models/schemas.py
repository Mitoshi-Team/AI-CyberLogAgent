"""Pydantic models for AI analysis results."""

from pydantic import BaseModel, Field


class PrimaryAnalysisResult(BaseModel):
    """Result from Agent 1 - Primary log analysis."""

    success: bool = Field(..., description="Whether analysis was successful")
    analysis_text: str = Field(..., description="Primary analysis report text")
    events_found: int = Field(
        default=0, description="Number of suspicious events found"
    )
    error_message: str | None = Field(None, description="Error message if failed")
    processing_time_ms: float | None = Field(
        None, description="Processing time in milliseconds"
    )


class MITREResult(BaseModel):
    """Result from RAG MITRE search."""

    success: bool = Field(..., description="Whether RAG search was successful")
    techniques: list[dict] = Field(
        default_factory=list, description="List of matched MITRE techniques"
    )
    context_text: str = Field(default="", description="Formatted context from RAG")
    error_message: str | None = Field(None, description="Error message if failed")


class IncidentData(BaseModel):
    """Single incident within a report, mapped to a MITRE technique."""

    description: str = Field(..., description="Description of the incident event")
    technique_id: str = Field(..., description="MITRE ATT&CK technique ID (e.g. T1110)")
    technique_name: str = Field(..., description="MITRE technique name")
    tactic: str = Field(..., description="MITRE tactic (e.g. TA0006 - Credential Access)")
    severity_level_id: int = Field(..., ge=1, le=4, description="Severity level 1-4")
    threat_type_id: int | None = Field(None, description="Optional threat type 1-11")
    group_id: str | None = Field(None, description="Event group ID from Agent 1")
    confirmed: bool = Field(True, description="Whether incident is confirmed by YARA/Sigma")


class FinalAnalysisResult(BaseModel):
    """Result from Agent 2 - Final report generation."""

    success: bool = Field(..., description="Whether analysis was successful")
    report_text: str = Field(..., description="Final report text")
    overall_severity_level_id: int = Field(..., ge=1, le=4, description="Overall severity level 1-4")
    incidents: list[IncidentData] = Field(
        default_factory=list, description="List of detected incidents with MITRE techniques"
    )
    error_message: str | None = Field(None, description="Error message if failed")
    processing_time_ms: float | None = Field(
        None, description="Processing time in milliseconds"
    )


class FullPipelineResult(BaseModel):
    """Complete pipeline result combining all stages."""

    success: bool = Field(..., description="Whether full pipeline was successful")
    primary_analysis: PrimaryAnalysisResult | None = Field(
        None, description="Agent 1 result"
    )
    mitre_result: MITREResult | None = Field(None, description="RAG result")
    final_result: FinalAnalysisResult | None = Field(None, description="Agent 2 result")
    total_processing_time_ms: float | None = Field(
        None, description="Total processing time"
    )
    log_size_bytes: int = Field(..., description="Size of analyzed log in bytes")

    @property
    def report_text(self) -> str:
        """Get final report text if available."""
        if self.final_result and self.final_result.success:
            return self.final_result.report_text
        return ""

    @property
    def overall_severity_level_id(self) -> int:
        """Get overall severity level ID if available."""
        if self.final_result and self.final_result.success:
            return self.final_result.overall_severity_level_id
        return 3  # Default: Medium

    @property
    def incidents(self) -> list:
        """Get incidents list if available."""
        if self.final_result and self.final_result.success:
            return self.final_result.incidents
        return []
