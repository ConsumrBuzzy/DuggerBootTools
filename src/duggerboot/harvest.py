"""
Harvest Engine - Component extraction and registration for DuggerBootTools.

Intelligent code harvesting from existing projects for template registry population.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set

from loguru import logger
from rich.console import Console
from rich.table import Table

from .exceptions import DuggerBootError

console = Console()


class HarvestEngine:
    """Engine for harvesting reusable components from existing projects."""
    
    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize HarvestEngine.
        
        Args:
            registry_path: Path to component registry directory
        """
        self.registry_path = registry_path or Path.cwd() / "components"
        self.logger = logger.bind(component="HarvestEngine")
    
    def harvest_component(
        self,
        source_path: Path,
        component_name: str,
        component_type: str,
        description: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """Harvest a single component from source project.
        
        Args:
            source_path: Path to source file or directory
            component_name: Name for the harvested component
            component_type: Type of component (python, chrome, shared, etc.)
            description: Optional description of the component
            force: Force overwrite if component exists
            
        Returns:
            True if harvest successful, False otherwise
        """
        try:
            # Validate source path
            if not source_path.exists():
                raise DuggerBootError(f"Source path does not exist: {source_path}")
            
            # Determine component category
            category = self._categorize_component(source_path, component_type)
            
            # Create component destination
            component_dir = self.registry_path / category / component_name
            if component_dir.exists() and not force:
                raise DuggerBootError(f"Component already exists: {component_dir}")
            
            # Extract metadata
            metadata = self._extract_metadata(source_path, component_name, description)
            
            # Copy component files
            self._copy_component_files(source_path, component_dir)
            
            # Save component manifest
            self._save_component_manifest(component_dir, metadata)
            
            self.logger.info(f"Harvested component: {component_name} ({category})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to harvest {component_name}: {e}")
            return False
    
    def harvest_project(
        self,
        project_path: Path,
        harvest_rules: Optional[Dict[str, List[str]]] = None,
        force: bool = False,
    ) -> Dict[str, bool]:
        """Harvest multiple components from a project.
        
        Args:
            project_path: Path to project directory
            harvest_rules: Rules for what to harvest (file patterns)
            force: Force overwrite existing components
            
        Returns:
            Dictionary of component names and harvest success status
        """
        results = {}
        
        # Default harvest rules
        if harvest_rules is None:
            harvest_rules = {
                "utils": ["utils/**/*.py", "helpers/**/*.py", "lib/**/*.py"],
                "clients": ["*client*.py", "*api*.py"],
                "scrapers": ["*scrape*.py", "*crawl*.py", "*spider*.py"],
                "config": ["config*.py", "settings*.py", "*.yaml", "*.yml"],
                "chrome": ["manifest.json", "background.js", "content.js"],
            }
        
        for category, patterns in harvest_rules.items():
            for pattern in patterns:
                matches = list(project_path.rglob(pattern))
                
                for match in matches:
                    component_name = f"{category}_{match.stem}"
                    success = self.harvest_component(
                        source_path=match,
                        component_name=component_name,
                        component_type=category,
                        force=force,
                    )
                    results[component_name] = success
        
        return results
    
    def list_components(self) -> Dict[str, List[Dict]]:
        """List all harvested components in the registry.
        
        Returns:
            Dictionary of component categories and their components
        """
        components = {}
        
        if not self.registry_path.exists():
            return components
        
        for category_dir in self.registry_path.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            components[category] = []
            
            for component_dir in category_dir.iterdir():
                if not component_dir.is_dir():
                    continue
                
                # Load component manifest
                manifest_path = component_dir / "component.json"
                if manifest_path.exists():
                    try:
                        with manifest_path.open("r") as f:
                            manifest = json.load(f)
                        components[category].append(manifest)
                    except Exception as e:
                        self.logger.warning(f"Failed to load manifest for {component_dir}: {e}")
        
        return components
    
    def get_component(self, category: str, name: str) -> Optional[Dict]:
        """Get component metadata by category and name.
        
        Args:
            category: Component category
            name: Component name
            
        Returns:
            Component metadata or None if not found
        """
        component_dir = self.registry_path / category / name
        manifest_path = component_dir / "component.json"
        
        if not manifest_path.exists():
            return None
        
        try:
            with manifest_path.open("r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load component manifest: {e}")
            return None
    
    def _categorize_component(self, source_path: Path, component_type: str) -> str:
        """Determine component category based on path and type.
        
        Args:
            source_path: Path to source component
            component_type: Specified component type
            
        Returns:
            Component category
        """
        # Use specified type if valid
        valid_categories = ["python", "chrome", "shared", "utils", "clients", "scrapers", "config"]
        if component_type in valid_categories:
            return component_type
        
        # Auto-categorize based on file patterns
        if source_path.suffix == ".py":
            return "python"
        elif source_path.suffix == ".js":
            return "chrome"
        elif source_path.name == "manifest.json":
            return "chrome"
        elif source_path.name in ["config.py", "settings.py"]:
            return "config"
        else:
            return "shared"
    
    def _extract_metadata(
        self,
        source_path: Path,
        component_name: str,
        description: Optional[str],
    ) -> Dict:
        """Extract metadata from source component.
        
        Args:
            source_path: Path to source component
            component_name: Component name
            description: Optional description
            
        Returns:
            Component metadata dictionary
        """
        metadata = {
            "name": component_name,
            "source_path": str(source_path),
            "harvested_at": str(Path.cwd()),
            "description": description or f"Harvested from {source_path.name}",
            "files": [],
            "dependencies": [],
            "tags": set(),
            "quality_score": 0.0,
        }
        
        # Analyze files
        if source_path.is_file():
            metadata["files"].append(source_path.name)
            metadata.update(self._analyze_file(source_path))
        else:
            for file_path in source_path.rglob("*"):
                if file_path.is_file():
                    metadata["files"].append(str(file_path.relative_to(source_path)))
                    file_analysis = self._analyze_file(file_path)
                    metadata["dependencies"].extend(file_analysis.get("dependencies", []))
        
        # Remove duplicates and convert sets
        metadata["dependencies"] = list(set(metadata["dependencies"]))
        metadata["tags"] = list(metadata["tags"])
        
        return metadata
    
    def _analyze_file(self, file_path: Path) -> Dict:
        """Analyze a file for dependencies and quality indicators.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            File analysis results
        """
        analysis = {
            "dependencies": [],
            "tags": set(),
            "quality_score": 0.0,
            "lines_of_code": 0,
        }
        
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.splitlines()
                analysis["lines_of_code"] = len(lines)
                
                if file_path.suffix == ".py":
                    # Extract Python imports
                    import re
                    
                    # Standard imports
                    imports = re.findall(r"^(?:import|from)\s+(\w+)", content, re.MULTILINE)
                    analysis["dependencies"].extend(imports)
                    
                    # Look for TODO/FIXME comments
                    if re.search(r"#\s*(TODO|FIXME|NOTE)", content, re.IGNORECASE):
                        analysis["tags"].add("has_todos")
                    
                    # Look for class/function definitions
                    if re.search(r"def\s+\w+", content):
                        analysis["tags"].add("has_functions")
                    if re.search(r"class\s+\w+", content):
                        analysis["tags"].add("has_classes")
                    
                    # Quality score based on structure
                    score = 0.0
                    if len(imports) > 0:
                        score += 0.2
                    if analysis["lines_of_code"] > 10:
                        score += 0.3
                    if "has_functions" in analysis["tags"]:
                        score += 0.3
                    if "has_classes" in analysis["tags"]:
                        score += 0.2
                    analysis["quality_score"] = min(score, 1.0)
                
                elif file_path.suffix == ".js":
                    # Extract JavaScript imports/requires
                    imports = re.findall(r"(?:import|require)\s+[\"']([^\"']+)[\"']", content)
                    analysis["dependencies"].extend(imports)
                    
                    # Look for function definitions
                    if re.search(r"function\s+\w+", content):
                        analysis["tags"].add("has_functions")
                    
                    # Quality score
                    score = 0.0
                    if len(imports) > 0:
                        score += 0.3
                    if analysis["lines_of_code"] > 10:
                        score += 0.4
                    if "has_functions" in analysis["tags"]:
                        score += 0.3
                    analysis["quality_score"] = min(score, 1.0)
                
                elif file_path.name == "manifest.json":
                    analysis["tags"].add("chrome_manifest")
                    try:
                        manifest_data = json.loads(content)
                        if manifest_data.get("manifest_version") == 3:
                            analysis["tags"].add("manifest_v3")
                        analysis["dependencies"] = list(manifest_data.get("permissions", []))
                        analysis["quality_score"] = 0.8  # High score for manifests
                    except json.JSONDecodeError:
                        pass
        
        except Exception as e:
            self.logger.warning(f"Failed to analyze {file_path}: {e}")
        
        return analysis
    
    def _copy_component_files(self, source_path: Path, dest_dir: Path) -> None:
        """Copy component files to destination directory.
        
        Args:
            source_path: Source file or directory
            dest_dir: Destination directory
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        if source_path.is_file():
            shutil.copy2(source_path, dest_dir / source_path.name)
        else:
            shutil.copytree(source_path, dest_dir / source_path.name, dirs_exist_ok=True)
    
    def _save_component_manifest(self, component_dir: Path, metadata: Dict) -> None:
        """Save component manifest file.
        
        Args:
            component_dir: Component directory
            metadata: Component metadata
        """
        manifest_path = component_dir / "component.json"
        
        with manifest_path.open("w") as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def display_components(self) -> None:
        """Display all components in a formatted table."""
        components = self.list_components()
        
        if not components:
            console.print("No components found in registry.")
            return
        
        console.print(f"\n[bold blue]Component Registry ({self.registry_path})[/bold blue]\n")
        
        for category, component_list in components.items():
            console.print(f"[bold]{category.title()}:[/bold]")
            
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Files", justify="right")
            table.add_column("Quality", justify="right")
            table.add_column("Tags", style="green")
            
            for component in component_list:
                table.add_row(
                    component["name"],
                    str(len(component["files"])),
                    f"{component['quality_score']:.2f}",
                    ", ".join(component["tags"][:3])  # Show first 3 tags
                )
            
            console.print(table)
            console.print()
    
    def search_components(self, query: str) -> List[Dict]:
        """Search components by name, description, or tags.
        
        Args:
            query: Search query
            
        Returns:
            List of matching components
        """
        results = []
        components = self.list_components()
        
        query_lower = query.lower()
        
        for category, component_list in components.items():
            for component in component_list:
                # Search in name, description, and tags
                if (
                    query_lower in component["name"].lower()
                    or query_lower in component["description"].lower()
                    or any(query_lower in tag.lower() for tag in component["tags"])
                ):
                    component["category"] = category
                    results.append(component)
        
        return results