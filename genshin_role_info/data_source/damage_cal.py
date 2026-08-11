"""Compatibility import for the Miao-Plugin damage engine.

The former hand-written calculator lived in this module.  It is intentionally
no longer implemented here: all role, weapon, artifact, reaction, and shield
calculation now comes from the synchronized Miao metadata under
``data_source.damage``.
"""

from .damage import get_role_dmg

__all__ = ["get_role_dmg"]
