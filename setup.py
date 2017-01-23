from setuptools import setup
VERSION = '0.2'

setup(
        name='md2conf',
        version=VERSION,
        description='Upload .md file to Confluence',
        install_requires=[
            'requests',
            'beautifulsoup4',
            'markdown',
            ],
        scripts=['bin/md2conf'],
        )
