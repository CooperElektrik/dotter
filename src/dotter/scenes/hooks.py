"""Decorators and registry for inProse companion Python hooks."""

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotter.scenes.context import HookContext

type HookFn = Callable[[HookContext], Any]


class HookRegistry:
    """Registry managing companion hook functions keyed by name or lifecycle event."""

    def __init__(self) -> None:
        self._named_hooks: dict[str, HookFn] = {}
        self._entry_hooks: dict[str, list[HookFn]] = {}
        self._exit_hooks: dict[str, list[HookFn]] = {}

    def register_hook(self, name: str, fn: HookFn) -> None:
        """Register a named hook corresponding to '~ <name>' in .p."""
        self._named_hooks[name] = fn

    def register_on_entry(self, label: str, fn: HookFn) -> None:
        """Register an entry hook called when entering label."""
        self._entry_hooks.setdefault(label, []).append(fn)

    def register_on_exit(self, label: str, fn: HookFn) -> None:
        """Register an exit hook called when leaving label."""
        self._exit_hooks.setdefault(label, []).append(fn)

    def execute_hook(self, name: str, ctx: HookContext) -> bool:
        """Execute a named hook if present, returning True if found."""
        if name in self._named_hooks:
            self._named_hooks[name](ctx)
            return True
        return False

    def execute_on_entry(self, label: str, ctx: HookContext) -> None:
        """Execute all on_entry hooks registered for a label."""
        for fn in self._entry_hooks.get(label, ()):
            fn(ctx)

    def execute_on_exit(self, label: str, ctx: HookContext) -> None:
        """Execute all on_exit hooks registered for a label."""
        for fn in self._exit_hooks.get(label, ()):
            fn(ctx)

    def load_companion_module(self, py_path: Path) -> bool:
        """Dynamically load companion Python module to trigger hook registrations."""
        if not py_path.exists():
            return False

        module_name = f"companion_{py_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_path)
        if spec is None or spec.loader is None:
            return False

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True


_DEFAULT_REGISTRY = HookRegistry()


def get_default_registry() -> HookRegistry:
    """Retrieve the global default hook registry."""
    return _DEFAULT_REGISTRY


def hook(name: str) -> Callable[[HookFn], HookFn]:
    """Decorator registering a function as a named hook for '~ <name>'."""

    def decorator(fn: HookFn) -> HookFn:
        _DEFAULT_REGISTRY.register_hook(name, fn)
        return fn

    return decorator


def on_entry(label: str) -> Callable[[HookFn], HookFn]:
    """Decorator registering a function to run when entering a label."""

    def decorator(fn: HookFn) -> HookFn:
        _DEFAULT_REGISTRY.register_on_entry(label, fn)
        return fn

    return decorator


def on_exit(label: str) -> Callable[[HookFn], HookFn]:
    """Decorator registering a function to run when exiting a label."""

    def decorator(fn: HookFn) -> HookFn:
        _DEFAULT_REGISTRY.register_on_exit(label, fn)
        return fn

    return decorator
