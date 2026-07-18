"""Helpers for safe logging of user-influenced values."""


def scrub(value: object) -> str:
    """Strip CR/LF from a value before it is written to a log line.

    User-controlled strings (business names, search terms, emails) can contain
    newlines that forge extra log entries (log injection). Collapsing line
    breaks to spaces neutralises that while keeping the value readable.
    """
    return str(value).replace("\r", " ").replace("\n", " ")
