docker build -t flaresolverr .
docker run --name=flaresolverr -p 8191:8191 -e LOG_LEVEL=debug -it flaresolverr