"""
Setup script for IB Simulator
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("ib_simulator/requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ib-simulator",
    version="1.0.0",
    author="IB Simulator Contributors",
    description="A high-fidelity simulator for Interactive Brokers TWS API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ib-simulator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ib-simulator=ib_simulator.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ib_simulator": ["config.yaml", "requirements.txt"],
    },
)