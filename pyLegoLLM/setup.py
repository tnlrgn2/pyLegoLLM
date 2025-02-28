from setuptools import setup, find_packages

setup(
    name="pyLegoLLM",
    version="0.1.0",
    description="A Python package to control LEGO bricks via BLE.",
    author="tnl2rgn2",
    author_email="tnl2rgn2@example.com",
    packages=find_packages(),  # Automatically find all packages
    install_requires=[
        "bleak",  # Add any dependencies your package requires
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",  # Specify Python version compatibility
)