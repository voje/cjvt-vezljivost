#!/bin/bash

docker stack deploy -c docker-compose.dev.yml valstack

echo "docker ps"
echo "Copy flask_app container's name and open a bash shell into it:"
echo "docker exec -it <name> /bin/bash"
echo "You will need to 'run pip install .' to build your package in dev mode."
