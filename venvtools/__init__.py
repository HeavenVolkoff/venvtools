# Internal
import sys

if sys.version_info < (3, 8):
    # External
    from importlib_metadata import version  # type: ignore
else:
    # Internal
    from importlib.metadata import version

try:
    __version__: str = version(__name__)
except Exception:  # pragma: no cover
    # Internal
    import traceback
    from warnings import warn

    warn(f"Failed to set version due to:\n{traceback.format_exc()}", ImportWarning)
    __version__ = "0.0a0"

__all__ = ("__version__",)
