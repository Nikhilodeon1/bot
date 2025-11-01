"""
Setup configuration for Botted Library
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="botted-library",
    version="1.0.1",
    author="Botted Library Team",
    author_email="contact@botted-library.com",
    description="Human-like AI workers that can use any tool to accomplish tasks - web search, coding, document creation, and more",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/botted-library/botted-library",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Office/Business",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "openai": ["openai>=1.3.0"],
        "anthropic": ["anthropic>=0.7.0"],
        "dev": [
            "pytest>=7.4.0",
            "pytest-mock>=3.12.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "botted-library=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "botted_library": ["*.md", "*.txt", "*.json"],
    },
    keywords="ai automation browser selenium llm workers intelligent agents human-like research coding",
    project_urls={
        "Bug Reports": "https://github.com/botted-library/botted-library/issues",
        "Source": "https://github.com/botted-library/botted-library",
        "Documentation": "https://github.com/botted-library/botted-library#readme",
        "Homepage": "https://botted-library.com",
    },
)