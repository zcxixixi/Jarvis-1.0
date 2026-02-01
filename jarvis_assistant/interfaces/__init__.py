"""
Clean interface abstractions for Jarvis I/O.
Allows agent to work with ANY input/output implementation.
"""

from .input import InputInterface
from .output import OutputInterface

__all__ = ["InputInterface", "OutputInterface"]
