"""
Project Scout - Historical Indexer for the Dugger ecosystem.

Intelligent repository analysis for code recycling and harvestable component identification.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from loguru import logger
from rich.console import Console
from rich.table import Table

from duggerlink.models.inventory import (
    DNAStatus,
    EcosystemInventory,
    HarvestCandidate,
    ProjectFamily,
    ProjectInventory,
    ProjectMetrics,
    ProjectStack,
)

console = Console()


class ProjectScout:
    """Intelligent project analyzer for ecosystem-wide code recycling."""
    
    # Pattern matching for utility detection
    UTILITY_PATTERNS = {
        "api_client": [
            r"api.*client",
            r"client.*api",
            r".*api\.py$",
            r".*client\.py$",
        ],
        "scraper": [
            r"scrape",
            r"crawl",
            r"spider",
            r".*scraper\.py$",
        ],
        "config": [
            r"config",
            r"settings",
            r".*config\.py$",
            r".*settings\.py$",
        ],
        "utils": [
            r"utils?/",
            r"helpers?/",
            r".*utils?\.py$",
            r".*helpers?\.py$",
        ],
        "data_processing": [
            r"process",
            r"transform",
            r"parse",
            r".*processor\.py$",
        ],
    }
    
    # File extension patterns for stack detection
    STACK_PATTERNS = {
        ProjectStack.PYTHON: [".py", "requirements.txt", "pyproject.toml", "setup.py"],
        ProjectStack.CHROME_EXTENSION: ["manifest.json", "background.js", "content.js"],
        ProjectStack.JAVASCRIPT: [".js", "package.json", ".jsx"],
        ProjectStack.TYPESCRIPT: [".ts", ".tsx", "tsconfig.json"],
    }
    
    # High-value file patterns
    HIGH_VALUE_PATTERNS = [
        r".*\.py$",  # Python files
        r".*\.js$",  # JavaScript files
        r"manifest\.json$",  # Chrome manifests
        r".*config\..*$",  # Configuration files
        r".*client\..*$",  # API clients
        r".*scraper\..*$",  # Scrapers
    ]
    
    def __init__(self, ecosystem_root: Path):
        """Initialize ProjectScout.
        
        Args:
            ecosystem_root: Root directory containing all projects (e.g., C:\GitHub)
        """
        self.ecosystem_root = ecosystem_root
        self.logger = logger.bind(component="ProjectScout")
    
    def scan_ecosystem(self, suggest_recycle: bool = False) -> EcosystemInventory:
        """Perform complete ecosystem scan.
        
        Args:
            suggest_recycle: Whether to suggest retrofit commands
            
        Returns:
            Complete ecosystem inventory
        """
        self.logger.info(f"Starting ecosystem scan of {self.ecosystem_root}")
        
        # Discover all project directories
        project_dirs = self._discover_projects()
        self.logger.info(f"Found {len(project_dirs)} project directories")
        
        # Analyze each project
        projects = []
        for project_dir in project_dirs:
            try:
                project = self._analyze_project(project_dir)
                projects.append(project)
                self.logger.info(f"Analyzed {project.name}: {project.stack} - {project.dna_status}")
            except Exception as e:
                self.logger.error(f"Failed to analyze {project_dir}: {e}")
        
        # Create ecosystem inventory
        inventory = EcosystemInventory(
            total_projects=len(projects),
            projects=projects,
        )
        
        # Generate retrofit suggestions if requested
        if suggest_recycle:
            self._suggest_retrofit_commands(inventory)
        
        self.logger.info(f"Ecosystem scan complete: {len(projects)} projects analyzed")
        return inventory
    
    def _discover_projects(self) -> List[Path]:
        """Discover project directories using fast os.scandir().
        
        Returns:
            List of project directory paths
        """
        project_dirs = []
        
        try:
            with os.scandir(self.ecosystem_root) as entries:
                for entry in entries:
                    if not entry.is_dir() or entry.name.startswith('.'):
                        continue
                    
                    project_path = Path(entry.path)
                    
                    # Fast detection: if it has .git or signature files, it's a project
                    if (project_path / '.git').exists():
                        project_dirs.append(project_path)
                        continue
                    
                    # Check for signature files in root only (shallow detection)
                    signature_files = [
                        'manifest.json',
                        'pyproject.toml',
                        'requirements.txt',
                        'package.json',
                        'dugger.yaml',
                        'setup.py'
                    ]
                    
                    if any((project_path / sig).exists() for sig in signature_files):
                        project_dirs.append(project_path)
                        
        except PermissionError:
            self.logger.warning(f"Permission denied scanning {self.ecosystem_root}")
        except Exception as e:
            self.logger.error(f"Error scanning {self.ecosystem_root}: {e}")
        
        return project_dirs
    
    def _has_project_indicators(self, path: Path) -> bool:
        """Check if directory has project indicator files.
        
        Args:
            path: Directory path to check
            
        Returns:
            True if directory looks like a project
        """
        indicators = [
            "pyproject.toml",
            "package.json",
            "manifest.json",
            "setup.py",
            "requirements.txt",
            "dugger.yaml",
        ]
        
        return any((path / indicator).exists() for indicator in indicators)
    
    def _analyze_project(self, project_dir: Path) -> ProjectInventory:
        """Analyze a single project directory.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            Project inventory analysis
        """
        # Basic project info
        name = project_dir.name
        
        # Detect stack
        stack = self._detect_stack(project_dir)
        
        # Detect family
        family = self._detect_family(project_dir, name)
        
        # Check DNA status
        dna_status = self._check_dna_status(project_dir)
        
        # Calculate metrics
        metrics = self._calculate_metrics(project_dir)
        
        # Find harvest candidates
        harvest_candidates = self._find_harvest_candidates(project_dir)
        
        # Detect dependencies
        dependencies = self._detect_dependencies(project_dir, stack)
        
        # Quality indicators
        quality_indicators = self._assess_quality(project_dir)
        
        return ProjectInventory(
            name=name,
            path=project_dir,
            stack=stack,
            family=family,
            dna_status=dna_status,
            metrics=metrics,
            harvest_candidates=harvest_candidates,
            dependencies=dependencies,
            quality_indicators=quality_indicators,
        )
    
    def _detect_stack(self, project_dir: Path) -> ProjectStack:
        """Detect the technology stack of a project.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            Detected project stack
        """
        stack_scores = {stack: 0 for stack in ProjectStack}
        
        # Count files matching each stack pattern
        for stack, patterns in self.STACK_PATTERNS.items():
            for pattern in patterns:
                matches = list(project_dir.rglob(pattern))
                stack_scores[stack] += len(matches)
        
        # Find stack with highest score
        best_stack = max(stack_scores, key=stack_scores.get)
        
        # Return best stack if it has matches, otherwise unknown
        return best_stack if stack_scores[best_stack] > 0 else ProjectStack.UNKNOWN
    
    def _detect_family(self, project_dir: Path, name: str) -> ProjectFamily:
        """Detect project family based on name and content.
        
        Args:
            project_dir: Project directory path
            name: Project name
            
        Returns:
            Detected project family
        """
        name_lower = name.lower()
        
        # Name-based detection
        if any(keyword in name_lower for keyword in ["arbiter", "trading", "market"]):
            return ProjectFamily.TRADING
        elif any(keyword in name_lower for keyword in ["extension", "chrome"]):
            return ProjectFamily.EXTENSIONS
        elif any(keyword in name_lower for keyword in ["automation", "scraper", "bot"]):
            return ProjectFamily.AUTOMATION
        elif any(keyword in name_lower for keyword in ["data", "analytics", "report"]):
            return ProjectFamily.DATA_ANALYTICS
        elif any(keyword in name_lower for keyword in ["web", "site", "page"]):
            return ProjectFamily.WEB_TOOLS
        elif any(keyword in name_lower for keyword in ["util", "helper", "tool"]):
            return ProjectFamily.UTILITIES
        
        # Content-based detection
        if (project_dir / "manifest.json").exists():
            return ProjectFamily.EXTENSIONS
        
        return ProjectFamily.UNKNOWN
    
    def _check_dna_status(self, project_dir: Path) -> DNAStatus:
        """Check DLT DNA validation status.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            DNA validation status
        """
        dugger_yaml = project_dir / "dugger.yaml"
        
        if not dugger_yaml.exists():
            return DNAStatus.MISSING
        
        try:
            # Try to validate with DLT Project model
            from duggerlink.models.project import DuggerProject
            project = DuggerProject.from_file(dugger_yaml)
            return DNAStatus.VALID
        except Exception as e:
            self.logger.debug(f"DNA validation failed for {project_dir}: {e}")
            return DNAStatus.INVALID
    
    def _calculate_metrics(self, project_dir: Path) -> ProjectMetrics:
        """Calculate project metrics.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            Project metrics
        """
        total_files = 0
        code_files = 0
        test_files = 0
        config_files = 0
        documentation_files = 0
        lines_of_code = 0
        
        # Walk through all files
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                total_files += 1
                
                # Categorize files
                if file_path.suffix in [".py", ".js", ".ts", ".jsx", ".tsx"]:
                    code_files += 1
                    try:
                        with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                            lines_of_code += len(f.readlines())
                    except Exception:
                        pass
                
                elif "test" in file_path.name.lower():
                    test_files += 1
                
                elif file_path.name in ["config", "settings", "manifest", "package"]:
                    config_files += 1
                
                elif file_path.suffix in [".md", ".rst", ".txt"]:
                    documentation_files += 1
        
        # Get git info
        git_commits = self._get_git_commit_count(project_dir)
        last_modified = self._get_last_modified(project_dir)
        
        # Calculate complexity score (simplified)
        complexity_score = min(lines_of_code / 10000, 1.0)
        
        # Determine if actively developed
        days_since_modified = (datetime.now() - last_modified).days
        active_development = days_since_modified < 90 and git_commits > 5
        
        return ProjectMetrics(
            total_files=total_files,
            code_files=code_files,
            test_files=test_files,
            config_files=config_files,
            documentation_files=documentation_files,
            lines_of_code=lines_of_code,
            complexity_score=complexity_score,
            last_modified=last_modified,
            git_commits=git_commits,
            active_development=active_development,
        )
    
    def _find_harvest_candidates(self, project_dir: Path) -> List[HarvestCandidate]:
        """Find harvestable components in project.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            List of harvest candidates
        """
        candidates = []
        
        for file_path in project_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Check if file matches high-value patterns
            if not self._is_high_value_file(file_path):
                continue
            
            # Calculate scores
            complexity_score = self._calculate_complexity_score(file_path)
            utility_score = self._calculate_utility_score(file_path)
            uniqueness_score = self._calculate_uniqueness_score(file_path)
            
            # Overall harvest score
            harvest_score = (complexity_score + utility_score + uniqueness_score) / 3
            
            # Only include if harvestable
            if harvest_score > 0.5:
                tags = self._extract_file_tags(file_path)
                dependencies = self._extract_file_dependencies(file_path)
                
                candidates.append(HarvestCandidate(
                    file_path=file_path.relative_to(project_dir),
                    file_type=file_path.suffix,
                    complexity_score=complexity_score,
                    utility_score=utility_score,
                    uniqueness_score=uniqueness_score,
                    harvest_score=harvest_score,
                    tags=tags,
                    dependencies=dependencies,
                ))
        
        # Sort by harvest score
        candidates.sort(key=lambda hc: hc.harvest_score, reverse=True)
        return candidates[:10]  # Top 10 candidates per project
    
    def _is_high_value_file(self, file_path: Path) -> bool:
        """Check if file is potentially high-value.
        
        Args:
            file_path: File path to check
            
        Returns:
            True if file is high-value
        """
        # Check against high-value patterns
        for pattern in self.HIGH_VALUE_PATTERNS:
            if re.search(pattern, file_path.name, re.IGNORECASE):
                return True
        
        # Check file size (larger files might be more valuable)
        try:
            if file_path.stat().st_size > 1000:  # > 1KB
                return True
        except Exception:
            pass
        
        return False
    
    def _calculate_complexity_score(self, file_path: Path) -> float:
        """Calculate complexity score for a file.
        
        Args:
            file_path: File path to analyze
            
        Returns:
            Complexity score (0.0 to 1.0)
        """
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = len(content.splitlines())
                
                # Simple complexity based on lines and unique constructs
                if file_path.suffix == ".py":
                    functions = len(re.findall(r"def\s+\w+", content))
                    classes = len(re.findall(r"class\s+\w+", content))
                    imports = len(re.findall(r"^(import|from)\s+", content, re.MULTILINE))
                    
                    complexity = min((functions * 0.3 + classes * 0.4 + imports * 0.2 + lines / 1000 * 0.1), 1.0)
                else:
                    # For other files, use line count as proxy
                    complexity = min(lines / 500, 1.0)
                
                return complexity
        except Exception:
            return 0.0
    
    def _calculate_utility_score(self, file_path: Path) -> float:
        """Calculate utility score based on filename patterns.
        
        Args:
            file_path: File path to analyze
            
        Returns:
            Utility score (0.0 to 1.0)
        """
        name = file_path.name.lower()
        
        # Check utility patterns
        for category, patterns in self.UTILITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    return 0.8  # High utility for pattern matches
        
        # Check for common utility indicators
        utility_keywords = ["util", "helper", "tool", "service", "client", "api"]
        if any(keyword in name for keyword in utility_keywords):
            return 0.6
        
        return 0.3  # Base utility score
    
    def _calculate_uniqueness_score(self, file_path: Path) -> float:
        """Calculate uniqueness score (simplified heuristic).
        
        Args:
            file_path: File path to analyze
            
        Returns:
            Uniqueness score (0.0 to 1.0)
        """
        # For now, use file size and name uniqueness as proxy
        try:
            size_score = min(file_path.stat().st_size / 10000, 1.0)
            
            # Penalize common filenames
            common_names = ["index.js", "main.py", "app.py", "utils.py", "config.py"]
            name_penalty = 0.3 if file_path.name in common_names else 0.0
            
            return max(0.0, size_score - name_penalty)
        except Exception:
            return 0.0
    
    def _extract_file_tags(self, file_path: Path) -> Set[str]:
        """Extract tags from file based on patterns.
        
        Args:
            file_path: File path to analyze
            
        Returns:
            Set of tags
        """
        tags = set()
        name = file_path.name.lower()
        
        for category, patterns in self.UTILITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    tags.add(category)
        
        return tags
    
    def _extract_file_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from file (simplified).
        
        Args:
            file_path: File path to analyze
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
                if file_path.suffix == ".py":
                    # Extract imports
                    imports = re.findall(r"^(?:import|from)\s+(\w+)", content, re.MULTILINE)
                    dependencies.extend(imports)
                
                elif file_path.suffix == ".js":
                    # Extract require/import statements
                    imports = re.findall(r"(?:require|import)\s+[\"']([^\"']+)[\"']", content)
                    dependencies.extend(imports)
        except Exception:
            pass
        
        return list(set(dependencies))[:5]  # Top 5 dependencies
    
    def _detect_dependencies(self, project_dir: Path, stack: ProjectStack) -> Dict[str, str]:
        """Detect project dependencies.
        
        Args:
            project_dir: Project directory path
            stack: Project stack
            
        Returns:
            Dictionary of dependencies
        """
        dependencies = {}
        
        if stack == ProjectStack.PYTHON:
            # Check requirements.txt
            req_file = project_dir / "requirements.txt"
            if req_file.exists():
                try:
                    with req_file.open("r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0]
                                dependencies[pkg_name] = line
                except Exception:
                    pass
            
            # Check pyproject.toml
            pyproject_file = project_dir / "pyproject.toml"
            if pyproject_file.exists():
                try:
                    with pyproject_file.open("r") as f:
                        content = f.read()
                        # Simple regex for dependencies
                        deps = re.findall(r"^\s*([a-zA-Z0-9\-_]+)\s*=", content, re.MULTILINE)
                        for dep in deps:
                            dependencies[dep] = "pyproject.toml"
                except Exception:
                    pass
        
        elif stack in [ProjectStack.JAVASCRIPT, ProjectStack.TYPESCRIPT]:
            # Check package.json
            package_file = project_dir / "package.json"
            if package_file.exists():
                try:
                    with package_file.open("r") as f:
                        package_data = json.load(f)
                        deps = package_data.get("dependencies", {})
                        dependencies.update(deps)
                except Exception:
                    pass
        
        return dependencies
    
    def _assess_quality(self, project_dir: Path) -> Dict[str, bool]:
        """Assess project quality indicators.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            Dictionary of quality indicators
        """
        indicators = {}
        
        # Has tests
        indicators["has_tests"] = any("test" in f.name.lower() for f in project_dir.rglob("*") if f.is_file())
        
        # Has documentation
        indicators["has_docs"] = any(f.suffix in [".md", ".rst"] for f in project_dir.rglob("*") if f.is_file())
        
        # Has configuration management
        indicators["has_config"] = any(
            f.name in ["config.py", "settings.py", ".env.example", "config.json"]
            for f in project_dir.rglob("*") if f.is_file()
        )
        
        # Has version control
        indicators["has_git"] = (project_dir / ".git").exists()
        
        # Has CI/CD
        indicators["has_ci"] = any(
            f.name in [".github", ".gitlab-ci.yml", ".travis.yml", "Jenkinsfile"]
            for f in project_dir.iterdir() if f.is_dir() or f.is_file()
        )
        
        return indicators
    
    def _get_git_commit_count(self, project_dir: Path) -> int:
        """Get git commit count for project.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            Number of commits
        """
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-list", "HEAD", "--count"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception:
            pass
        
        return 0
    
    def _get_last_modified(self, project_dir: Path) -> datetime:
        """Get last modification date for project.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            Last modified datetime
        """
        try:
            latest_time = 0
            for file_path in project_dir.rglob("*"):
                if file_path.is_file():
                    file_time = file_path.stat().st_mtime
                    if file_time > latest_time:
                        latest_time = file_time
            
            return datetime.fromtimestamp(latest_time)
        except Exception:
            return datetime.now()
    
    def _suggest_retrofit_commands(self, inventory: EcosystemInventory) -> None:
        """Generate retrofit suggestions for projects.
        
        Args:
            inventory: Ecosystem inventory
        """
        console.print("\n[bold blue]Retrofit Suggestions:[/bold blue]\n")
        
        for project in inventory.retrofit_candidates[:5]:  # Top 5
            cmd = f"dbt-init {project.name} --retrofit --force"
            console.print(f"  📦 {project.name} (Priority: {project.retrofit_priority:.2f})")
            console.print(f"     {cmd}")
            console.print(f"     Status: {project.dna_status.value} | Stack: {project.stack.value}")
            console.print("")
    
    def generate_ecosystem_map(self, inventory: EcosystemInventory, output_path: Path) -> None:
        """Generate ECOSYSTEM_MAP.md with project analysis.
        
        Args:
            inventory: Ecosystem inventory
            output_path: Output file path
        """
        content = f"""# Dugger Ecosystem Map

