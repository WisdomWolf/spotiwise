from setuptools import setup
import spotiwise

with open("README.md", "r") as f:
    long_description = f.read()

test_reqs = [
    'mock==2.0.0'
]

doc_reqs = [
    'Sphinx>=1.5.2'
]

extra_reqs = {
    'doc': doc_reqs,
    'test': test_reqs
}

setup(
    name='spotiwise',
    version=spotiwise.__version__,
    description='simple client for the Spotify Web API',
    author="WisdomWolf",
    author_email="wisdomwolf@gmail.com",
    url='http://spotipy.readthedocs.org/',
    install_requires=[
        'requests>=2.20.0',
        'six>=1.10.0',
    ],
    license='LICENSE.txt',
    packages=['spotiwise'],
    tests_require=test_reqs,
    extras_require=extra_reqs,
)
