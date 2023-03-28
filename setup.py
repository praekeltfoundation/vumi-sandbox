from setuptools import setup, find_packages

setup(
    name="vxsandbox",
    version="0.6.2-alpha3",
    url='http://github.com/praekelt/vumi-sandbox',
    license='BSD',
    description="A sandbox application worker for Vumi.",
    long_description=open('README.rst', 'r').read(),
    author='Praekelt Foundation',
    author_email='dev@praekeltfoundation.org',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'automat<22.10.0',  # Twisted dep, newer versions don't work with ancient Python.
        'cryptography<3.3',  # To see if this avoids "undefined symbol: FIPS_mode".
        'Twisted>=20.3.0,<21.0.0',
        'vumi>=0.6.19',
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
