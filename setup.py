from setuptools import setup

setup(
    name='tljh-opendatacube',
    version='0.1',
    description='An Open Data Cube (ODC) deployment of The Littlest JupyterHub (TLJH)',
    url='https://github.com/AMA-Labs/tljh-opendatacube',
    author='AMA Earth Analytics Lab',
    author_email='eal@ama-inc.com',
    license='Apache License 2.0',
    entry_points={
        'tljh': [
            'odc = tljh_opendatacube',
        ]
    },
    py_modules = ['tljh_opendatacube'],
    install_requires=['sh']
)