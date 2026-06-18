"""Cross-repo invariant verifier for the zyplux organization."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("zyplux-cerberus")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0+unknown"
