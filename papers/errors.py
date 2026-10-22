"""Errors that every layer may raise or catch. This module imports nothing from the package, so any
module can import it without a cycle."""


class ProviderError(RuntimeError):
    """A provider, a model answer, or a workflow step failed in a way the reader can act on.

    ``message`` is the plain line that the reader sees. ``detail`` is the raw text, such as an HTTP status
    and the provider's own words. ``str()`` keeps both, so records and the retry checks still see the status.
    """

    def __init__(self, message, detail=''):
        super().__init__(message + (' ' + detail if detail else ''))
        self.message, self.detail = message, detail
