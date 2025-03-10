import logging
import os
import re
import time
from typing import Optional
from urllib.parse import unquote

from func_timeout import func_timeout, FunctionTimedOut
from selenium.common import TimeoutException, NoSuchElementException, InvalidCookieDomainException, WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located, staleness_of
from twocaptcha import TwoCaptcha

from dtos import V1RequestBase, V1ResponseBase, ChallengeResolutionT, ChallengeResolutionResultT, IndexResponse, \
    HealthResponse, STATUS_OK, STATUS_ERROR
import utils

ACCESS_DENIED_SELECTORS = [
    # Cloudflare
    'div.main-wrapper div.header.section h1 span.code-label span'
]

CHALLENGE_SELECTORS = [
    # Cloudflare
    '#cf-challenge-running', '.ray_id', '.attack-box', '#cf-please-wait', '#challenge-spinner', '#trk_jschal_js',
    # DDoS-GUARD
    '#link-ddg',
    # Custom CloudFlare for EbookParadijs, Film-Paleis, MuziekFabriek and Puur-Hollands
    'td.info #js_info'
]

CAPTCHA_SELECTORS = {
    # hCaptcha
    '#challenge-hcaptcha-wrapper': 'hCaptcha',
    # button "Verify you are human"
    '#challenge-stage': 'turnstile'
}

SHORT_TIMEOUT = 5

IS_DEBUG = False


def test_browser_installation():
    logging.info("Testing web browser installation...")
    user_agent = utils.get_user_agent()
    logging.info("FlareSolverr User-Agent: " + user_agent)
    logging.info("Test successful")


def index_endpoint() -> IndexResponse:
    res = IndexResponse({})
    res.msg = "FlareSolverr is ready!"
    res.version = utils.get_flaresolverr_version()
    res.userAgent = utils.get_user_agent()
    return res


def health_endpoint() -> HealthResponse:
    res = HealthResponse({})
    res.status = STATUS_OK
    return res


def controller_v1_endpoint(req: V1RequestBase) -> V1ResponseBase:
    start_ts = int(time.time() * 1000)
    logging.info(f"Incoming request => POST /v1 body: {utils.object_to_dict(req)}")
    res: V1ResponseBase
    try:
        res = _controller_v1_handler(req)
    except Exception as e:
        res = V1ResponseBase({})
        res.__error_500__ = True
        res.status = STATUS_ERROR
        res.message = "Error: " + str(e)
        logging.error(res.message)

    res.startTimestamp = start_ts
    res.endTimestamp = int(time.time() * 1000)
    res.version = utils.get_flaresolverr_version()
    logging.debug(f"Response => POST /v1 body: {utils.object_to_dict(res)}")
    logging.info(f"Response in {(res.endTimestamp - res.startTimestamp) / 1000} s")
    return res


def _controller_v1_handler(req: V1RequestBase) -> V1ResponseBase:
    # do some validations
    if req.cmd is None:
        raise Exception("Request parameter 'cmd' is mandatory.")
    if req.headers is not None:
        logging.warning("Request parameter 'headers' was removed in FlareSolverr v2.")
    if req.userAgent is not None:
        logging.warning("Request parameter 'userAgent' was removed in FlareSolverr v2.")

    # set default values
    if req.maxTimeout is None or req.maxTimeout < 1:
        req.maxTimeout = 60000

    # execute the command
    res: V1ResponseBase
    if req.cmd == 'sessions.create':
        raise Exception("Not implemented yet.")
    elif req.cmd == 'sessions.list':
        raise Exception("Not implemented yet.")
    elif req.cmd == 'sessions.destroy':
        raise Exception("Not implemented yet.")
    elif req.cmd == 'request.get':
        res = _cmd_request_get(req)
    elif req.cmd == 'request.post':
        res = _cmd_request_post(req)
    else:
        raise Exception(f"Request parameter 'cmd' = '{req.cmd}' is invalid.")

    return res


def _cmd_request_get(req: V1RequestBase) -> V1ResponseBase:
    # do some validations
    if req.url is None:
        raise Exception("Request parameter 'url' is mandatory in 'request.get' command.")
    if req.postData is not None:
        raise Exception("Cannot use 'postBody' when sending a GET request.")
    if req.returnRawHtml is not None:
        logging.warning("Request parameter 'returnRawHtml' was removed in FlareSolverr v2.")
    if req.download is not None:
        logging.warning("Request parameter 'download' was removed in FlareSolverr v2.")

    challenge_res = _resolve_challenge(req, 'GET')
    res = V1ResponseBase({})
    res.status = challenge_res.status
    res.message = challenge_res.message
    res.solution = challenge_res.result
    return res


