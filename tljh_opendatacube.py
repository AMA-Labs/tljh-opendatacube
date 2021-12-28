import os
import pwd
from typing import DefaultDict
import sh
from tljh.hooks import hookimpl
from tljh.user import ensure_group
import subprocess

import logging
logger = logging.getLogger("tljh")

# CONFIG #
LOAD_INITIAL_DATA = False
DEFAULT_ENV = '/lab'  # /lab, /tree, or /nteract
SHARED_DIR = '/srv/shared'  # not completely fool-proof, pls don't change this

# POSTGRES SETTINGS #
PSQL_HOST = 'localhost'
POSTGRES_DB_USER = 'postgres'
POSTGRES_DB_PASS = 'superPassword'

# DATACUBE DB #
ODC_DB_NAME = 'datacube'
# read/write creds
ODC_DB_ADMIN_USER = 'odc_db_admin'
ODC_DB_ADMIN_PASS = 'insecurePassword'
# read-only creds
ODC_DB_READ_ONLY_USER = 'odc_db_user'
ODC_DB_READ_ONLY_PASS = 'worrysomepPassword'

# INITIAL/STARTER DATA (yellowstone np)
BBOX_LEFT = -111.1423
BBOX_BOTTOM = 44.0854
BBOX_RIGHT = -109.3594
BBOX_TOP = 45.1167
TIME_RANGE = '2019-01-01/2021-11-01'


def setup_default_products():

    preamble = f'source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME={ODC_DB_ADMIN_USER} DB_PASSWORD={ODC_DB_ADMIN_PASS} DB_DATABASE={ODC_DB_NAME}'

    # initialise datacube database  default products
    sh.bash("-c", f"{preamble} DB_DATABASE={ODC_DB_NAME} dc-sync-products https://raw.githubusercontent.com/AMA-Labs/tljh-opendatacube/master/products.csv")

    # index default products
    sh.bash("-c", f"{preamble} stac-to-dc --bbox='{BBOX_LEFT}, {BBOX_BOTTOM}, {BBOX_RIGHT}, {BBOX_TOP}' --catalog-href='https://earth-search.aws.element84.com/v0/' --collections='sentinel-s2-l2a-cogs' --datetime='{TIME_RANGE}'")
    sh.bash("-c", f"{preamble} stac-to-dc --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='io-lulc'")
    sh.bash("-c", f"{preamble} stac-to-dc --bbox='{BBOX_LEFT}, {BBOX_BOTTOM}, {BBOX_RIGHT}, {BBOX_TOP}' --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='nasadem'")
    sh.bash("-c", f"{preamble} stac-to-dc --bbox='{BBOX_LEFT}, {BBOX_BOTTOM}, {BBOX_RIGHT}, {BBOX_TOP}' --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='landsat-8-c2-l2' --datetime='{TIME_RANGE}")


def setup_database_for_datacube():

    logger.info('Setting up the Postgresql DB for the Open Data Cube...')
    # TODO: create a read-only account for non-admin users

    # enable then restart teh service
    sh.systemctl("enable", "postgresql")
    sh.service("postgresql", "restart")

    su_postgres = sh.su.bake("-", "postgres", "-c")  # preamble

    # ensure we're starting from scratch
    su_postgres(f"psql -c \'DROP DATABASE IF EXISTS {ODC_DB_NAME};\'")
    su_postgres("psql -c \'DROP EXTENSION IF EXISTS postgis;\'")
    su_postgres(f"psql -c \'DROP ROLE IF EXISTS {ODC_DB_ADMIN_USER};\'")
    su_postgres(f"psql -c \'DROP ROLE IF EXISTS {ODC_DB_READ_ONLY_USER};\'")

    # create database + extension
    su_postgres("psql -c \'CREATE EXTENSION postgis;\'")
    su_postgres(f"psql -c \'CREATE DATABASE {ODC_DB_NAME};\'")

    # set a pw for the postgres db user
    su_postgres(f"psql -c \"ALTER USER {POSTGRES_DB_USER} PASSWORD \'{POSTGRES_DB_PASS}\';\"")

    # initialize the datacube
    su_postgres(f"source /opt/tljh/user/bin/activate && DB_HOSTNAME={PSQL_HOST} DB_USERNAME={POSTGRES_DB_USER} DB_PASSWORD={POSTGRES_DB_PASS} DB_DATABASE={ODC_DB_NAME} datacube -v system init")

    # create an admin role in the odc db
    su_postgres(f"psql -c \"CREATE ROLE {ODC_DB_ADMIN_USER} WITH LOGIN IN ROLE agdc_admin, agdc_user ENCRYPTED PASSWORD \'{ODC_DB_ADMIN_PASS}\';\"")

    # create user role in the odc db
    su_postgres(f"psql -c \"CREATE ROLE {ODC_DB_READ_ONLY_USER} WITH LOGIN IN ROLE agdc_user ENCRYPTED PASSWORD \'{ODC_DB_READ_ONLY_PASS}\';\"")
    su_postgres(f"psql -c \'ALTER DATABASE {ODC_DB_NAME} OWNER TO {ODC_DB_ADMIN_USER};\'")


