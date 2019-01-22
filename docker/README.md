# The Docker Stack

To run the stack, build all neccessary dockerfiles, 
then run:
```bash
$ docker swarm init  # only once, to init Docker Swarm
$ docker stack deploy -c docker-compose.yml valency_stack
```

## Follow the bash scripts
Just follow the numbered bash scripts for building deploying etc...
