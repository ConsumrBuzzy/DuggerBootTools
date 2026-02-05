# DuggerBootTools (DBT)

The "Ignition System" of the DuggerLinkTools ecosystem. Ensures every new project is "Born Valid" with full DLT DNA integration from second zero.

## 🧬 Architecture

### Core Components
- **The Forge**: Project directory scaffolding (src/, tests/, docs/)
- **The DNA Injector**: dugger.yaml generation validated against DLT Project schemas
- **The Spark**: Automatic Git initialization with semantic commits
- **The Tether**: Automatic dependency linking (duggerlink in pyproject.toml)

### Implementation Tiers
1. **Headlong**: `dbt-init [name]` - Direct CLI creation
2. **Template Registry**: Extensible template system
3. **Project Retrofit**: `dbt-upgrade` for existing projects

## 🚀 Quick Start

```bash
# Install DuggerBootTools
pip install duggerboot-tools

# Initialize a new project
dbt-init my-awesome-project

# List available templates
dbt-list
```

## 📋 Requirements

- **Hard Dependency**: DuggerLinkTools must be installed
- **Python**: 3.11+
- **Git**: For version control integration

## 🔧 Usage

### Basic Project Creation
```bash
dbt-init project-name --template standard
```

### Available Templates
- `standard`: Basic Python project structure
- `trading`: Trading bot template (coming soon)
- `automation`: Automation script template (coming soon)

### Options
- `--path`: Parent directory for new project (default: current)
- `--force`: Overwrite existing directory
- `--template`: Template type to use (default: standard)

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=src --cov-report=html
```

## 🔗 Integration

### DuggerLinkTools DNA Validation
Every generated project includes:
- ✅ Schema-validated `dugger.yaml`
- ✅ Standardized directory structure
- ✅ Pre-configured quality gates
- ✅ Git workflow integration

### Quality Gates
- **Black**: Code formatting (line length: 88)
- **Ruff**: Comprehensive linting
- **Pytest**: Test coverage reporting

## 📁 Project Structure

```
DuggerBootTools/
├── src/
│   └── duggerboot/
│       ├── cli.py           # CLI interface (dbt-init, dbt-list)
│       ├── engine.py        # Core scaffolding logic
│       ├── exceptions.py    # Custom exceptions
│       └── templates/       # Project templates
├── tests/                   # Test suite
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## 🤝 Contributing

1. Follow DuggerLinkTools commit conventions
2. Ensure all tests pass
3. Update documentation
4. Add new templates to the templates/ directory

## 📄 License

MIT License - see LICENSE file for details.