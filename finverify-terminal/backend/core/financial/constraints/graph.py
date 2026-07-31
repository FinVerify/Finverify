"""Deterministic dependency graph for financial equations."""

from __future__ import annotations

import heapq
from typing import Iterable

from .models import Equation


class ConstraintGraph:
    """Build and query a deterministic dependency graph."""

    def __init__(self, equations: Iterable[Equation]):
        self._equations = tuple(equations)
        dependency_map: dict[str, set[str]] = {}
        dependent_map: dict[str, set[str]] = {}
        nodes: set[str] = set()

        for equation in self._equations:
            target = equation.target.name
            nodes.add(target)
            dependency_map.setdefault(target, set())
            dependent_map.setdefault(target, set())
            for dependency in equation.dependency_names():
                nodes.add(dependency)
                dependency_map.setdefault(dependency, set())
                dependent_map.setdefault(dependency, set())
                dependency_map[target].add(dependency)
                dependent_map[dependency].add(target)

        self.nodes = tuple(sorted(nodes))
        self._dependencies = {
            node: tuple(sorted(dependency_map.get(node, set())))
            for node in self.nodes
        }
        self._dependents = {
            node: tuple(sorted(dependent_map.get(node, set())))
            for node in self.nodes
        }
        self._topological_order = self._compute_topological_order()

    def get_dependencies(self, variable: str) -> tuple[str, ...]:
        return self._dependencies.get(variable, ())

    def get_dependents(self, variable: str) -> tuple[str, ...]:
        return self._dependents.get(variable, ())

    def topological_order(self) -> tuple[str, ...]:
        return self._topological_order

    def edges(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (source, target)
            for source in self.nodes
            for target in self.get_dependents(source)
        )

    def _compute_topological_order(self) -> tuple[str, ...]:
        indegree = {
            node: len(self._dependencies[node])
            for node in self.nodes
        }
        ready = [node for node, degree in indegree.items() if degree == 0]
        heapq.heapify(ready)
        ordered: list[str] = []

        while ready:
            node = heapq.heappop(ready)
            ordered.append(node)
            for dependent in self._dependents[node]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    heapq.heappush(ready, dependent)

        if len(ordered) != len(self.nodes):
            remaining = tuple(sorted(node for node, degree in indegree.items() if degree > 0))
            cycle = self._find_cycle(remaining)
            raise ValueError(f"Cycle detected: {' -> '.join(cycle)}")

        return tuple(ordered)

    def _find_cycle(self, remaining: tuple[str, ...]) -> list[str]:
        remaining_set = set(remaining)
        visited: set[str] = set()
        stack: list[str] = []
        on_stack: set[str] = set()

        def dfs(node: str) -> list[str] | None:
            visited.add(node)
            stack.append(node)
            on_stack.add(node)
            neighbors = [
                neighbor
                for neighbor in self._dependents[node]
                if neighbor in remaining_set
            ]

            # Explore deeper first so we prefer a fuller explicit cycle path.
            for neighbor in neighbors:
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle is not None:
                        return cycle

            for neighbor in neighbors:
                if neighbor in on_stack:
                    start_index = stack.index(neighbor)
                    return stack[start_index:] + [neighbor]

            stack.pop()
            on_stack.remove(node)
            return None

        for node in remaining:
            if node in visited:
                continue
            cycle = dfs(node)
            if cycle is not None:
                return cycle

        return [remaining[0], remaining[0]]
