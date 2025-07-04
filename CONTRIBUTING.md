# Contributing to IB Simulator

Thank you for your interest in contributing to IB Simulator! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior vs actual behavior
- System information (OS, Python version)
- Relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- A clear and descriptive title
- Detailed description of the proposed feature
- Use cases and benefits
- Possible implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Make your changes
4. Run tests to ensure nothing is broken
5. Commit your changes with clear messages
6. Push to your fork
7. Open a Pull Request

#### Pull Request Guidelines

- Follow PEP 8 style guide
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic
- Write clear commit messages

### Code Style

- Use Python 3.8+ features where appropriate
- Follow PEP 8 with 100-character line limit
- Use type hints for function parameters and returns
- Write docstrings for all public functions and classes
- Use meaningful variable names

### Testing

- Write unit tests for new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage
- Test edge cases and error conditions

### Documentation

- Update README.md if adding new features
- Add docstrings to new functions and classes
- Include usage examples for new functionality
- Keep documentation clear and concise

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ib-simulator.git
cd ib-simulator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r ib_simulator/requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

4. Run tests:
```bash
python -m pytest tests/
```

## Project Structure

```
ib_simulator/
├── core/           # Core server components
├── protocol/       # IB protocol implementation
├── database/       # Database layer
├── handlers/       # Message handlers (future)
├── utils/          # Utility functions
└── tests/          # Test suite
```

## Future Improvements

Areas where contributions are especially welcome:

- Additional IB API method implementations
- Options pricing models
- Market microstructure simulation
- Performance optimizations
- Additional test coverage
- Documentation improvements

## Questions?

Feel free to open an issue for any questions about contributing!

Thank you for helping make IB Simulator better! 🚀