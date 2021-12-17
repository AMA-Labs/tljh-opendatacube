from tljh.hooks import hookimpl
from tljh.user import ensure_group
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
    #Set JupyterLab to be default
    c.Spawner.default_url = '/lab'

    # Setup AWS Cognito OAuthenticator
    c.GenericOAuthenticator.client_id = "[your app client ID]"
    c.GenericOAuthenticator.client_secret = "[your app client secret]"
    c.GenericOAuthenticator.oauth_callback_url = "https://[your-jupyterhub-host]/hub/oauth_callback"

    c.GenericOAuthenticator.authorize_url = "https://your-AWSCognito-domain/oauth2/authorize"
    c.GenericOAuthenticator.token_url = "https://your-AWSCognito-domain/oauth2/token"
    c.GenericOAuthenticator.userdata_url = "https://your-AWSCognito-domain/oauth2/userInfo"
    c.GenericOAuthenticator.logout_redirect_url = "https://your-AWSCognito-domain/oauth2/logout"

    # these are always the same
    c.GenericOAuthenticator.login_service = "AWS Cognito"
    c.GenericOAuthenticator.username_key = "username"
    c.GenericOAuthenticator.userdata_method = "POST"

@hookimpl
def tljh_config_post_install(config):
    """
    Configure shared directory (src: https://github.com/kafonek/tljh-shared-directory/blob/master/tljh_shared_directory.py)
    """
    ### mkdir -p /srv/shared
    ### sudo chown  root:jupyterhub-users /srv/shared
    ### sudo chmod 777 /srv/shared
    ### sudo chmod g+s /srv/shared
    ### sudo ln -s /srv/shared /etc/skel/shared
    sh.mkdir('/srv/shared', '-p')
    # jupyterhub-users doesn't get created until a user logs in
    # make sure it's created before changing permissions on directory
    ensure_group('jupyterhub-users') 
    sh.chown('root:jupyterhub-users', '/srv/shared')
    sh.chmod('777', '/srv/shared')
    sh.chmod('g+s', '/srv/shared')
    sh.ln('-s', '/srv/shared', '/etc/skel/shared')

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
    #Change extents with bbox='<left>,<bottom>,<right>,<top>'
    bbox='-83.675395, 36.540738, -75.242266, 39.466012'
    time_range='2017-06-01/2021-11-01'

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
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube dc-sync-products https://raw.githubusercontent.com/AMA-Labs/odc-tljh/master/products.csv")

    # index default products
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube stac-to-dc --bbox='{bbox}' --catalog-href='https://earth-search.aws.element84.com/v0/' --collections='sentinel-s2-l2a-cogs' --datetime='{time_range}'")
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube stac-to-dc --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='io-lulc'")
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube stac-to-dc --bbox='{bbox}' --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='nasadem'")
    sh.bash("-c", f"source /opt/tljh/user/bin/activate && DB_HOSTNAME=localhost DB_USERNAME=odc_db_admin DB_PASSWORD={odc_db_admin_password} DB_DATABASE=datacube stac-to-dc --bbox='{bbox}' --catalog-href='https://planetarycomputer.microsoft.com/api/stac/v1/' --collections='landsat-8-c2-l2' --datetime='{time_range}")

@hookimpl
def tljh_new_user_create(username):
    """
    Script to be executed after a new user has been added.
    This can be arbitrary Python code.
    """
    