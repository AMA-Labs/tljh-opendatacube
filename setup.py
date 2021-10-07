from setuptools import setup

setup(
    name='odc-tljh',
    version='0.1',
    description='An Open Data Cube (ODC) deployment of The Littlest JupyterHub (TLJH)',
    url='https://github.com/jcrattz/odc-tljh',
    author='AMA Earth Analytics Lab',
    author_email='eal@ama-inc.com',
    license='Apache License 2.0',
    pymodules = ['tljh_odc'],
    entry_points={
        'tljh': [
            'odc = tljh_odc',
        ]
    },
)