def _cmd_request_post(req: V1RequestBase) -> V1ResponseBase:
    # do some validations
    if req.postData is None:
        raise Exception("Request parameter 'postData' is mandatory in 'request.post' command.")
    if req.returnRawHtml is not None:
        logging.warning("Request parameter 'returnRawHtml' was removed in FlareSolverr v2.")
    if req.download is not None:
        logging.warning("Request parameter 'download' was removed in FlareSolverr v2.")

    challenge_res = _resolve_challenge(req, 'POST')
    res = V1ResponseBase({})
    res.status = challenge_res.status
    res.message = challenge_res.message
    res.solution = challenge_res.result
    return res


def _resolve_challenge(req: V1RequestBase, method: str) -> ChallengeResolutionT:
    timeout = req.maxTimeout / 1000
    driver = None
    try:
        driver = utils.get_webdriver()
        return func_timeout(timeout, _evil_logic, (req, driver, method))
    except FunctionTimedOut:
        raise Exception(f'Error solving the challenge. Timeout after {timeout} seconds.')
    except Exception as e:
        raise Exception('Error solving the challenge. ' + str(e))
    finally:
        if driver is not None:
            driver.quit()


def _evil_logic(req: V1RequestBase, driver: WebDriver, method: str) -> ChallengeResolutionT:
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': """
        function onHCaptchaLoaded() {
          console.log(hcaptcha);
        
          let origFunc = hcaptcha.render;
        
          hcaptcha.render = function (a, b) {
            window.flareCallback = b.callback;
        
            origFunc(a, b);
          };
        }
        
        var hasHCaptchaLoaded = false;
        
        function checkHCaptcha() {
            if (window.hcaptcha !== undefined) {
              onHCaptchaLoaded();
            } else {
              requestAnimationFrame(checkHCaptcha);
            }
        };
        
        requestAnimationFrame(checkHCaptcha);
        """
    })

    _add_cookies(driver, req.url, req.cookies)

    res = ChallengeResolutionT({})
    res.status = STATUS_OK
    res.message = ""

    # navigate to the page
    logging.debug(f'Navigating to... {req.url}')
    if method == 'POST':
        _post_request(req, driver)
    else:
        driver.get(req.url)
    if utils.get_config_log_html():
        logging.debug(f"Response HTML:\n{driver.page_source}")

    # wait for the page
    html_element = driver.find_element(By.TAG_NAME, "html")

    # find access denied selectors
    if _check_access_denied(driver):
        raise Exception('Cloudflare has blocked this request. '
                        'Probably your IP is banned for this site, check in your web browser.')

    # find challenge selectors
    challenge_found = False
    for selector in CHALLENGE_SELECTORS:
        found_elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if len(found_elements) > 0:
            challenge_found = True
            logging.info("Challenge detected. Selector found: " + selector)
            break

    captcha_type = None

    if challenge_found:
        while True:
            try:
                # then wait until all the selectors disappear
                for selector in CHALLENGE_SELECTORS:
                    logging.debug("Waiting for selector: " + selector)
                    WebDriverWait(driver, SHORT_TIMEOUT).until_not(
                        presence_of_element_located((By.CSS_SELECTOR, selector)))
                # all elements not found
                break

            except TimeoutException:
                captcha_type = _captcha_detect_type(driver)

                if captcha_type is not None:
                    if not _captcha_solve(driver, captcha_type):
                        _save_debug_info(driver)

                        res.status = STATUS_ERROR
                        res.message = "Unable to solve captcha of type %s" % captcha_type
                        return res

                    continue

                logging.debug("Timeout waiting for selector")

                # update the html (cloudflare reloads the page every 5 s)
                html_element = driver.find_element(By.TAG_NAME, "html")

        # waits until cloudflare redirection ends
        logging.debug("Waiting for redirect")
        # noinspection PyBroadException
        try:
            WebDriverWait(driver, SHORT_TIMEOUT + 25000).until(staleness_of(html_element))
        except Exception:
            logging.debug("Timeout waiting for redirect")

        logging.info("Challenge solved!")
        res.message = "Challenge solved!"
    else:
        logging.info("Challenge not detected!")
        res.message = "Challenge not detected!"

    challenge_res = ChallengeResolutionResultT({})
    challenge_res.url = driver.current_url
    challenge_res.status = 200  # todo: fix, selenium not provides this info
    challenge_res.captcha_type = captcha_type
    challenge_res.cookies = driver.get_cookies()
    challenge_res.userAgent = utils.get_user_agent(driver)

    if not req.returnOnlyCookies:
        challenge_res.headers = {}  # todo: fix, selenium not provides this info
        challenge_res.response = driver.page_source

    res.result = challenge_res
    return res


def _post_request(req: V1RequestBase, driver: WebDriver):
    post_form = f'<form id="hackForm" action="{req.url}" method="POST">'
    query_string = req.postData if req.postData[0] != '?' else req.postData[1:]
    pairs = query_string.split('&')
    for pair in pairs:
        parts = pair.split('=')
        # noinspection PyBroadException
        try:
            name = unquote(parts[0])
        except Exception:
            name = parts[0]
        if name == 'submit':
            continue
        # noinspection PyBroadException
        try:
            value = unquote(parts[1])
        except Exception:
            value = parts[1]
        post_form += f'<input type="text" name="{name}" value="{value}"><br>'
    post_form += '</form>'
    html_content = f"""
        <!DOCTYPE html>
        <html>
        <body>
            {post_form}
            <script>document.getElementById('hackForm').submit();</script>
        </body>
        </html>"""
    driver.get("data:text/html;charset=utf-8," + html_content)


def _add_cookies(driver: WebDriver, url: str, cookies: Optional[list]):
    if cookies is None:
        return

    # Enables network tracking so we may use Network.setCookie method
    driver.execute_cdp_cmd('Network.enable', {})

    try:
        for cookie in cookies:
            driver.execute_cdp_cmd('Network.setCookie', cookie)
    except WebDriverException as e:
        logging.error("Failed to add cookies %s" % e)
        raise Exception("Failed to add cookies: %s" % e.msg)
    finally:
        # Disable network tracking
        driver.execute_cdp_cmd('Network.disable', {})


def _check_access_denied(driver: WebDriver):
    for selector in ACCESS_DENIED_SELECTORS:
        found_elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if len(found_elements) > 0:
            return True

    return False


def _captcha_detect_type(driver: WebDriver):
    for selector in CAPTCHA_SELECTORS:
        found_elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if len(found_elements) > 0:
            return CAPTCHA_SELECTORS[selector]

    return None


def _captcha_solve(driver: WebDriver, captcha_type: str) -> bool:
    logging.debug('Detected %s captcha' % captcha_type)

    if captcha_type == 'hCaptcha':
        logging.debug('[hCaptcha] Searching for sitekey')

        # Parse sitekey.
        c_iframe = driver.find_element(By.TAG_NAME, 'iframe')
        c_iframe_src = c_iframe.get_attribute('src')

        # Find hCaptcha sitekey.
        sitekey = re.findall(r"sitekey=([a-z0-9-]+)&", c_iframe_src)[0]
        logging.debug('[hCaptcha] Found sitekey %s' % sitekey)

        # Find element in which the result goes.
        result_el = driver.find_element(By.CSS_SELECTOR, 'textarea[name="h-captcha-response"]')
        logging.debug('[hCaptcha] Found hcaptcha response textarea with id %s' % result_el.get_attribute('id'))

        # Solve captcha.
        logging.debug('[hCaptcha] Sitekey %s' % sitekey)
        logging.debug('[hCaptcha] Url %s' % driver.current_url)

        result_code = _captcha_solver_external(sitekey, driver.current_url)

        logging.debug('[hCaptcha] External result %s' % result_code)

        # Set captcha result.
        logging.debug('[hCaptcha] Calling callback')
        driver.execute_script('window.flareCallback("%s");' % result_code)
        logging.debug('[hCaptcha] Called callback')

        return True
    elif captcha_type == 'turnstile':
        # Find button to press.
        logging.debug('[turnstile] Searching for button')

        c_switched = False
        c_button = driver.find_elements(By.CSS_SELECTOR, '.big-button.pow-button')

        if len(c_button) != 1:
            logging.debug('[turnstile] Searching for other button')

            try:
                c_iframe = driver.find_element(By.TAG_NAME, 'iframe')

                driver.switch_to.frame(c_iframe)

                c_switched = True
                c_button = driver.find_elements(By.CSS_SELECTOR, 'span.mark')
            except NoSuchElementException:
                logging.debug('[turnstile] Relevant element not found')

        if len(c_button) != 1:
            logging.debug('[turnstile] Unable to find button (%d)' % len(c_button))
            return False

        # Click the button.
        logging.debug('[turnstile] Clicking button')

        c_button[0].click()

        # Switch back.
        if c_switched:
            driver.switch_to.parent_frame()

        return True

    return False


def _captcha_solver_external(sitekey: str, url: str):
    two_captcha_key = os.environ.get('2CAPTCHA_KEY', None)

    if two_captcha_key is not None:
        solver = TwoCaptcha(**{
            'server': '2captcha.com',
            'apiKey': two_captcha_key,
            'defaultTimeout': 120,
            'recaptchaTimeout': 600,
            'pollingInterval': 5,
        })

        logging.debug('[hCaptcha] Solving with 2Captcha')

        result = solver.hcaptcha(sitekey=sitekey, url=url)

        return result['code']

    raise Exception('No hCaptcha solver was configured')


def _save_debug_info(driver):
    if not IS_DEBUG:
        return

    logging.debug('Saving debug info')

    if os.path.exists('/screenshots'):
        file_name = '/screenshots/%d' % (int(time.time() * 1000))
    else:
        file_name = os.path.join(os.path.dirname(__file__), '..', 'screenshots', str(int(time.time() * 1000)))

    driver.save_screenshot('%s.png' % file_name)

    with open('%s.html' % file_name, 'w') as f:
        f.write(driver.page_source)