def setup_odc_gee():
    logger.info('Setting up the odc-gee plugin...')
    # subprocess.run('git clone https://github.com/ceos-seo/odc-gee.git /home/ubuntu/odc-gee', shell=False)
    # subprocess.run(["git clone https://github.com/ceos-seo/odc-gee.git"])
    os.system('git clone https://github.com/ceos-seo/odc-gee.git')

    # subprocess.run(['git', 'clone', 'https://github.com/ceos-seo/odc-gee.git'], shell=True)
    # install_cmd = 'source /opt/tljh/user/bin/activate && sudo -E /opt/tljh/user/bin/pip install -e /home/ubuntu/odc-gee'
    # install_cmd = 'source /opt/tljh/user/bin/activate && sudo -E /opt/tljh/user/bin/python -m pip install -e /home/ubuntu/odc-gee'
    # install_cmd = 'sudo su - ubuntu -c \'source /opt/tljh/user/bin/activate && sudo -E /opt/tljh/user/bin/python -m pip install -e /home/ubuntu/odc-gee\''
    # install_cmd = 'source /opt/tljh/user/bin/activate && sudo -E /opt/tljh/user/bin/python -m pip install -e odc-gee'
    install_cmd = 'sudo -E /opt/tljh/user/bin/python -m pip install -e odc-gee'
    os.system(install_cmd)
    logger.info('The odc-gee plugin has been setup!')


def setup_shared_directory():
    logger.info('Setting up a shared directory...')
    sh.mkdir(SHARED_DIR, '-p')  # make a shared folder
    ensure_group('jupyterhub-users')  # create teh user group since no one's logged in yet
    sh.chown('root:jupyterhub-users', SHARED_DIR)  # let the group own it
    sh.chmod('777', SHARED_DIR)  # allow everyone access
    sh.chmod('g+s', SHARED_DIR)  # set group id
    os.system('rm -rf /etc/skel/shared/shared')  # reinstall compatability
    sh.ln('-s',  SHARED_DIR, '/etc/skel/shared')  # symlink

@hookimpl
def tljh_extra_user_conda_packages():
    return [
        'gdal',
        'geopandas',
        'datacube',
        'Cython',
        'matplotlib',
        'seaborn',
        'folium',
        'scipy',
        'scikit-image',
        'tqdm',
        'python-dateutil',
        ]

@hookimpl
def tljh_extra_user_pip_packages():
    return [
        '--extra-index-url=https://packages.dea.ga.gov.au',
        'odc_algo[hdstats]',
        'odc_ui',
        'odc_index',
        'odc_aws',
        'odc_geom',
        'odc_io',
        'odc_aio',
        'odc_dscache',
        'odc_dtools',
        'odc-apps-dc-tools',
        'odc-apps-cloud',
        'odc_ppt',
        'eodatasets3',
        'datacube-stats',
        # '--no-binary=Cython,rasterio,Shapely,pygeos,netCDF4,pyproj,fc,hdstats,lmdb,lxml,numexpr,pyzmq,msgpack,ruamel.yaml.clib,zstandard'
    ]

@hookimpl
def tljh_extra_hub_pip_packages():
    """
    Return list of extra pip packages to install in the hub environment.
    """
    pass

@hookimpl
def tljh_extra_apt_packages():
    return [
        'curl',
        'git',
        'unzip',
        'zip',
        'libpq-dev',
        'libgdal-dev',
        'libhdf5-dev',
        'libnetcdf-dev',
        'python3-dev',
        'postgresql',
        'postgresql-contrib',
        'postgis',
        # already on ec2:
        # 'wget',
        # 'less',
        # 'vim',
        # 'htop',
    ]

@hookimpl
def tljh_custom_jupyterhub_config(c):
    """
    Provide custom traitlet based config to JupyterHub.
    Anything you can put in `jupyterhub_config.py` can
    be here.
    """
    c.Spawner.default_url = DEFAULT_ENV  # default to jupyter lab

@hookimpl
def tljh_config_post_install(config):
    """
    Configure shared directory and change config mods
     - src: https://github.com/kafonek/tljh-shared-directory/blob/master/tljh_shared_directory.py
    """
    setup_shared_directory()

@hookimpl
def tljh_post_install():
    """
    Executes after installation and all the other hooks. Used to configure the postgres database for datacube
    """
    setup_database_for_datacube()
    setup_odc_gee()
    if LOAD_INITIAL_DATA:
        setup_default_products()

@hookimpl
def tljh_new_user_create(username):
    """
    Script to be executed after a new user has been added.
    This can be arbitrary Python code.
    """

    def check_user_type(user):
        check_string = 'is not allowed to run sudo'
        proc = subprocess.Popen([f"sudo -l -U {user}"], stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()

        if check_string in str(out):
            return 'user'
        elif '(ALL) NOPASSWD: ALL' in str(out):
            return 'admin'
        else:
            print(err)
            return 'user'

    # get the user type
    user_type = check_user_type(username)


    datacube_conf_settings = f"""[datacube]
db_database: {ODC_DB_NAME}
db_hostname: {PSQL_HOST}"""

    # set up the user's datacube.conf file appropriately
    if user_type == 'user':
        datacube_conf_settings += f"""
db_username: {ODC_DB_READ_ONLY_USER}
db_password: {ODC_DB_READ_ONLY_PASS}"""

    elif user_type == 'admin':
        datacube_conf_settings += f"""
db_username: {ODC_DB_ADMIN_USER}
db_password: {ODC_DB_ADMIN_PASS}"""

    else:
        # default to read-only
        datacube_conf_settings += f"""
db_username: {ODC_DB_READ_ONLY_USER}
db_password: {ODC_DB_READ_ONLY_PASS}"""

    # pop it in a file for the user
    with open(f'/home/{username}/.datacube.conf', 'w+') as f:
        f.write(datacube_conf_settings)

