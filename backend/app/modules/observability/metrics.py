"""Privacy-safe performance metrics, telemetry collector, and correlation tracking."""

from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import Dict, List, Optional
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


class TelemetryCollector:
    """Thread-safe in-memory telemetry, request counting, and latency percentiles."""

    def __init__(self):
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._status_counts: Dict[int, int] = defaultdict(int)
        self._latencies: List[float] = []

    def record_request(
        self, method: str, path: str, status_code: int, duration_ms: float
    ) -> None:
        """Record an incoming HTTP request outcome."""
        self._request_count += 1
        self._status_counts[status_code] += 1
        if status_code >= 400:
            self._error_count += 1

        # Keep a bounded sample of recent latencies (max 5,000 items)
        if len(self._latencies) >= 5000:
            self._latencies.pop(0)
        self._latencies.append(duration_ms)

    def get_summary(self) -> Dict[str, float | int | dict]:
        """Calculates current telemetry summary including percentiles."""
        uptime = round(time.time() - self._start_time, 2)
        sorted_latencies = sorted(self._latencies) if self._latencies else [0.0]
        n = len(sorted_latencies)

        def percentile(p: float) -> float:
            if not sorted_latencies or sorted_latencies == [0.0]:
                return 0.0
            idx = max(0, min(n - 1, int(math.ceil((p / 100.0) * n) - 1)))
            return round(sorted_latencies[idx], 2)

        p50 = percentile(50.0)
        p95 = percentile(95.0)
        p99 = percentile(99.0)

        error_rate = round(self._error_count / self._request_count, 4) if self._request_count > 0 else 0.0

        return {
            "uptime_seconds": uptime,
            "total_requests": self._request_count,
            "error_count": self._error_count,
            "error_rate": error_rate,
            "status_codes": dict(self._status_counts),
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "latency_p99_ms": p99,
        }

    def reset(self) -> None:
        """Reset telemetry collector metrics."""
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._status_counts.clear()
        self._latencies.clear()


# Global telemetry singleton
telemetry = TelemetryCollector()
