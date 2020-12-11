import pathlib
from setuptools import setup, find_packages


here = pathlib.Path(__file__).parent.resolve()

with open(here / "runtime.txt", "r") as f:
    runtime = f.read().replace("python-", "")


extras_require = {
    "checks": [
        "tox==3.20.1",
        "mypy==0.790",
        "black==20.8b1",
        "flake8==3.8.4",
        "flake8-bugbear==20.11.1",
    ],
    "tests": [
        "pytest==6.1.2",
        "pytest-asyncio==0.14.0",
        "pytest-lazy-fixture==0.6.3",
        "coverage==5.3",
    ],
}

extras_require["dev"] = extras_require["checks"] + extras_require["tests"]

setup(
    name="geniust",
    packages=find_packages(
        exclude=(
            "tests",
            "tests.*",
        )
    ),
    extras_require=extras_require,
    python_requires=">=" + runtime,
)
