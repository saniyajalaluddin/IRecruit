"""Dashboard module initialization."""

from backend.app.modules.dashboard.schemas import (
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    DashboardMetrics,
)
from backend.app.modules.dashboard.service import (
    DashboardService,
    dashboard_service,
)

__all__ = [
    "AnalysisHistoryItem",
    "AnalysisHistoryResponse",
    "DashboardMetrics",
    "DashboardService",
    "dashboard_service",
]

