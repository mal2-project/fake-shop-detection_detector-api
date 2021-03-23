# Fake-Shop Detector API

## About / Synopsis

* central source for serving browser plugin
* homogeneously integrates multiple local or api providers of trustworthy and known fraudulent sites
* provides mal2-model prediction capabilities
* caching and load balancing
* Project status: working/prototype

## Table of contents

> * [Requirements](#requirements)
> * [Installation](#installation)
> * [Usage](#usage)
> * [Running with Docker](#Running-with-Docker)
> * [REST-API](#rest-api)
> * [About MAL2](#about-mal2)
> * [Contact](#contact)
> * [License](#license)

## Requirements

* Ubuntu 16.04
* Python 3.8
* PostgreSQL 10
* Python-Packages as defined in [requirments.txt](backend-api-server/requirements.txt)

## Installation

Create a Python virtual environment with e.g. [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) or anaconda.
The Python version used is 3.8.

```shell
$ mkvirtualenv -p /path/to/python3.8 rest-api
```

Install the required Python packages

```shell
pip install -r backend-api-server/requirements.txt
```

PostgreSQL 10 is used as database. Create a database and change the `backend-api-server/swagger_server/mals/db/handler/db_handler.py` accordingly.

The database initializiation is done by calling init-mal2-db.sh
```shell
#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE mal2user WITH LOGIN PASSWORD 'change_pass' SUPERUSER INHERIT CREATEDB CREATEROLE;
    CREATE DATABASE mal2restdb OWNER mal2user;
EOSQL
```

## Usage

To run the server, please execute the following from the backend-api-server directory:

```
python3 -m swagger_server
```

and point your browser to:

```
http://localhost:8080/malzwei/ecommerce/1.1/ui/
```

Your Swagger definition lives here:

```
http://localhost:8080/malzwei/ecommerce/1.1/swagger.json
```

Attention, this is for development only. In a production environment, for example, [uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/WSGIquickstart.html) can be used with [apache2](http://httpd.apache.org/).

## Running with Docker

For a full local deployment with an external db launch the docker build:
```shell
# starting the containers
docker-compose -f docker-compose.local_dev.yml up
```

For a full server deployment launch the docker build:
```shell
# building the image
docker-compose build --build-arg ENDPOINT_BASE=your.server.location

# starting the containers
docker-compose up
```

All details on the docker stand-alon or docker-compose build are provided in the files
`docker-compose.yml`
`docker-compose.local_dev.yml`
and
`backend-api-server/docker/Dockerfile`

The code as is contains settings for local dev deployment. The Dockerfile uses 'sed' to provide the production configuration and docker-compose up to start the integrated system
`RUN sed -i "s|127.0.0.1|$env_ENDPOINT_BASE|g" swagger_server/swagger/swagger.yaml`

## REST-API

The REST API documentation is available at http://localhost:8081/malzwei/ecommerce/1.1/ui/.

Please note all port configurations of the server are defined within the docker-compose build stage. Therefore make sure when adjusting the ports within docker-compose.yml to have identical ports for container and host within the mal2-rest-api service as they are passed to connexion[swagger-ui] at build time.

## About MAL2

The MAL2 project applies Deep Neural Networks and Unsupervised Machine Learning to advance cybercrime prevention by a) automating the discovery of fraudulent eCommerce and b) detecting Potentially Harmful Apps (PHAs) in Android.
The goal of the MAL2 project is to provide (i) an Open Source framework and expert tools with integrated functionality along the required pipeline – from malicious data archiving, feature selection and extraction, training of Machine Learning classification and detection models towards explainability in the analysis of results (ii) to execute its components at scale and (iii) to publish an annotated Ground-Truth dataset in both application domains. To raise awareness for cybercrime prevention in the general public, two demonstrators, a Fake-Shop Detection Browser Plugin as well as a Android Malware Detection Android app are released that allow live-inspection and AI based predictions on the trustworthiness of eCommerce sites and Android apps.

The work is based on results carried out in the research project [MAL2 project](https://projekte.ffg.at/projekt/3044975), which was partially funded by the Austrian Federal Ministry for Climate Action, Environment, Energy, Mobility, Innovation and Technology (BMK) through the ICT of the future research program (6th call) managed by the Austrian federal funding agency (FFG).
* Austrian Institute of Technology GmbH, Center for Digital Safety and Security [AIT](https://www.ait.ac.at/)
* Austrian Institute for Applied Telecommunications [ÖIAT](https://www.oiat.at)
* X-NET Services GmbH [XNET](https://x-net.at/de/)
* Kuratorium sicheres Österreich [KSÖ](https://kuratorium-sicheres-oesterreich.at/)
* IKARUS Security Software [IKARUS](https://www.ikarussecurity.com/)

More information is available at [www.malzwei.at](http://www.malzwei.at)

## Contact
For details on behalf of the MAL2 consortium contact: 
Andrew Lindley (project lead)
Research Engineer, Data Science & Artificial Intelligence
Center for Digital Safety and Security, AIT Austrian Institute of Technology GmbH
Giefinggasse 4 | 1210 Vienna | Austria
T +43 50550-4272 | M +43 664 8157848 | F +43 50550-4150
andrew.lindley@ait.ac.at | www.ait.ac.at
or
Woflgang Eibner, X-NET Services GmbH, we@x-net.at

## License
The MAL2 Software stack is dual-licensed under commercial and open source licenses. 
The Software in this repository is subject of the terms and conditions defined in file 'LICENSE.md'
