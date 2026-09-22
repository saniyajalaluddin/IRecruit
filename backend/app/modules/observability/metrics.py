"""Privacy-safe performance metrics and correlation tracking."""

import time
from typing import Dict
from pydantic import BaseModel, Field
from backend.app.core.logging import logger


class PipelineStageMetric(BaseModel):
    """Execution timing and status of an individual processing stage."""
    stage_name: str
    duration_ms: float
    status: str = "success"


class PipelineExecutionSummary(BaseModel):
    """Aggregate execution performance metrics for an analysis pipeline run."""
    analysis_id: str
    total_duration_ms: float
    stages: Dict[str, float] = Field(default_factory=dict)
    tokens_used: int = 0


class PerformanceTracker:
    """Contextual timer for measuring sub-system latencies safely."""

    def __init__(self, analysis_id: str):
        self.analysis_id = analysis_id
        self.start_time = time.perf_counter()
        self.stage_timings: Dict[str, float] = {}
        self.total_tokens: int = 0

    def record_stage(self, stage_name: str, duration_ms: float) -> None:
        """Records latency for a named pipeline stage."""
        self.stage_timings[stage_name] = round(duration_ms, 2)

    def record_tokens(self, count: int) -> None:
        """Tracks token expenditure without recording prompt content."""
        self.total_tokens += count

    def finish(self) -> PipelineExecutionSummary:
        """Finalizes timing and logs structured performance summary."""
        total_duration_ms = (time.perf_counter() - self.start_time) * 1000
        summary = PipelineExecutionSummary(
            analysis_id=self.analysis_id,
            total_duration_ms=round(total_duration_ms, 2),
            stages=self.stage_timings,
            tokens_used=self.total_tokens,
        )
        logger.info(
            f"Pipeline completed for analysis={self.analysis_id} in {summary.total_duration_ms}ms stages={self.stage_timings}",
            extra={"request_id": self.analysis_id},
        )
        return summary
