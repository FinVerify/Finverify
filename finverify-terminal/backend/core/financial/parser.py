"""Rule-based parser for Milestone 1 financial tasks."""

from .tasks import FinancialTask, TaskType


class TaskParser:
    @staticmethod
    def parse(question: str) -> FinancialTask:
        lower_question = question.lower()
        if "gross margin" in lower_question or "gross profit margin" in lower_question:
            return FinancialTask(
                type=TaskType.ANSWER_METRIC,
                metric="GrossMargin",
            )
        return FinancialTask(type=TaskType.ANSWER_METRIC)
