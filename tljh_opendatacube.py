import os
import sh
from tljh.hooks import hookimpl
from tljh.user import ensure_group

# CONFIG #
LOAD_INITIAL_DATA = True
DEFAULT_ENV = '/lab'  # /lab, /tree, or /nteract
SHARED_DIR = '/srv/shared'  # not completely fool-proof, pls don't change this

# DATABASE SETTINGS #
DATABASE_NAME = 'datacube'
POSTGRES_PW = 'superPassword'
DB_ADMIN_ROLE = 'odc_db_admin'
DB_ADMIN_PW = 'insecurePassword'
DB_USER_ROLE = 'odc_db_user'
DB_USER_PW = 'worrysomepPassword'
ODC_ADMIN_ROLE = 'agdc_admin'
ODC_USER_ROLE = 'agdc_user'

# INITIAL/STARTER DATA (yellowstone np)
BBOX_LEFT = -111.1423
BBOX_BOTTOM = 44.0854
BBOX_RIGHT = -109.3594
BBOX_TOP = 45.1167
TIME_RANGE = '2019-01-01/2021-11-01'


def setup_default_products():

    preamble = f'source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME={DB_ADMIN_ROLE} DB_PASSWORD={DB_ADMIN_PW} DB_DATABASE={DATABASE_NAME}'

    # initialise datacube database  default products
    sh.bash("-c", f"{preamble} DB_DATABASE={DATABASE_NAME} dc-sync-products https://raw.githubusercontent.com/AMA-Labs/tljh-opendatacube/master/products.csv")

    # index default products
    sh.bash("-c", f"{preamble} stac-to-dc --bbox='{BBOX_LEFT}, {BBOX_BOTTOM}, {BBOX_RIGHT}, {BBOX_TOP}' --catalog-href='https://earth-search.aws.element84.com/v0/' --collections='sentinel-s2-l2a-cogs' --datetime='{TIME_RANGE}'")
    sh.bash("-c", f"{preamble} stac-to-dc --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='io-lulc'")
    sh.bash("-c", f"{preamble} stac-to-dc --bbox='{BBOX_LEFT}, {BBOX_BOTTOM}, {BBOX_RIGHT}, {BBOX_TOP}' --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='nasadem'")
    sh.bash("-c", f"{preamble} stac-to-dc --bbox='{BBOX_LEFT}, {BBOX_BOTTOM}, {BBOX_RIGHT}, {BBOX_TOP}' --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='landsat-8-c2-l2' --datetime='{TIME_RANGE}")


def setup_database_for_datacube():


    DB_NAME = 'datacube'

    sh.systemctl("enable", "postgresql")
    sh.service("postgresql", "restart")

    su_postgres = sh.su.bake("-", "postgres", "-c")

    # ensure we're starting from scratch
    su_postgres(f"psql -c \'DROP DATABASE IF EXISTS {DB_NAME};\'")
    su_postgres("psql -c \'DROP EXTENSION IF EXISTS postgis;\'")
    su_postgres(f"psql -c \'DROP ROLE IF EXISTS {DB_ADMIN_ROLE};\'")
    su_postgres(f"psql -c \'DROP ROLE IF EXISTS {DB_USER_ROLE};\'")

    # create database + extension
    su_postgres("psql -c \'CREATE EXTENSION postgis;\'")
    su_postgres(f"psql -c \'CREATE DATABASE {DB_NAME};\'")

    # configure postgres to work with datacube
    su_postgres(f"psql -c \"ALTER USER postgres PASSWORD \'{POSTGRES_PW}\';\"")
    su_postgres(f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=postgres DB_PASSWORD={POSTGRES_PW} DB_DATABASE={DATABASE_NAME} {DATABASE_NAME} -v system init")
    su_postgres(f"psql -c \"CREATE ROLE {DB_ADMIN_ROLE} WITH LOGIN IN ROLE {ODC_ADMIN_ROLE}, {ODC_USER_ROLE} ENCRYPTED PASSWORD \'{DB_ADMIN_PW}\';\"")
    su_postgres(f"psql -c \"CREATE ROLE {DB_USER_ROLE} WITH LOGIN IN ROLE {ODC_USER_ROLE} ENCRYPTED PASSWORD \'{DB_USER_PW}\';\"")
    su_postgres(f"psql -c \'ALTER DATABASE {DB_NAME} OWNER TO {DB_ADMIN_ROLE};\'")


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
    sh.mkdir(SHARED_DIR, '-p')  # make a shared folder
    ensure_group('jupyterhub-users')  # create teh user group since no one's logged in yet
    sh.chown('root:jupyterhub-users', SHARED_DIR)  # let the group own it
    sh.chmod('777', SHARED_DIR)  # allow everyone access
    sh.chmod('g+s', SHARED_DIR)  # set group id
    os.system('rm -rf /etc/skel/shared/shared')  # reinstall compatability
    sh.ln('-s',  SHARED_DIR, '/etc/skel/shared')  # symlink

@hookimpl
def tljh_post_install():
    """
    Executes after installation and all the other hooks. Used to configure the postgres database for datacube
    """
    setup_database_for_datacube()
    if LOAD_INITIAL_DATA:
        setup_default_products()

@hookimpl
def tljh_new_user_create(username):
    """
    Script to be executed after a new user has been added.
    This can be arbitrary Python code.
    """
    