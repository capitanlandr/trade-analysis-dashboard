# Contributing to Trade Analysis Dashboard

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Git
- Basic knowledge of React, TypeScript, and Node.js

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/capitanlandr/trade-analysis-dashboard.git
   cd trade-analysis-dashboard
   ```

2. **Run setup script**
   ```bash
   ./setup.sh
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📝 Development Guidelines

### Code Style

- **TypeScript**: Use strict TypeScript throughout
- **ESLint**: Follow the existing ESLint configuration
- **Prettier**: Code is automatically formatted
- **Naming**: Use descriptive names for variables and functions

### Component Guidelines

- **React Components**: Use functional components with hooks
- **Props**: Define proper TypeScript interfaces for all props
- **Error Boundaries**: Wrap components that might fail
- **Performance**: Use React.memo for expensive components
- **Accessibility**: Ensure components are accessible

### API Guidelines

- **REST**: Follow RESTful conventions
- **Error Handling**: Return consistent error responses
- **Validation**: Validate all inputs
- **Documentation**: Document API endpoints

## 🔄 Contribution Workflow

### 1. Issue First

- Check existing issues before creating new ones
- Use issue templates for bugs and features
- Discuss major changes in issues first

### 2. Branch Naming

Use descriptive branch names:
- `feature/add-trade-filtering`
- `bugfix/fix-manager-rankings`
- `docs/update-readme`

### 3. Commit Messages

Follow conventional commit format:
```
type(scope): description

feat(dashboard): add real-time trade updates
fix(api): resolve team name resolution bug
docs(readme): update installation instructions
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### 4. Pull Request Process

1. **Update your branch**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Run tests and linting**
   ```bash
   npm run lint
   npm test
   npm run build
   ```

3. **Create Pull Request**
   - Use the PR template
   - Link related issues
   - Add screenshots for UI changes
   - Request review from maintainers

## 🐛 Bug Reports

When reporting bugs, include:

- **Clear description** of the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment details** (OS, browser, Node.js version)
- **Console errors** if applicable
- **Screenshots** for UI issues

## ✨ Feature Requests

For new features, provide:

- **Problem description** - what need does this address?
- **Proposed solution** - how should it work?
- **Use cases** - when would this be used?
- **Implementation ideas** - any technical thoughts?

Thank you for contributing to make fantasy football trade analysis better for everyone! 🏈📈