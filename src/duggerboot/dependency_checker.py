"""
Dependency compatibility checker for DuggerBootTools.

Ensures template dependencies are compatible with current environment.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from packaging import version
from rich.console import Console

console = Console()


class DependencyChecker:
    """Validates dependency compatibility for templates and projects."""
    
    def __init__(self) -> None:
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    def check_template_compatibility(self, template_config: Dict) -> Tuple[bool, List[str]]:
        """Check if template dependencies are compatible with current environment."""
        issues = []
        
        # Check Python version requirement
        if "dependencies" in template_config and "python" in template_config["dependencies"]:
            python_req = template_config["dependencies"]["python"]
            if not self._check_python_version(python_req):
                issues.append(f"Python version {self.python_version} does not meet requirement: {python_req}")
        
        # Check DuggerLinkTools availability
        if "dependencies" in template_config and "duggerlink-tools" in template_config["dependencies"]:
            dlt_req = template_config["dependencies"]["duggerlink-tools"]
            dlt_version = self._get_package_version("duggerlink-tools")
            if dlt_version is None:
                issues.append("duggerlink-tools is not installed")
            elif not self._check_version_compatibility(dlt_version, dlt_req):
                issues.append(f"duggerlink-tools version {dlt_version} does not meet requirement: {dlt_req}")
        
        return len(issues) == 0, issues
    
    def check_project_dependencies(self, project_path: Path) -> Tuple[bool, List[str]]:
        """Check if project dependencies are satisfied."""
        pyproject_path = project_path / "pyproject.toml"
        
        if not pyproject_path.exists():
            return True, []
        
        # Parse pyproject.toml for dependencies
        try:
            import tomllib
            with open(pyproject_path, "rb") as f:
                pyproject = tomllib.load(f)
            
            dependencies = pyproject.get("project", {}).get("dependencies", [])
            issues = []
            
            for dep in dependencies:
                # Parse dependency name and version requirement
                dep_name, version_req = self._parse_dependency(dep)
                installed_version = self._get_package_version(dep_name)
                
                if installed_version is None:
                    issues.append(f"Dependency {dep_name} is not installed")
                elif version_req and not self._check_version_compatibility(installed_version, version_req):
                    issues.append(f"Dependency {dep_name} version {installed_version} does not meet requirement: {version_req}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            return False, [f"Failed to parse dependencies: {e}"]
    
    def _check_python_version(self, requirement: str) -> bool:
        """Check if current Python version meets requirement."""
        try:
            # Simple version comparison for >= requirements
            if requirement.startswith(">="):
                required_version = requirement[2:].strip()
                return version.parse(self.python_version) >= version.parse(required_version)
            elif requirement.startswith(">"):
                required_version = requirement[1:].strip()
                return version.parse(self.python_version) > version.parse(required_version)
            elif requirement.startswith("=="):
                required_version = requirement[2:].strip()
                return version.parse(self.python_version) == version.parse(required_version)
            else:
                # Exact match
                return self.python_version == requirement
        except Exception:
            return False
    
    def _get_package_version(self, package_name: str) -> str | None:
        """Get installed package version."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    return line.split(":")[1].strip()
        except subprocess.CalledProcessError:
            pass
        return None
    
    def _check_version_compatibility(self, installed: str, required: str) -> bool:
        """Check if installed version meets requirement."""
        try:
            if required.startswith(">="):
                required_version = required[2:].strip()
                return version.parse(installed) >= version.parse(required_version)
            elif required.startswith(">"):
                required_version = required[1:].strip()
                return version.parse(installed) > version.parse(required_version)
            elif required.startswith("=="):
                required_version = required[2:].strip()
                return version.parse(installed) == version.parse(required_version)
            else:
                return installed == required
        except Exception:
            return False
    
    def _parse_dependency(self, dep: str) -> Tuple[str, str | None]:
        """Parse dependency string into name and version requirement."""
        if ">=" in dep:
            parts = dep.split(">=")
            return parts[0].strip(), f">={parts[1].strip()}"
        elif ">" in dep:
            parts = dep.split(">")
            return parts[0].strip(), f">{parts[1].strip()}"
        elif "==" in dep:
            parts = dep.split("==")
            return parts[0].strip(), f"=={parts[1].strip()}"
        else:
            return dep.strip(), None
