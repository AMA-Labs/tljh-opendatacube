from tljh.hooks import hookimpl
import sh

@hookimpl
def tljh_extra_user_conda_packages():
    return [
        'gdal==3.3.2',
        'Cython',
        'numpy',
        'pandas',
        'xarray',
        'matplotlib-base',
        'rasterio',
        'folium',
        'scipy',
        'scikit-image',
        'geopandas',
        'tqdm',
        'click',
        ]

@hookimpl
def tljh_extra_user_pip_packages():
    return [
        # 'Cython',
        # 'numpy',
        # 'rasterio',
        '--extra-index-url=https://packages.dea.ga.gov.au',
        'datacube[performance,s3]==1.8.6',
        'eodatasets3',
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
        'datacube-stats',
        # 'gdal==3.3.2',
        # 'folium',
        # 'scipy',
        # 'pandas==1.3.4',
        # 'xarray',
        # 'matplotlib==3.4.3',
        # 'geopandas',
        # 'scikit-image',
        # 'tqdm',
        # 'click<8.0.0',
        'python-dateutil==2.7.5',
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
        'less',
        'wget',
        'curl',
        'vim',
        'htop',
        'unzip',
        'zip',
        'python3-dev',
        'libpq-dev',
        'postgresql',
        'postgresql-contrib',
        'postgis',
    ]

@hookimpl
def tljh_custom_jupyterhub_config(c):
    """
    Provide custom traitlet based config to JupyterHub.
    Anything you can put in `jupyterhub_config.py` can
    be here.
    """
    pass

@hookimpl
def tljh_config_post_install(config):
    """
    Set JupyterLab to be default
    """
    user_environment = config.get('user_environment', {})
    user_environment['default_app'] = user_environment.get(
        'default_app', 'jupyterlab')

    config['user_environment'] = user_environment

@hookimpl
def tljh_post_install():
    """
    Post install script to be executed after installation
    and after all the other hooks.
    This can be arbitrary Python code.
    """
    postgres_password = 'superPassword'
    odc_db_admin_password = 'insecurePassword'
    odc_db_user_password = 'worrysomePassword'
    bbox='146.8,-36.3, 147.3, -35.8'
    time_range='2021-06-01/2021-07-01'

    # Start postgresql
    sh.systemctl("enable", "postgresql")
    sh.service("postgresql", "restart")

    # Some guards in case running the install script repeatedly in same container. This will remove the database
    su_postgres = sh.su.bake("-", "postgres", "-c")

    su_postgres("psql -c 'DROP DATABASE IF EXISTS datacube;'")
    su_postgres("psql -c 'DROP EXTENSION IF EXISTS postgis;'")
    su_postgres("psql -c 'DROP ROLE IF EXISTS odc_db_admin;'")
    su_postgres("psql -c 'DROP ROLE IF EXISTS odc_db_user;'")

    # Configure postgres and create datacube database
    su_postgres("psql -c 'CREATE EXTENSION postgis;'")
    su_postgres("psql -c 'CREATE DATABASE datacube;'")
    # The datacube system commands will require a postgres super user password
    # and also the specification to use localhost for the database hostname
    su_postgres(f"psql -c \"ALTER USER postgres PASSWORD \'{postgres_password}\';\"")
    su_postgres(f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=postgres DB_PASSWORD={postgres_password} DB_DATABASE=datacube datacube -v system init")
    su_postgres(f"psql -c \"CREATE ROLE odc_db_admin WITH LOGIN IN ROLE agdc_admin, agdc_user ENCRYPTED PASSWORD \'{odc_db_admin_password}\';\"")
    su_postgres(f"psql -c \"CREATE ROLE odc_db_user WITH LOGIN IN ROLE agdc_user ENCRYPTED PASSWORD \'{odc_db_user_password}\';\"")
    su_postgres("psql -c 'ALTER DATABASE datacube OWNER TO odc_db_admin;'")

    # initialise datacube database  default products
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube dc-sync-products https://raw.githubusercontent.com/woodcockr/tljh-oea/main/products.csv")

    # index default products
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube stac-to-dc --bbox='{bbox}' --catalog-href='https://earth-search.aws.element84.com/v0/' --collections='sentinel-s2-l2a-cogs' --datetime='{time_range}'")
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube stac-to-dc --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='io-lulc'")
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube stac-to-dc --bbox='{bbox}' --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='nasadem'")

@hookimpl
def tljh_new_user_create(username):
    """
    Script to be executed after a new user has been added.
    This can be arbitrary Python code.
    """
    