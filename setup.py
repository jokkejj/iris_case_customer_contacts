from setuptools import setup, find_packages

setup(
    name="iris_case_customer_contacts",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "iris-module-interface>=1.1,<1.3",
    ],
)
