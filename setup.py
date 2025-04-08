#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="sms_parser",
    version="1.0.0",
    description="A comprehensive SMS parser for banking transactions, promotional messages, and fraud detection",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "google-generativeai>=0.3.0",
        "flask>=2.0.0",
        "python-dotenv>=0.19.0",
        "requests>=2.26.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "sms-parser=sms_parser.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 