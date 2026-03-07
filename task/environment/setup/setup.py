from setuptools import setup, find_packages

setup(
    name="spacecraft_sim",
    version="1.0.0",
    description="Orbital mechanics engine extracted from SpacecraftSimulator (Alessio Negri, LGPL v3)",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24",
        "scipy>=1.10",
    ],
)
