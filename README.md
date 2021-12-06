# Open Data Cube Plugin for The Littlest JupyterHub
![odc-logo](https://static.wixstatic.com/media/8959d6_af917b5494184676952b5bc69f6d5e7b~mv2_d_14168_4343_s_3_2.png)

A plugin for [The Littlest JupyterHub (TLJH)](https://tljh.jupyter.org) that installs a [The Open Datacube](https://www.opendatacube.org/).

![odc-logo](https://static.wixstatic.com/media/f9d4ea_b8902e098bc244929b418980ce21b23f~mv2.jpg/v1/fill/w_1920,h_595,al_c,q_85/f9d4ea_b8902e098bc244929b418980ce21b23f~mv2.webp)
## About
---
The Open Data Cube makes managing and processing Earth observation data easier by organizing the metadata and files available from different platforms and providing a simple interface to reproject and access data as arrays.

This plugin provides a simple way for groups and institutions to setup an Open Datacube for multiple users to access through the Jupyter enviroment.

## Install
---
Follow [one of the tutorials to install TLJH](https://tljh.jupyter.org/en/latest/#installation) and at the step asking for user data, modify the command [as documented for installing plugins](https://tljh.jupyter.org/en/latest/topic/customizing-installer.html?highlight=plugin#installing-tljh-plugins)

For Example:
```
#!/bin/bash
curl https://raw.githubusercontent.com/jupyterhub/the-littlest-jupyterhub/master/bootstrap/bootstrap.py \
 | sudo python3 - \
   --admin odc-admin:<replacepassword> --show-progress-page --plugin git+https://github.com/AMA-Labs/odc-tljh
```