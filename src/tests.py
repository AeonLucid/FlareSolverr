import unittest
from datetime import datetime, timezone

from webtest import TestApp

from dtos import IndexResponse, HealthResponse, V1ResponseBase, STATUS_OK, STATUS_ERROR
import flaresolverr
import utils


def _find_obj_by_key(key: str, value: str, _list: list) -> dict | None:
    for obj in _list:
        if obj[key] == value:
            return obj
    return None


class TestFlareSolverr(unittest.TestCase):

    proxy_url = "http://127.0.0.1:8888"
    proxy_socks_url = "socks5://127.0.0.1:1080"
    google_url = "https://www.google.com"
    post_url = "https://ptsv2.com/t/qv4j3-1634496523"
    cloudflare_url = "https://nowsecure.nl"
    cloudflare_url_2 = "https://idope.se/torrent-list/harry/"
    ddos_guard_url = "https://anidex.info/"
    custom_cloudflare_url = "https://www.muziekfabriek.org"
    cloudflare_blocked_url = "https://avistaz.to/api/v1/jackett/torrents?in=1&type=0&search="

    app = TestApp(flaresolverr.app)

    def test_wrong_endpoint(self):
        res = self.app.get('/wrong', status=404)
        self.assertEqual(res.status_code, 404)

        body = res.json
        self.assertEqual("Not found: '/wrong'", body['error'])
        self.assertEqual(404, body['status_code'])

    def test_index_endpoint(self):
        res = self.app.get('/')
        self.assertEqual(res.status_code, 200)

        body = IndexResponse(res.json)
        self.assertEqual("FlareSolverr is ready!", body.msg)
        self.assertEqual(utils.get_flaresolverr_version(), body.version)
        self.assertIn("Chrome/", body.userAgent)

    def test_health_endpoint(self):
        res = self.app.get('/health')
        self.assertEqual(res.status_code, 200)

        body = HealthResponse(res.json)
        self.assertEqual(STATUS_OK, body.status)

    def test_v1_endpoint_wrong_cmd(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.bad",
            "url": self.google_url
        }, status=500)
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_ERROR, body.status)
        self.assertEqual("Error: Request parameter 'cmd' = 'request.bad' is invalid.", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version) 

    def test_v1_endpoint_request_get_no_cloudflare(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.google_url
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge not detected!", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version) 

        solution = body.solution
        self.assertIn(self.google_url, solution.url)
        self.assertEqual(solution.status, 200)
        self.assertIs(len(solution.headers), 0)
        self.assertIn("<title>Google</title>", solution.response)
        self.assertGreater(len(solution.cookies), 0)
        self.assertIn("Chrome/", solution.userAgent)

    def test_v1_endpoint_request_get_cloudflare_js_1(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.cloudflare_url
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge solved!", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version) 

        solution = body.solution
        self.assertIn(self.cloudflare_url, solution.url)
        self.assertEqual(solution.status, 200)
        self.assertIs(len(solution.headers), 0)
        self.assertIn("<title>nowSecure</title>", solution.response)
        self.assertGreater(len(solution.cookies), 0)
        self.assertIn("Chrome/", solution.userAgent)

        cf_cookie = _find_obj_by_key("name", "cf_clearance", solution.cookies)
        self.assertIsNotNone(cf_cookie, "Cloudflare cookie not found")
        self.assertGreater(len(cf_cookie["value"]), 30)

    def test_v1_endpoint_request_get_cloudflare_js_2(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.cloudflare_url_2
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge solved!", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version) 

        solution = body.solution
        self.assertIn(self.cloudflare_url_2, solution.url)
        self.assertEqual(solution.status, 200)
        self.assertIs(len(solution.headers), 0)
        self.assertIn("<title>harry - idope torrent search</title>", solution.response)
        self.assertGreater(len(solution.cookies), 0)
        self.assertIn("Chrome/", solution.userAgent)

        cf_cookie = _find_obj_by_key("name", "cf_clearance", solution.cookies)
        self.assertIsNotNone(cf_cookie, "Cloudflare cookie not found")
        self.assertGreater(len(cf_cookie["value"]), 30)

    def test_v1_endpoint_request_get_ddos_guard_js(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.ddos_guard_url
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge solved!", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version) 

        solution = body.solution
        self.assertIn(self.ddos_guard_url, solution.url)
        self.assertEqual(solution.status, 200)
        self.assertIs(len(solution.headers), 0)
        self.assertIn("<title>AniDex</title>", solution.response)
        self.assertGreater(len(solution.cookies), 0)
        self.assertIn("Chrome/", solution.userAgent)

        cf_cookie = _find_obj_by_key("name", "__ddg1_", solution.cookies)
        self.assertIsNotNone(cf_cookie, "DDOS-Guard cookie not found")
        self.assertGreater(len(cf_cookie["value"]), 10)

    def test_v1_endpoint_request_get_custom_cloudflare_js(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.custom_cloudflare_url
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge solved!", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version) 

        solution = body.solution
        self.assertIn(self.custom_cloudflare_url, solution.url)
        self.assertEqual(solution.status, 200)
        self.assertIs(len(solution.headers), 0)
        self.assertIn("<title>MuziekFabriek : Aanmelden</title>", solution.response)
        self.assertGreater(len(solution.cookies), 0)
        self.assertIn("Chrome/", solution.userAgent)

        cf_cookie = _find_obj_by_key("name", "ct_anti_ddos_key", solution.cookies)
        self.assertIsNotNone(cf_cookie, "Custom Cloudflare cookie not found")
        self.assertGreater(len(cf_cookie["value"]), 10)

    # todo: test Cmd 'request.get' should return fail with Cloudflare CAPTCHA

    def test_v1_endpoint_request_get_cloudflare_blocked(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.cloudflare_blocked_url
        }, status=500)
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_ERROR, body.status)
        self.assertEqual("Error: Error solving the challenge. Cloudflare has blocked this request. "
                         "Probably your IP is banned for this site, check in your web browser.", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version)

    # todo: test Cmd 'request.get' should return OK with 'cookies' param

    def test_v1_endpoint_request_get_returnOnlyCookies_param(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.google_url,
            "returnOnlyCookies": True
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge not detected!", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version)

        solution = body.solution
        self.assertIn(self.google_url, solution.url)
        self.assertEqual(solution.status, 200)
        self.assertIsNone(solution.headers)
        self.assertIsNone(solution.response)
        self.assertGreater(len(solution.cookies), 0)
        self.assertIsNone(solution.userAgent)

    # todo: test Cmd 'request.get' should return OK with HTTP 'proxy' param
    # todo: test Cmd 'request.get' should return OK with HTTP 'proxy' param with credentials
    # todo: test Cmd 'request.get' should return OK with SOCKSv5 'proxy' param
    # todo: test Cmd 'request.get' should fail with wrong 'proxy' param

    def test_v1_endpoint_request_get_fail_timeout(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.google_url,
            "maxTimeout": 10
        }, status=500)
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_ERROR, body.status)
        self.assertEqual("Error: Error solving the challenge. Timeout after 0.01 seconds.", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version)

    def test_v1_endpoint_request_get_fail_bad_domain(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": "https://www.google.combad"
        }, status=500)
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_ERROR, body.status)
        self.assertIn("Message: unknown error: net::ERR_NAME_NOT_RESOLVED", body.message)

    def test_v1_endpoint_request_get_deprecated_param(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.google_url,
            "userAgent": "Test User-Agent"  # was removed in v2, not used
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge not detected!", body.message)

    def test_v1_endpoint_request_post_no_cloudflare(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.post",
            "url": self.post_url + '/post',
            "postData": "param1=value1&param2=value2"
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge not detected!", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version)

        solution = body.solution
        self.assertIn(self.post_url, solution.url)
        self.assertEqual(solution.status, 200)
        self.assertIs(len(solution.headers), 0)
        self.assertIn("I hope you have a lovely day!", solution.response)
        self.assertEqual(len(solution.cookies), 0)
        self.assertIn("Chrome/", solution.userAgent)

        # check that we sent the post data
        res2 = self.app.post_json('/v1', {
            "cmd": "request.get",
            "url": self.post_url
        })
        self.assertEqual(res2.status_code, 200)

        body2 = V1ResponseBase(res2.json)
        self.assertEqual(STATUS_OK, body2.status)
        date_hour = datetime.now(timezone.utc).isoformat().split(':')[0].replace('T', ' ')
        self.assertIn(date_hour, body2.solution.response)

    def test_v1_endpoint_request_post_cloudflare(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.post",
            "url": self.cloudflare_url,
            "postData": "param1=value1&param2=value2"
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge solved!", body.message)
        self.assertGreater(body.startTimestamp, 10000)
        self.assertGreaterEqual(body.endTimestamp, body.startTimestamp)
        self.assertEqual(utils.get_flaresolverr_version(), body.version)

        solution = body.solution
        self.assertIn(self.cloudflare_url, solution.url)
        self.assertEqual(solution.status, 200)
        self.assertIs(len(solution.headers), 0)
        self.assertIn("<title>405 Not Allowed</title>", solution.response)
        self.assertGreater(len(solution.cookies), 0)
        self.assertIn("Chrome/", solution.userAgent)

        cf_cookie = _find_obj_by_key("name", "cf_clearance", solution.cookies)
        self.assertIsNotNone(cf_cookie, "Cloudflare cookie not found")
        self.assertGreater(len(cf_cookie["value"]), 30)

    def test_v1_endpoint_request_post_fail_no_post_data(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.post",
            "url": self.google_url
        }, status=500)
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_ERROR, body.status)
        self.assertIn("Request parameter 'postData' is mandatory in 'request.post' command", body.message)

    def test_v1_endpoint_request_post_deprecated_param(self):
        res = self.app.post_json('/v1', {
            "cmd": "request.post",
            "url": self.google_url,
            "postData": "param1=value1&param2=value2",
            "userAgent": "Test User-Agent"  # was removed in v2, not used
        })
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json)
        self.assertEqual(STATUS_OK, body.status)
        self.assertEqual("Challenge not detected!", body.message)

    # todo: test Cmd 'sessions.create' should return OK
    # todo: test Cmd 'sessions.create' should return OK with session
    # todo: test Cmd 'sessions.list' should return OK
    # todo: test Cmd 'sessions.destroy' should return OK
    # todo: test Cmd 'sessions.destroy' should fail
    # todo: test Cmd 'request.get' should use session


if __name__ == '__main__':
    unittest.main()
