# Contributing to TrustChain

First off, thanks for considering contributing to TrustChain! 🎉

This project is about making AI accountable and transparent, especially for high-stakes government decisions. Every contribution helps make that vision a reality.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug:
1. Check if it's already reported in [Issues](https://github.com/yourusername/trustchain/issues)
2. If not, open a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (Python version, OS, etc.)

### Suggesting Features

Have an idea? Great! Open an issue with:
- **Problem**: What problem does this solve?
- **Solution**: How would it work?
- **Alternatives**: What other approaches did you consider?

### Pull Requests

1. **Fork the repo**
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Add tests** (if applicable)
5. **Update documentation**
6. **Run tests**: `pytest` (when test suite is added)
7. **Commit**: Use clear, descriptive commit messages
8. **Push**: `git push origin feature/your-feature-name`
9. **Open PR**: Describe what you changed and why

## 🎯 Areas for Contribution

### High Priority
- **Database integration** (PostgreSQL schema implementation)
- **Frontend dashboard** (React/Vue visualization)
- **Advanced consensus algorithms** (weighted voting, Bayesian approaches)
- **Bias detection improvements** (LIME/SHAP integration)

### Medium Priority
- **Additional providers** (Cohere, AI21, etc.)
- **Caching layer** (Redis integration)
- **Authentication** (JWT implementation)
- **Rate limiting**
- **Monitoring/metrics** (Prometheus integration)

### Documentation
- Tutorial videos
- Deployment guides (Docker, Kubernetes, etc.)
- Use case examples
- API client libraries (JavaScript, Go, etc.)

## 💻 Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/trustchain.git
cd trustchain/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your API keys to .env

# Run tests
python test_providers.py
```

## 📝 Code Style

- **Type hints**: Use them everywhere
- **Docstrings**: Every function/class needs one
- **Comments**: Explain WHY, not WHAT
- **Formatting**: Run `black` before committing
- **Linting**: Run `ruff` to catch issues

Example:
```python
async def make_decision(
    self,
    case_id: str,
    decision_type: str,
    prompt: str
) -> Decision:
    """
    Make a consensus decision using multiple AI models.

    Args:
        case_id: Unique identifier for this case
        decision_type: Type of decision (e.g., 'unemployment_benefits')
        prompt: The case details to evaluate

    Returns:
        Decision object with consensus analysis and audit trail

    Raises:
        ProviderException: If all AI providers fail
    """
    # Implementation...
```

## 🛡️ Safety & Compliance

This project handles sensitive government decisions. When contributing:

- **Never commit API keys or secrets**
- **Preserve audit trail integrity** (don't break SHA-256 hashing)
- **Maintain bias detection** (don't remove safety checks)
- **Test with edge cases** (especially for protected attributes)
- **Document compliance impact** (FOIA, civil rights, etc.)

## 🧪 Testing

When adding features:
1. **Unit tests**: Test individual functions
2. **Integration tests**: Test component interactions
3. **Safety tests**: Verify bias detection still works
4. **Edge cases**: Protected attributes, low confidence, provider failures

## 📚 Documentation

Update documentation when you:
- Add a new feature
- Change an API
- Add a new provider
- Modify bias detection logic

Files to update:
- `README.md` - If it affects setup/usage
- `API_GUIDE.md` - If it's an API change
- `SAFETY_SAFEGUARDS.md` - If it's a safety feature
- Inline docstrings - Always!

## 🔒 Security

If you find a security vulnerability:
1. **DO NOT** open a public issue
2. Email: [your-email@example.com]
3. Include: Description, reproduction steps, impact

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be:
- Listed in a CONTRIBUTORS.md file
- Mentioned in release notes
- Credited in any derivative work (as per MIT license)

## ❓ Questions?

- Open a [Discussion](https://github.com/yourusername/trustchain/discussions)
- Reach out on [LinkedIn](https://linkedin.com/in/yourprofile)

---

**Thanks for making AI more accountable!** 🚀
