FROM python:3.7.6-buster

#Sets the APIs public endpoint default-location to localhost
#override by calling docker-compose build --build-arg ENDPOINT_BASE=mal2.ait.ac.at
ARG ENDPOINT_BASE=localhost
ARG ENDPOINT_PORT=8080
RUN echo "building MAL2-REST API public endpoint: '$ENDPOINT_BASE' port: '$ENDPOINT_PORT'"

#our working dir in the container
RUN mkdir -p /mal2/rest-api
WORKDIR /mal2/rest-api

# need to copy as volumens are only accessible once container created
COPY ./backend-api-server/. /mal2/rest-api

#install our mal2-model dependency
RUN pip3 install docker/kosoh_logo_classifier-0.1-py3-none-any.whl
RUN pip3 install docker/mal2_fakeshop_models-0.25-py3-none-any.whl

#install swagger-ui which allows browsing open-api app routes e.g. http://localhost:8080/malzwei/ecommerce/1.1/ui/
RUN pip3 install connexion[swagger-ui]

#install all other dependencies for the mal2-rest app
RUN pip3 install --no-cache-dir -r requirements.txt

#replace the mal2 apps db configuration (port and host) using sed
RUN sed -i 's/54320/5432/g' swagger_server/mal2/db/handler/db_handler.py
RUN sed -i 's/127.0.0.1/mal2-fakeshop-plugin_rest-api_db/g' swagger_server/mal2/db/handler/db_handler.py

#ENV vars are available to container (also beyond build)
ENV env_ENDPOINT_BASE=$ENDPOINT_BASE
ENV env_ENDPOINT_PORT=$ENDPOINT_PORT

#replace API public endpoint location. [used by swagger-ui]
RUN sed -i "s|127.0.0.1|$env_ENDPOINT_BASE|g" swagger_server/swagger/swagger.yaml
RUN sed -i "s|8080|$env_ENDPOINT_PORT|g" swagger_server/swagger/swagger.yaml
RUN sed -i "s|8080|$env_ENDPOINT_PORT|g" swagger_server/__main__.py

#remove data import limits i.e. import all 
RUN sed -i "s|limit_imported_items=10||g" swagger_server/mal2/db/handler/db_whitelist_handler.py
RUN sed -i "s|limit_imported_items=10||g" swagger_server/mal2/db/handler/db_ignorelist_handler.py
RUN sed -i "s|limit_imported_items=10||g" swagger_server/mal2/db/handler/db_blacklist_handler.py
RUN sed -i "s|limit_imported_items=10||g" swagger_server/mal2/db/handler/db_greylist_handler.py
RUN sed -i "s|limit_imported_items=10||g" swagger_server/mal2/db/handler/db_handler.py

#for debugging container interactively
#ENTRYPOINT ["sh", "-c", "sleep 2073600"]

EXPOSE $ENDPOINT_PORT

ENTRYPOINT ["python3"]

CMD ["-m", "swagger_server"]

