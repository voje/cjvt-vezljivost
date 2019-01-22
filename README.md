# CJVT Valency
The app parses a corpus (Kres.xml) and extracts valency frames. 
A web user interface is exposed to list and examine the sentences and valency frames from the input corpus. 
Users can add their own senses to sentences, which are used for grouping sentences and creating sense-specific valency patterns. 

## Deployment
We're using Docker. A single node Docker Swarm, to be exact. 
Check out `./docker/README.md`.
