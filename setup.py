from setuptools import setup, find_packages

setup(
    name='py_cherty',
    version='0.4.1',
    description='A package to send messages to an Electron app',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Alan Ransil',
    author_email='alan@devonian.ai',
    url='https://github.com/devonian-ai/py_cherty',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
