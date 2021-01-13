# -*- coding: utf-8 -*-
from setuptools import setup


readme = 'docs/README.md'

setup(
    name='AppWatch',
    version=__import__('src').__version__,
    url="https://bitbucket.org/JusTopich/appwatch",
    author="JusTopich",
    py_modules=['AppWatch', 'conf', 'inspector'],
    license="GPLv3",
    author_email="alex1.beloglazov@yandex.ru",
    description="Simple WatchDog for Windows applications with email or Slack notifications.",
    long_description=open(readme, encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    install_requires=open('requirements.txt', encoding='utf-8').readlines(),
    keywords=['application', 'app', 'watchdog', 'monitor', 'watch', 'control']
)