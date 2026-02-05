"""
Structured logging configuration for DuggerBootTools.

Provides centralized logging with Loguru for application events
and Rich integration for user-facing output.
"""

import sys
from pathlib import Path
from typing import Any, Dict
from loguru import logger
from rich.console import Console


class DuggerLogger:
    """Centralized logging system for DuggerBootTools."""
    
    def __init__(self) -> None:
        self.console = Console()
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure Loguru with appropriate handlers."""
        # Remove default handler
        logger.remove()
        
        # Add console handler with structured format
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            level="INFO",
            colorize=True,
        )
        
        # Add file logging for debugging
        log_dir = Path.home() / ".duggerboot" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_dir / "duggerboot.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="gz",
        )
    
    def log_bootstrap_start(self, project_name: str, template_type: str) -> None:
        """Log project bootstrap initiation."""
        logger.info(f"Starting bootstrap: project='{project_name}' template='{template_type}'")
    
    def log_bootstrap_success(self, project_path: Path) -> None:
        """Log successful bootstrap completion."""
        logger.info(f"Bootstrap completed successfully: path='{project_path}'")
    
    def log_bootstrap_failure(self, project_name: str, error: Exception) -> None:
        """Log bootstrap failure with context."""
        logger.error(f"Bootstrap failed: project='{project_name}' error='{str(error)}'")
        logger.exception("Bootstrap failure details")
    
    def log_dependency_check(self, template_name: str, is_compatible: bool, issues: list[str]) -> None:
        """Log dependency compatibility check results."""
        if is_compatible:
            logger.info(f"Dependency check passed: template='{template_name}'")
        else:
            logger.warning(f"Dependency check failed: template='{template_name}' issues={issues}")
    
    def log_template_load(self, template_name: str, template_path: Path) -> None:
        """Log template loading."""
        logger.debug(f"Template loaded: name='{template_name}' path='{template_path}'")
    
    def log_git_operation(self, operation: str, project_path: Path, success: bool) -> None:
        """Log Git operations."""
        if success:
            logger.info(f"Git operation successful: operation='{operation}' path='{project_path}'")
        else:
            logger.error(f"Git operation failed: operation='{operation}' path='{project_path}'")
    
    def log_rollback(self, project_path: Path, reason: str) -> None:
        """Log rollback operations."""
        logger.warning(f"Rollback initiated: path='{project_path}' reason='{reason}'")
    
    def log_scout_start(self, scan_path: Path) -> None:
        """Log ecosystem scout initiation."""
        logger.info(f"Starting ecosystem scan: path='{scan_path}'")
    
    def log_scout_results(self, projects_found: int, retrofit_candidates: int) -> None:
        """Log scout results."""
        logger.info(f"Scan completed: projects_found={projects_found} retrofit_candidates={retrofit_candidates}")
    
    def log_harvest_operation(self, component_name: str, source_path: Path, success: bool) -> None:
        """Log component harvest operations."""
        if success:
            logger.info(f"Component harvested: name='{component_name}' source='{source_path}'")
        else:
            logger.error(f"Harvest failed: name='{component_name}' source='{source_path}'")
    
    def log_validation_error(self, file_path: Path, validation_errors: list[str]) -> None:
        """Log validation errors."""
        logger.error(f"Validation failed: file='{file_path}' errors={validation_errors}")
    
    def display_error(self, title: str, message: str) -> None:
        """Display error to user with Rich formatting."""
        self.console.print(
            f"[bold red]{title}[/bold red]: {message}",
            style="red"
        )
    
    def display_success(self, title: str, message: str) -> None:
        """Display success message to user."""
        self.console.print(
            f"[bold green]{title}[/bold green]: {message}",
            style="green"
        )
    
    def display_warning(self, title: str, message: str) -> None:
        """Display warning message to user."""
        self.console.print(
            f"[bold yellow]{title}[/bold yellow]: {message}",
            style="yellow"
        )
    
    def display_info(self, title: str, message: str) -> None:
        """Display info message to user."""
        self.console.print(
            f"[bold blue]{title}[/bold blue]: {message}",
            style="blue"
        )


# Global logger instance
dugger_logger = DuggerLogger()
