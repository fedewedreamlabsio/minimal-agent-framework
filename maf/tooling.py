from __future__ import annotations

from .contracts import ToolSpec


class ToolRegistry:
    def __init__(self, tools: list[ToolSpec] | None = None) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: ToolSpec) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool registration: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def schemas(self) -> list[dict[str, object]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
                "timeout_seconds": tool.timeout_seconds,
            }
            for tool in self._tools.values()
        ]
