# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-03

### Added (v1.1.0)

- Premium UI Polish: Enhanced gradients for Agent, Character, Director, and Auditor nodes.
- Canvas Background Performance: Smooth animated celestial glow effect on the workspace.
- Modern Scrollbars: Slim, themed scrollbars across the entire application.
- Node Visuals: GPU-accelerated glow effects and entrance animations for improved feedback.

### Fixed (v1.1.0)

- Core Interactivity: Resolved node selection bug ensuring configuration panel updates correctly.
- Drag-and-Drop: Fixed palette item instantiation on the canvas.
- Stability: Cleaned up redundant script inclusions and added defensive code to prevent UI crashes.

## [1.0.0] - 2026-01-25

### Added (v1.0.0)

- Initial public release
- Visual node-based workflow editor
- Multiple LLM provider support (Ollama, Groq, Google AI)
- Live thought streaming for DeepSeek-R1 and similar models
- 8 template workflows:
  - Game Character Creator
  - Code Reviewer
  - Programmer Team
  - Idea Validator
  - Grand Council
  - Legal Team
  - Debug Detective
  - Story Writer
- Hardware profiles (low_end, medium, high_end)
- Feedback loop support for iterative workflows
- Shared story memory context
- Node approval gates for human-in-the-loop
- Export to markdown files
- WebSocket real-time updates

### Fixed

- Edge feedback property preservation during workflow load
- Director node deadlock with consensus loop
- Character agent circular dependency resolution
- KeyError in shared history context building

### Technical

- FastAPI backend with async execution
- Streaming response support in Ollama provider
- Pydantic v2 models
- Topological sort with cycle detection
