"""Lightweight Adaptive AUTOSAR-inspired execution manager placeholder."""


class ExecutionManager:
    """Reads the service manifest and coordinates service startup."""

    def start(self) -> None:
        """Start managed services in dependency order."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop managed services gracefully."""
        raise NotImplementedError
