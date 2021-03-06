"""Distribution script for Pedlar client API."""
import setuptools
from config import VERSION

with open("README.md", 'r') as fh:
  long_description = fh.read()

setuptools.setup(
  name="pedlaragent",
  version=VERSION,
  author="thomas",
  author_email="nuric@users.noreply.github.com",
  description="Algorithmic Trading Platform for Python",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url="https://github.com/ThomasWong2022/pedlar/",
  packages=["pedlaragent"],
  include_package_data=True,
  classifiers=[
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: Apache Software License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3 :: Only",
    "Topic :: Office/Business :: Financial",
  ],
  install_requires=[
    'requests'
  ]
)
