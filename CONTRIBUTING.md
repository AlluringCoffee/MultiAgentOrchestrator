# Contributing to Multi-Agent Orchestrator

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/multi-agent-orchestrator.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Submit a pull request

## 📁 Project Structure

```
multi-agent-orchestrator/
├── core/           # Core workflow engine
├── providers/      # LLM provider integrations
├── static/         # Frontend (HTML, CSS, JS)
├── workflows/      # Workflow templates
├── config/         # Configuration files
└── tests/          # Test suite
```

## 🔧 Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python server.py
```

## 📝 Code Style

- **Python**: Follow PEP 8
- **JavaScript**: Use ES6+ features
- **CSS**: Use semantic class names
- Add docstrings to all functions
- Comment complex logic

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_workflow.py -v
```

## 📦 Adding New Features

### New Provider

1. Create `providers/your_provider.py`
2. Implement the `LLMProvider` interface
3. Register in `providers/__init__.py`
4. Add to `providers.json.example`

### New Workflow Template

1. Create workflow in the UI
2. Save as JSON
3. Place in `workflows/templates/`
4. Update README with description

### New Node Type

1. Add type to `NodeType` enum in `core/workflow.py`
2. Implement processing logic
3. Add to frontend palette in `static/nodes.js`

## 🐛 Bug Reports

Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- System info (OS, Python version, browser)
- Logs if available

## 💡 Feature Requests

Open an issue with:
- Clear description
- Use case / motivation
- Proposed solution (optional)

## 📄 Pull Request Guidelines

- Keep PRs focused (one feature/fix per PR)
- Update documentation if needed
- Add tests for new features
- Ensure all tests pass
- Follow existing code style

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.
