""" NOTE: Use 'pip install -e .' to install in development mode """

from setuptools import setup, find_packages


with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="UD_draft_model",
    version="1.0.0",
    packages=find_packages(),
    install_requires=requirements
)