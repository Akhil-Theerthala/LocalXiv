"""Errors that every layer may raise or catch. This module imports nothing from the package, so any
module can import it without a cycle."""


class ProviderError(RuntimeError):
    """A provider, a model answer, or a workflow step failed in a way the reader can act on."""
