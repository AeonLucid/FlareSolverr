FROM ubuntu:22.04

# Install dependencies and create flaresolverr user
# You can test Chromium running this command inside the container:
#    xvfb-run -s "-screen 0 1600x1200x24" chromium --no-sandbox
# The error traces is like this: "*** stack smashing detected ***: terminated"
# To check the package versions available you can use this command:
#    apt-cache madison chromium
WORKDIR /app

# Install packages
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:saiarcot895/chromium-beta && \
    apt-get update && \
    apt-get install -y \
    chromium-browser=1:108.0.5359.40-0ubuntu1~ppa1~22.04.1 \
    xvfb \
    python3-pip \
    && \
    # Remove temporary files and hardware decoding libraries
    rm -rf /var/lib/apt/lists/* && \
    rm -f /usr/lib/x86_64-linux-gnu/libmfxhw* && \
    rm -rf /root/.cache

# Install Python dependencies
COPY requirements.txt .

RUN pip install -r requirements.txt && \
    # Remove temporary files
    find / -name '*.pyc' -delete

# Create flaresolverr user
RUN useradd --home-dir /app --shell /bin/sh flaresolverr && \
    chown -R flaresolverr:flaresolverr .

USER flaresolverr

COPY src .
COPY package.json ../

EXPOSE 8191

CMD ["/usr/bin/python3", "-u", "/app/flaresolverr.py"]
