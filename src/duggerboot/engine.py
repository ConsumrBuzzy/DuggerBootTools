"""
DuggerBootTools Core Engine

Handles project scaffolding, template rendering, and DLT integration.
"""

from pathlib import Path
from typing import List, Dict, Any
import shutil
import subprocess
from jinja2 import Environment, FileSystemLoader, Template

from duggerlink.models.project import DuggerProject as Project
from duggerlink.retrofit_engine import RetrofitEngine
from .exceptions import DuggerBootError


class BootEngine:
    """Core engine for bootstrapping projects with DLT DNA validation."""
    
    def __init__(self) -> None:
        self.templates_dir = Path(__file__).parent / "templates"
        # GitOperations will be initialized per project
        self.git_manager = None
        
    def bootstrap_project(
        self,
        name: str,
        template_type: str,
        parent_path: Path,
        force: bool = False,
    ) -> Path:
        """Bootstrap a new project with full DLT integration."""
        
        # Validate project name
        self._validate_project_name(name)
        
        # Create project path
        project_path = parent_path / name
        
        # Check if directory exists
        if project_path.exists() and not force:
            raise DuggerBootError(f"Directory '{project_path}' already exists. Use --force to overwrite.")
        
        # Load template
        template_data = self._load_template(template_type)
        
        # Create directory structure
        self._create_directory_structure(project_path, template_data["structure"])
        
        # Render and create files
        template_path = self.templates_dir / template_type
        context = {
            "project_name": name,
            "template_type": template_type,
        }
        self._render_files(project_path, template_path, context)
        
        # Validate generated dugger.yaml against DLT schema
        self._validate_dna(project_path / "dugger.yaml")
        
        # Initialize Git and make initial commit
        self._initialize_git(project_path, name)
        
        return project_path
    
    def list_templates(self) -> List[str]:
        """List all available project templates."""
        if not self.templates_dir.exists():
            return []
        
        return [d.name for d in self.templates_dir.iterdir() if d.is_dir()]
    
    def _validate_project_name(self, name: str) -> None:
        """Validate project name meets standards."""
        if not name:
            raise DuggerBootError("Project name cannot be empty.")
        
        # Check for invalid characters
        invalid_chars = set('<>:"/\\|?*')
        if any(char in invalid_chars for char in name):
            raise DuggerBootError("Project name contains invalid characters.")
        
        # Check if starts with letter or underscore
        if not (name[0].isalpha() or name[0] == '_'):
            raise DuggerBootError("Project name must start with a letter or underscore.")
    
    def _load_template(self, template_type: str) -> Dict[str, Any]:
        """Load template configuration and files."""
        template_path = self.templates_dir / template_type
        
        if not template_path.exists():
            available = ", ".join(self.list_templates())
            raise DuggerBootError(
                f"Template '{template_type}' not found. Available: {available}"
            )
        
        # Load template manifest
        manifest_path = template_path / "template.yaml"
        if not manifest_path.exists():
            raise DuggerBootError(f"Template '{template_type}' missing template.yaml")
        
        # For now, return a basic structure
        # In a full implementation, we'd parse the YAML
        return {
            "structure": ["src", "tests", "docs"],
            "files": self._get_template_files(template_path),
        }
    
    def _get_template_files(self, template_path: Path) -> Dict[str, str]:
        """Get all template files and their contents."""
        files = {}
        
        # Walk through template directory
        for file_path in template_path.rglob("*"):
            if file_path.is_file() and file_path.name != "template.yaml":
                # Get relative path from template directory
                rel_path = file_path.relative_to(template_path)
                files[str(rel_path)] = file_path.read_text()
        
        return files
    
    def _create_directory_structure(self, project_path: Path, structure: List[str]) -> None:
        """Create the basic directory structure."""
        # Remove existing directory if force is enabled
        if project_path.exists():
            shutil.rmtree(project_path)
        
        # Create project directory
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        for dir_name in structure:
            (project_path / dir_name).mkdir(exist_ok=True)
    
    def _render_files(self, project_path: Path, template_path: Path, context: Dict[str, Any]) -> None:
        """Render template files and write to project directory."""
        env = Environment(loader=FileSystemLoader(str(template_path)))
        
        # Walk through template directory
        for file_path in template_path.rglob("*"):
            if file_path.is_file() and file_path.name != "template.yaml":
                # Get relative path from template directory
                rel_path = file_path.relative_to(template_path)
                
                # Read template content
                content = file_path.read_text()
                
                # Render content with Jinja2 if it's a template file
                if file_path.suffix == ".j2":
                    template = env.get_template(str(rel_path))
                    rendered = template.render(**context)
                    # Remove .j2 extension for output file
                    output_path = project_path / str(rel_path)[:-3]
                else:
                    # Copy non-template files as-is
                    rendered = content
                    output_path = project_path / rel_path
                
                # Write to project directory
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding='utf-8')
    
    def _validate_dna(self, dugger_yaml_path: Path) -> None:
        """Validate generated dugger.yaml against DLT Project schema."""
        if not dugger_yaml_path.exists():
            raise DuggerBootError("dugger.yaml was not generated.")
        
        try:
            # Load and validate against DLT Project model
            project_data = Project.from_file(dugger_yaml_path)
            console.print(f"✅ DNA validation passed for {project_data.name}")
        except Exception as e:
            raise DuggerBootError(f"DNA validation failed: {e}")
    
    def _initialize_git(self, project_path: Path, project_name: str) -> None:
        """Initialize Git repository and make initial commit."""
        try:
            # Initialize git repository
            subprocess.run(
                ["git", "init"],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            
            # Add all files
            subprocess.run(
                ["git", "add", "."],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            
            # Make initial commit
            commit_message = f"chore: initial bootstrap of {project_name}"
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            
        except Exception as e:
            raise DuggerBootError(f"Git initialization failed: {e}") from e

    def retrofit_project(
        self,
        project_path: Path,
        project_name: str,
        overwrite_ide: bool = False,
    ) -> dict[str, bool]:
        """Retrofit existing project with DLT DNA using DLT's RetrofitEngine.
        
        Args:
            project_path: Path to existing project
            project_name: Name of the project
            overwrite_ide: Whether to overwrite existing IDE files
            
        Returns:
            Dictionary of actions performed
        """
        try:
            retrofit_engine = RetrofitEngine(project_path)
            return retrofit_engine.retrofit_project(
                project_name=project_name,
                overwrite_ide=overwrite_ide,
            )
        except Exception as e:
            raise DuggerBootError(f"Retrofit failed: {e}") from e


# Import console for validation feedback
from rich.console import Console
console = Console()