import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import questionary
import typer
from rich.panel import Panel

from cli.app import app, console
from database.models import Work, Volume
from database.repositories.book_repository import BookRepository

logger = logging.getLogger(__name__)
