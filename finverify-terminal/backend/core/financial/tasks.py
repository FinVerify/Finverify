"""Task models for deterministic financial reasoning."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    ANSWER_METRIC = "answer_metric"


class FinancialTask(BaseModel):
    type: TaskType
    metric: Optional[str] = None
    company: Optional[str] = None
    period: Optional[str] = None
    comparison: Optional[str] = None


class TaskRegistry(BaseModel):
    supported_metrics: dict[TaskType, set[str]] = Field(
        default_factory=lambda: {
            TaskType.ANSWER_METRIC: {
                "GrossMargin",
                "OperatingMargin",
                "Revenue",
                "RevenueYoYGrowth",
                "OperatingIncome",
                "NetIncome",
                "OperatingCashFlow",
            },
        }
    )

    def supports(self, task: FinancialTask) -> bool:
        if task.metric is None:
            return False
        return task.metric in self.supported_metrics.get(task.type, set())
