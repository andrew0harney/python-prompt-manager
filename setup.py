"""Setup configuration for python-prompt-manager."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read version from package
version_file = this_directory / "src" / "prompt_manager" / "__init__.py"
version = None
with open(version_file, "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split('"')[1]
            break

if not version:
    raise RuntimeError("Cannot find version information")

setup(
    name="python-prompt-manager",
    version=version,
    author="Your Name",
    author_email="your.email@example.com",
    description="Centralized prompt management for LLM applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/python-prompt-manager",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/python-prompt-manager/issues",
        "Documentation": "https://python-prompt-manager.readthedocs.io",
        "Source Code": "https://github.com/yourusername/python-prompt-manager",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        # Core dependencies - kept minimal
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "yaml": ["pyyaml>=5.4"],
        "django": ["django>=3.2"],
        "pydantic": ["pydantic>=2.0"],
        "all": ["openai>=1.0.0", "pyyaml>=5.4", "pydantic>=2.0"],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "pytest-django>=4.5",
            "pytest-env>=0.8",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
            "tox>=4.0",
            "sphinx>=5.0",
            "sphinx-rtd-theme>=1.0",
        ],
    },
    keywords=[
        "prompt",
        "prompt-management",
        "llm",
        "openai",
        "ai",
        "machine-learning",
        "configuration",
        "django",
    ],
    include_package_data=True,
    zip_safe=False,
)