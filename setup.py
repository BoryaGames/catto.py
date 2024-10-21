from setuptools import setup, find_packages  # type: ignore


def readme():
    with open("README.md", "r") as f:
        return f.read()


setup(
    name="catto.py",
    version="0.0.3",
    author="topcatto",
    author_email="feedbackborya@yandex.ru",
    description="A Python library for making webservers.",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/BoryaGames/catto.py",
    packages=find_packages(),
    install_requires=["uvicorn==0.30.3"],
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    keywords="catto cattojs cattopy webserver web server",
    project_urls={},
    python_requires=">=3.7"
)
