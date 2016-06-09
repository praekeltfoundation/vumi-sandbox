from setuptools import setup, find_packages

setup(
    name="vxsandbox",
    version="0.6.1",
    url='http://github.com/praekelt/vumi-sandbox',
    license='BSD',
    description="A sandbox application worker for Vumi.",
    long_description=open('README.rst', 'r').read(),
    author='Praekelt Foundation',
    author_email='dev@praekeltfoundation.org',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Twisted>=13.1.0',
        'vumi>=0.5',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
    ],
)
