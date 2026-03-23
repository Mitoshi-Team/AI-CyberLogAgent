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


class FinalAnalysisResult(BaseModel):
    """Result from Agent 2 - Final report generation."""

    success: bool = Field(..., description="Whether analysis was successful")
    report_text: str = Field(..., description="Final report text")
    severity_level_id: int = Field(..., ge=1, le=4, description="Severity level 1-4")
    threat_type_id: int = Field(..., ge=1, le=11, description="Threat type 1-11")
    mitre_techniques: list[str] = Field(
        default_factory=list, description="List of MITRE technique IDs"
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
    def severity_level_id(self) -> int:
        """Get severity level ID if available."""
        if self.final_result and self.final_result.success:
            return self.final_result.severity_level_id
        return 3  # Default: Medium

    @property
    def threat_type_id(self) -> int:
        """Get threat type ID if available."""
        if self.final_result and self.final_result.success:
            return self.final_result.threat_type_id
        return 11  # Default: Other
