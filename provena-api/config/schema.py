"""Custom drf-spectacular AutoSchema.

An operation's description comes only from the view's *own* class docstring (or
its handler method's docstring), never from one inherited from a mixin or base
class. Without this, drf-spectacular walks the MRO and picks up boilerplate such
as ``PaginatedListMixin``'s usage docstring, which then leaks into the API docs.

Explicit ``@extend_schema(description=...)`` still takes precedence; this only
governs the docstring fallback.
"""

import inspect

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import get_doc


class OwnDocstringAutoSchema(AutoSchema):
    def get_description(self) -> str:  # type: ignore[override]
        action_or_method = getattr(
            self.view, getattr(self.view, "action", self.method.lower()), None
        )
        action_doc = get_doc(action_or_method)

        # Only the docstring defined directly on the view class, not one
        # inherited via the MRO from a mixin/base class.
        own = self.view.__class__.__dict__.get("__doc__")
        view_doc = (
            "\n".join(line.rstrip() for line in inspect.cleandoc(own).splitlines()) if own else ""
        )

        return action_doc or view_doc
