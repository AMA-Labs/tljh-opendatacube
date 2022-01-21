import os
import sh
from tljh.hooks import hookimpl
from tljh.user import ensure_group
import subprocess

import logging
logger = logging.getLogger("tljh")


def setup_database_for_datacube():
    logger.info('Setting up the Postgresql DB for the Open Data Cube...')

    # enable then restart teh service
    sh.systemctl("enable", "postgresql")
    sh.service("postgresql", "restart")

    su_postgres = sh.su.bake("-", "postgres", "-c")  # preamble

    # create database + extension
    su_postgres("psql -c \'CREATE EXTENSION postgis;\'")
    su_postgres(f"psql -c \'CREATE DATABASE {os.getenv('ODC_DB_NAME', 'datacube')};\'")

    # set a pw for the postgres db user
    su_postgres(f"psql -c \"ALTER USER {os.getenv('POSTGRES_DB_USER', 'odc_db_user')} PASSWORD \'{os.getenv('POSTGRES_DB_PASS', 'worrysomepPassword')}\';\"")

    # initialize the datacube
    su_postgres(f"source /opt/tljh/user/bin/activate && DB_HOSTNAME={os.getenv('PSQL_HOST', 'localhost')} DB_USERNAME={os.getenv('POSTGRES_DB_USER', 'odc_db_user')} DB_PASSWORD={os.getenv('POSTGRES_DB_PASS', 'superPassword')} DB_DATABASE={os.getenv('ODC_DB_NAME', 'datacube')} datacube -v system init")

    # create an admin role in the odc db
    su_postgres(f"psql -c \"CREATE ROLE {os.getenv('ODC_DB_ADMIN_USER', 'odc_db_admin')} WITH LOGIN IN ROLE agdc_admin, agdc_user ENCRYPTED PASSWORD \'{os.getenv('ODC_DB_ADMIN_PASS', 'insecurePassword')}\';\"")

    # create user role in the odc db 
    su_postgres(f"psql -c \"CREATE ROLE {os.getenv('ODC_DB_READ_ONLY_USER', 'odc_db_user')} WITH LOGIN IN ROLE agdc_user ENCRYPTED PASSWORD \'{os.getenv('ODC_DB_READ_ONLY_PASS', 'worrysomepPassword')}\';\"")
    su_postgres(f"psql -c \'ALTER DATABASE {os.getenv('ODC_DB_NAME', 'datacube')} OWNER TO {os.getenv('ODC_DB_ADMIN_USER', 'odc_db_admin')};\'")


def setup_odc_gee():
    logger.info('Setting up the odc-gee plugin...')
    os.system('git clone https://github.com/ceos-seo/odc-gee.git')
    os.system('sudo -E /opt/tljh/user/bin/python -m pip install -e odc-gee')


def setup_shared_directory():
    shared_dir = '/srv/shared'
    logger.info('Setting up a shared directory...')
    sh.mkdir(shared_dir, '-p')  # make a shared folder
    ensure_group('jupyterhub-users')  # create teh user group since no one's logged in yet
    sh.chown('root:jupyterhub-users', shared_dir)  # let the group own it
    sh.chmod('777', shared_dir)  # allow everyone access
    sh.chmod('g+s', shared_dir)  # set group id
    os.system('rm -rf /etc/skel/shared/shared')  # reinstall compatability
    sh.ln('-s',  shared_dir, '/etc/skel/shared')  # symlink

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
    c.Spawner.default_url = '/lab'  # default to jupyter lab

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
    # pull in secrets and settings
    from dotenv import dotenv_values
    env = { **dotenv_values(".env") }

    for k in env.keys():
        try:
            os.environ[k]
        except KeyError:
            os.environ[k] = env[k]

    setup_database_for_datacube()
    setup_odc_gee()


@hookimpl
def tljh_new_user_create(username):
    """
    Script to be executed after a new user has been added.
    This can be arbitrary Python code.we're
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
db_database: {os.getenv('ODC_DB_NAME', 'datacube')}
db_hostname: {os.getenv('PSQL_HOST', 'localhost')}"""

    # set up the user's datacube.conf file appropriately
    if user_type == 'user':
        datacube_conf_settings += f"""
db_username: {os.getenv('ODC_DB_READ_ONLY_USER', 'odc_db_user')}
db_password: {os.getenv('POSTGRES_DB_PASS', 'worrysomepPassword')}"""

    elif user_type == 'admin':
        datacube_conf_settings += f"""
db_username: {os.getenv('ODC_DB_ADMIN_USER', 'odc_db_admin')}
db_password: {os.getenv('ODC_DB_ADMIN_PASS', 'insecurePassword')}"""

    else:
        # default to read-only
        datacube_conf_settings += f"""
db_username: {os.getenv('ODC_DB_READ_ONLY_USER', 'odc_db_user')}
db_password: {os.getenv('POSTGRES_DB_PASS', 'worrysomepPassword')}"""

    # pop it in a file for the user
    with open(f'/home/{username}/.datacube.conf', 'w+') as f:
        f.write(datacube_conf_settings)

