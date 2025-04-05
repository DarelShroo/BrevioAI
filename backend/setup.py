from setuptools import find_packages, setup

setup(
    name="BrevioAI",
    version="0.1",
    packages=find_packages(where="backend"),
    package_dir={"": "backend"},
)
