#!/bin/bash

# Install test dependencies
pip install -r requirements-test.txt

# Run tests with coverage
pytest --cov=webhookservice tests/ --cov-report=term-missing --cov-report=html

# Generate coverage report
coverage report -m

echo "Test coverage report generated in htmlcov/index.html" 