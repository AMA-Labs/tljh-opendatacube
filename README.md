# An Open Data Cube Plugin for The Littlest JupyterHub

![odc-logo](https://static.wixstatic.com/media/f9d4ea_b8902e098bc244929b418980ce21b23f~mv2.jpg/v1/fill/w_1920,h_595,al_c,q_85/f9d4ea_b8902e098bc244929b418980ce21b23f~mv2.webp)


## About
---
This plugin provides a simple way for groups and institutions to utilize [Open Data Cube](https://www.opendatacube.org/) for multiple users with Jupyter Notebooks

The `tljh-opendatacube` plugin..
- installs Open Data Cube in the host venv, making it available for each user
- installs any ODC dependancies as well as a few standard datascience packages
- installs PostgreSQL and sets up the database required to operate ODC
- creates a `datacube.conf` file for each user
- and configures a shared directory for users

![odc-logo](https://static.wixstatic.com/media/8959d6_af917b5494184676952b5bc69f6d5e7b~mv2_d_14168_4343_s_3_2.png)


The Open Data Cube makes managing and processing Earth observation data easier by organizing the metadata and files available from different platforms and providing a simple interface to reproject and access data as arrays.


## Usage
---
When installing TLJH, you will need to append this plugin as an argument to the `curl` bootstrap/install script:

`--plugin git+https://github.com/AMA-Labs/tljh-opendatacube`

For Example:
```sh
curl https://raw.githubusercontent.com/jupyterhub/the-littlest-jupyterhub/master/bootstrap/bootstrap.py | sudo python3 - \
   --admin <admin-name>:<admin-password> \
   --plugin git+https://github.com/AMA-Labs/tljh-opendatacube
```

## More Information
- [Installing TLJH](https://tljh.jupyter.org/en/latest/#installation)
- [Installing TLJH Plugins](https://tljh.jupyter.org/en/latest/topic/customizing-installer.html?highlight=plugin#installing-tljh-plugins)