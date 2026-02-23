#!/usr/bin/env python3
from setuptools import setup, find_packages

__VERSION__ = "1.0.0"

def main(args=None):
    README = open("./README.md").read()

    setup_required_packages = []

    required_packages = [
        "fastapi>=0.100",
        "uvicorn[standard]>=0.23",
        "starlette>=0.27",
        "pydantic>=2.0",
        "filelock",
        "web3",
        "websocket-client",
        "langdetect",
    ]
                  

    settings = dict(name="pyhypercycle_aim",
                    version=__VERSION__,
                    description="Hypercycle AIM Library",
                    long_description=README,
                    classifiers=["Programming Language :: Python", ],
                    author="",
                    author_email="",
                    url="",
                    keywords="hypercycle aim library",
                    packages=find_packages(),
                    include_package_data=True,
                    zip_safe=False,
                    install_requires=required_packages,
                    setup_requires=setup_required_packages
                    )
    if args:
        settings['script_name'] = __file__
        settings['script_args'] = args
    setup(**settings)


if __name__ == "__main__":
    main()