**Generated on:** {inventory.scan_date.strftime("%Y-%m-%d %H:%M:%S")}
**Total Projects:** {inventory.total_projects}

## Ecosystem Overview

### Stack Distribution
"""
        
        for stack, count in inventory.stack_distribution.items():
            content += f"- **{stack.value}**: {count} projects\n"
        
        content += "\n### Family Distribution\n"
        for family, count in inventory.family_distribution.items():
            content += f"- **{family.value}**: {count} projects\n"
        
        content += "\n### DNA Status Distribution\n"
        for status, count in inventory.dna_status_distribution.items():
            content += f"- **{status.value}**: {count} projects\n"
        
        content += "\n## Project Families\n\n"
        
        # Group projects by family
        by_family = {}
        for project in inventory.projects:
            if project.family not in by_family:
                by_family[project.family] = []
            by_family[project.family].append(project)
        
        for family, projects in by_family.items():
            content += f"### {family.value.title()} ({len(projects)} projects)\n\n"
            
            for project in sorted(projects, key=lambda p: p.name):
                status_emoji = "✅" if project.dna_status == DNAStatus.VALID else "⚠️"
                content += f"- {status_emoji} **{project.name}** ({project.stack.value})\n"
                content += f"  - Path: `{project.path}`\n"
                content += f"  - DNA: {project.dna_status.value}\n"
                content += f"  - Files: {project.metrics.code_files} code, {project.metrics.test_files} tests\n"
                if project.harvest_candidates:
                    content += f"  - Harvestable: {len(project.harvest_candidates)} components\n"
                content += "\n"
            
            content += "\n"
        
        # Add top harvest candidates
        if inventory.top_harvest_candidates:
            content += "## Top Harvest Candidates\n\n"
            for i, candidate in enumerate(inventory.top_harvest_candidates[:10], 1):
                content += f"{i}. **{candidate.file_path}** (Score: {candidate.harvest_score:.2f})\n"
                content += f"   - Tags: {', '.join(candidate.tags)}\n"
                content += f"   - Dependencies: {', '.join(candidate.dependencies[:3])}\n"
                content += "\n"
        
        # Add retrofit suggestions
        if inventory.retrofit_candidates:
            content += "## Retrofit Candidates\n\n"
            for project in inventory.retrofit_candidates[:5]:
                content += f"- **{project.name}** (Priority: {project.retrofit_priority:.2f})\n"
                content += f"  ```bash\n  dbt-init {project.name} --retrofit --force\n  ```\n"
                content += "\n"
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        
        self.logger.info(f"Ecosystem map generated: {output_path}")
    
    def inject_commit_stubs(self, dry_run: bool = False) -> Dict[str, bool]:
        """Inject ADR-003 commit.py bridge stubs into all projects.
        
        Args:
            dry_run: If True, only report what would be done without actually injecting
            
        Returns:
            Dictionary mapping project names to injection success status
        """
        self.logger.info("Starting ADR-003 commit.py bridge injection")
        
        # Discover all project directories using high-speed scan
        project_dirs = self._discover_projects()
        injection_results = {}
        
        # ADR-003 Bridge Stub content
        bridge_stub = '''try:
    from duggerlink.cli.commit import main
except ImportError:
    print("❌ DuggerLinkTools not found. Run: pip install -e C:\\\\Github\\\\DuggerLinkTools")
    exit(1)

if __name__ == "__main__":
    main()
'''
        
        for project_dir in project_dirs:
            commit_file = project_dir / "commit.py"
            
            try:
                # Check if commit.py already exists
                if commit_file.exists():
                    self.logger.info(f"commit.py already exists in {project_dir.name}")
                    injection_results[project_dir.name] = False
                    continue
                
                if not dry_run:
                    # Inject the ADR-003 commit.py bridge
                    commit_file.write_text(bridge_stub, encoding="utf-8")
                    self.logger.info(f"Injected ADR-003 bridge into {project_dir.name}")
                else:
                    self.logger.info(f"Would inject ADR-003 bridge into {project_dir.name} (dry run)")
                
                injection_results[project_dir.name] = True
                
            except Exception as e:
                self.logger.error(f"Failed to inject commit.py into {project_dir.name}: {e}")
                injection_results[project_dir.name] = False
        
        successful = sum(1 for success in injection_results.values() if success)
        self.logger.info(f"ADR-003 Bridge injection complete: {successful}/{len(project_dirs)} projects updated")
        
        return injection_results
    
    def display_summary(self, inventory: EcosystemInventory) -> None:
        """Display ecosystem summary in console.
        
        Args:
            inventory: Ecosystem inventory
        """
        console.print(f"\n[bold green]Ecosystem Scan Complete[/bold green]")
        console.print(f"📊 Total Projects: {inventory.total_projects}")
        console.print(f"🔍 Top Harvest Candidates: {len(inventory.top_harvest_candidates)}")
        console.print(f"🔧 Retrofit Candidates: {len(inventory.retrofit_candidates)}")
        
        # Show top projects by harvest potential
        if inventory.top_harvest_candidates:
            console.print("\n[bold blue]Top Harvest Candidates:[/bold blue]\n")
            
            table = Table()
            table.add_column("File", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Tags", style="green")
            
            for candidate in inventory.top_harvest_candidates[:5]:
                table.add_row(
                    str(candidate.file_path),
                    f"{candidate.harvest_score:.2f}",
                    ", ".join(candidate.tags)
                )
            
            console.print(table)
        
        # Show top projects by harvest potential
        if inventory.top_harvest_candidates:
            console.print("\n[bold blue]Top Harvest Candidates:[/bold blue]\n")
            
            table = Table()
            table.add_column("File", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Tags", style="green")
            
            for candidate in inventory.top_harvest_candidates[:5]:
                table.add_row(
                    str(candidate.file_path),
                    f"{candidate.harvest_score:.2f}",
                    ", ".join(candidate.tags)
                )
            
            console.print(table)