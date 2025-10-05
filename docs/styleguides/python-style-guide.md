# Python Style Guide

This document outlines the Python coding standards for the muzikki-backend project.

## General Guidelines

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code style
- Follow [PEP 257](https://www.python.org/dev/peps/pep-0257/) for docstring conventions
- Use Python 3.8+ features when appropriate

## Code Formatting

- **Line Length**: Maximum 120 characters (with some flexibility for readability)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Use double quotes for strings by default, single quotes for dictionary keys if needed

## Naming Conventions

- **Variables and Functions**: `snake_case`
  ```python
  user_name = "John"
  def get_user_data():
      pass
  ```

- **Classes**: `PascalCase`
  ```python
  class UserProfile:
      pass
  ```

- **Constants**: `UPPER_SNAKE_CASE`
  ```python
  MAX_RETRY_COUNT = 3
  API_BASE_URL = "https://api.example.com"
  ```

- **Private Methods/Variables**: Prefix with single underscore `_`
  ```python
  def _internal_helper():
      pass
  ```

## Imports

- Group imports in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application imports

- Use absolute imports when possible
- One import per line

Example:
```python
import os
import sys

from django.db import models
from rest_framework import serializers

from .models import User
```

## Documentation

- All public modules, classes, and functions should have docstrings
- Use Google-style or NumPy-style docstrings

Example:
```python
def calculate_total(items, tax_rate=0.1):
    """Calculate total price including tax.
    
    Args:
        items (list): List of item prices
        tax_rate (float): Tax rate as decimal (default: 0.1)
        
    Returns:
        float: Total price including tax
    """
    subtotal = sum(items)
    return subtotal * (1 + tax_rate)
```

## Type Hints

- Use type hints for function parameters and return values when possible
- Import from `typing` module for complex types

Example:
```python
from typing import List, Optional, Dict

def process_users(users: List[Dict[str, str]]) -> Optional[int]:
    pass
```

## Tools

- **Linter**: Use `flake8` or `pylint` for code quality checks
- **Formatter**: Use `black` for automatic code formatting
- **Import Sorter**: Use `isort` for organizing imports
