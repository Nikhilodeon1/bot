"""
Browser Interface module for the Botted Library

Handles all web interaction functionality including browser control,
action handling, and web scraping.
"""

from .browser_controller import BrowserController
from .actions import ActionHandler
from .scraper import WebScraper

__all__ = [
    "BrowserController",
    "ActionHandler",
    "WebScraper"
]