# FlareSolverr

[![Docker Pulls](https://img.shields.io/docker/pulls/flaresolverr/flaresolverr)](https://hub.docker.com/r/flaresolverr/flaresolverr/)
[![GitHub issues](https://img.shields.io/github/issues/FlareSolverr/FlareSolverr)](https://github.com/FlareSolverr/FlareSolverr/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/FlareSolverr/FlareSolverr)](https://github.com/FlareSolverr/FlareSolverr/pulls)
[![Donate PayPal](https://img.shields.io/badge/Donate-PayPal-yellow.svg)](https://www.paypal.com/paypalme/diegoheras0xff)
[![Donate Bitcoin](https://img.shields.io/badge/Donate-Bitcoin-f7931a.svg)](https://www.blockchain.com/btc/address/13Hcv77AdnFWEUZ9qUpoPBttQsUT7q9TTh)
[![Donate Ethereum](https://img.shields.io/badge/Donate-Ethereum-8c8c8c.svg)](https://www.blockchain.com/eth/address/0x0D1549BbB00926BF3D92c1A8A58695e982f1BE2E)

FlareSolverr is a proxy server to bypass Cloudflare and DDoS-GUARD protection.

## How it works

FlareSolverr starts a proxy server, and it waits for user requests in an idle state using few resources.
When some request arrives, it uses [Selenium](https://www.selenium.dev) with the
[undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
to create a web browser (Chrome). It opens the URL with user parameters and waits until the Cloudflare challenge
is solved (or timeout). The HTML code and the cookies are sent back to the user, and those cookies can be used to
bypass Cloudflare using other HTTP clients.

**NOTE**: Web browsers consume a lot of memory. If you are running FlareSolverr on a machine with few RAM, do not make
many requests at once. With each request a new browser is launched.

## Installation

### Docker

It is recommended to install using a Docker container because the project depends on an external browser that is
already included within the image.

```bash
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  -e 2CAPTCHA_KEY=KEY \
  --restart unless-stopped \
  ghcr.io/aeonlucid/flaresolverr:v3.0.0
```

If your host OS is Debian, make sure `libseccomp2` version is 2.5.x. You can check the version with `sudo apt-cache policy libseccomp2` 
and update the package with `sudo apt install libseccomp2=2.5.1-1~bpo10+1` or `sudo apt install libseccomp2=2.5.1-1+deb11u1`.
Remember to restart the Docker daemon and the container after the update.

### From source code

This is the recommended way for macOS users and for developers.
* Install [Python 3.10](https://www.python.org/downloads/).
* Install [Chrome](https://www.google.com/intl/en_us/chrome/) or [Chromium](https://www.chromium.org/getting-involved/download-chromium/) web browser.
* (Only in Linux / macOS) Install [Xvfb](https://en.wikipedia.org/wiki/Xvfb) package.
* Clone this repository and open a shell in that path.
* Run `pip install -r requirements.txt` command to install FlareSolverr dependencies.
* Run `python src/flaresolverr.py` command to start FlareSolverr.

## Usage

Example request:
```bash
curl -L -X POST 'http://localhost:8191/v1' \
-H 'Content-Type: application/json' \
--data-raw '{
  "cmd": "request.get",
  "url": "http://www.google.com/",
  "maxTimeout": 60000
}'
```

### Commands

#### + `request.get`

| Parameter         | Notes                                                                                                                                                                                                                                                                                                                                        |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| url               | Mandatory                                                                                                                                                                                                                                                                                                                                    |
| maxTimeout        | Optional, default value 60000. Max timeout to solve the challenge in milliseconds.                                                                                                                                                                                                                                                           |
| returnOnlyCookies | Optional, default false. Only returns the cookies. Response data, headers and other parts of the response are removed.                                                                                                                                                                                                                       |

:warning: If you want to use Cloudflare clearance cookie in your scripts, make sure you use the FlareSolverr User-Agent too. If they don't match you will see the challenge.

Example response from running the `curl` above:

```json
{
    "status": "ok",
    "message": "Challenge solved!",
    "solution": {
        "url": "https://www.google.com/?gws_rd=ssl",
        "status": 200,
        "captcha_type": "hCaptcha",
        "cookies": [
            {
                "name": "NID",
                "value": "204=QE3Ocq15XalczqjuDy52HeseG3zAZuJzID3R57...",
                "domain": ".google.com",
                "path": "/",
                "expires": 1610684149.307722,
                "size": 178,
                "httpOnly": true,
                "secure": true,
                "session": false,
                "sameSite": "None"
            },
            {
                "name": "1P_JAR",
                "value": "2020-07-16-04",
                "domain": ".google.com",
                "path": "/",
                "expires": 1597464949.307626,
                "size": 19,
                "httpOnly": false,
                "secure": true,
                "session": false,
                "sameSite": "None"
            }
        ],
        "userAgent": "Windows NT 10.0; Win64; x64) AppleWebKit/5..."
    },
    "startTimestamp": 1594872947467,
    "endTimestamp": 1594872949617,
    "version": "1.0.0"
}
```

### + `request.post`

This is the same as `request.get` but it takes one more param:

| Parameter | Notes                                                                    |
|-----------|--------------------------------------------------------------------------|
| postData  | Must be a string with `application/x-www-form-urlencoded`. Eg: `a=b&c=d` |

## Environment variables

| Name            | Default                | Notes                                                                                                                                                         |
|-----------------|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| HOST            | 0.0.0.0                | Listening interface. You don't need to change this if you are running on Docker.                                                                              |
| PORT            | 8191                   | Listening port. You don't need to change this if you are running on Docker.                                                                                   |
| LOG_LEVEL       | info                   | Verbosity of the logging. Use `LOG_LEVEL=debug` for more information.                                                                                         |
| LOG_HTML        | false                  | Only for debugging. If `true` all HTML that passes through the proxy will be logged to the console in `debug` level.                                          |
| 2CAPTCHA_KEY    | none                   | An API key for https://2captcha.com/, to solve hCaptcha.                                                                                                      |
| TZ              | UTC                    | Timezone used in the logs and the web browser. Example: `TZ=Europe/London`.                                                                                   |
| HEADLESS        | true                   | Only for debugging. To run the web browser in headless mode or visible.                                                                                       |

## Captcha Solvers

Sometimes CloudFlare not only gives mathematical computations and browser tests, sometimes they also require the user to
solve a captcha.
If this is the case, FlareSolverr will return the error `No hCaptcha solver was configured.`

FlareSolverr can be customized to solve the captchas automatically by setting the environment variable `2CAPTCHA_KEY`.

## Related projects

* C# implementation => https://github.com/FlareSolverr/FlareSolverrSharp
