from setuptools import setup

setup(
    name='spotwise',
    version='0.5.2',
    description='simple client for the Spotify Web API',
    author="WisdomWolf",
    author_email="wisdomwolf@gmail.com",
    url='http://spotipy.readthedocs.org/',
    install_requires=[
        'requests>=2.3.0',
        'six>=1.10.0',
    ],
    license='LICENSE.txt',
    packages=['spotipy'])
