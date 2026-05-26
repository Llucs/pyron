from setuptools import setup, find_packages

setup(
    name="pyron",
    version="1.0.0",
    description="Pyron - Autonomous AI Agent powered by OpenCode API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Llucs",
    author_email="llucs@pyron.dev",
    url="https://github.com/Llucs/pyron",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "pyron=pyron.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
