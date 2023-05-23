import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyfsdb-viewer",
    version="0.1",
    author="Wes Hardaker",
    author_email="opensource@hardakers.net",
    description="A pyfsdb and textual based viewer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gawseed/pyfsdb-viewer",
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": [
            # migrating to pdb prefixes
            "pdbview = pyfsdb_viewer.view:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    test_suite="nose.collector",
    tests_require=["nose"],
    install_requires=[
        "pyfsdb",
        "textual",
    ],
    package_data = {
        'pyfsdb_viewer': ['pyfsdb_viewer.css']
    }
)
