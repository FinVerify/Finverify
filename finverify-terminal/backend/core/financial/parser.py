"""Rule-based parser for Milestone 1 financial tasks."""

from .tasks import FinancialTask, TaskType


class TaskParser:
    @staticmethod
    def parse(question: str) -> FinancialTask:
        lower_question = question.lower()
        if "revenue" in lower_question and any(token in lower_question for token in ("yoy", "year over year", "compare", "growth")):
            return FinancialTask(
                type=TaskType.ANSWER_METRIC,
                metric="RevenueYoYGrowth",
                comparison="yoy",
            )
        if "gross margin" in lower_question or "gross profit margin" in lower_question:
            return FinancialTask(
                type=TaskType.ANSWER_METRIC,
                metric="GrossMargin",
            )
        if "operating margin" in lower_question:
            return FinancialTask(
                type=TaskType.ANSWER_METRIC,
                metric="OperatingMargin",
            )
        if "operating income" in lower_question:
            return FinancialTask(
                type=TaskType.ANSWER_METRIC,
                metric="OperatingIncome",
            )
        if "net income" in lower_question or "earnings" in lower_question:
            return FinancialTask(
                type=TaskType.ANSWER_METRIC,
                metric="NetIncome",
            )
        if "cash flow" in lower_question:
            return FinancialTask(
                type=TaskType.ANSWER_METRIC,
                metric="OperatingCashFlow",
            )
        if "revenue" in lower_question or "sales" in lower_question:
            return FinancialTask(
                type=TaskType.ANSWER_METRIC,
                metric="Revenue",
            )
        return FinancialTask(type=TaskType.ANSWER_METRIC)
