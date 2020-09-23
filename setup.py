from pathlib import Path
import re

from setuptools import setup  # type: ignore  # no stubs or types

root = Path(__file__).parent

requirements = (
    (root / "requirements.txt").read_text("utf-8").strip().splitlines()
)

text = (root / "gd" / "rpc.py").read_text("utf-8")

result = re.search(
    r"^__version__\s*=\s*[\"']([^\"']*)[\"']", text, re.MULTILINE
)

if result is None:
    raise RuntimeError("Failed to find version.")

version = result.group(1)

readme = (root / "README.rst").read_text("utf-8")


setup(
    name="gd.rpc",
    author="nekitdev",
    author_email="gdpy13@gmail.com",
    url="https://github.com/nekitdev/gd.rpc",
    project_urls={
        "Issue tracker": "https://github.com/nekitdev/gd.rpc/issues",
    },
    version=version,
    packages=["gd"],
    license="MIT",
    description="Geometry Dash Discord Rich Presence",
    long_description=readme,
    long_description_content_type="text/x-rst",
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Natural Language :: English",
        "Operating System :: Microsoft :: Windows",
    ],
    entry_points={"console_scripts": ["gd.rpc = gd.rpc:run"]},
)
