from setuptools import setup

setup(
    name='Valency',
    version='0.1',
    description='Valency lexicon of slovenian verbs.',
    url='https://bitbucket.org/voje/diploma',
    author='Kristjan Voje',
    author_email='kristjan.voje@gmail.com',
    license='MIT',
    packages=['valency'],  # where to look for __init__.py
    install_requires=[
        'bs4',
        'requests',
        'matplotlib',
        'flask',
        'nltk',
        'pymongo',
        'xmltodict',
        'scipy',
        'scikit-learn',
        'polyglot',
        'pyicu',
        'pycld2',
        'morfessor',
        'flask-cors',
    ]
)
