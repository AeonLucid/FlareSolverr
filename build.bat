docker build -t flaresolverr .
docker rm flaresolverr
docker volume rm screenshots
docker run --name=flaresolverr -v screenshots:/screenshots -p 8191:8191 -e LOG_LEVEL=debug -it flaresolverr