"""Execution planning for Milestone 1 financial tasks."""

from .concepts import ConceptRegistry
from .document import FinancialDocument
from .tasks import FinancialTask, TaskRegistry, TaskType


class ExecutionPlanner:
    def __init__(self, registry: ConceptRegistry, task_registry: TaskRegistry | None = None):
        self.registry = registry
        self.task_registry = task_registry or TaskRegistry()

    def plan(self, task: FinancialTask, doc: FinancialDocument) -> list[dict]:
        del doc
        if task.type == TaskType.ANSWER_METRIC and task.metric and self.task_registry.supports(task):
            spec = self.registry.get_concept(task.metric)
            required = spec.get("requires", []) or [task.metric]
            formula = spec.get("formula", "")
            return [
                {"action": "retrieve", "params": {"concepts": required}},
                {"action": "compute", "params": {"metric": task.metric, "formula": formula}},
                {"action": "verify", "params": {"metric": task.metric}},
                {"action": "build_contract", "params": {"required": required}},
            ]
        return []
