import bs4
import requests
from requests import cookies
import toml

NATION_API_PING_URL = "https://www.nationstates.net/cgi-bin/api.cgi?nation={nation_name}&q=ping"
NATION_SETTINGS_PAGE_URL = "https://www.nationstates.net/page=settings"


def get_nation_pin(nation_name: str, password: str, user_agent: str) -> str:
    """Get pin code of a nation for private request authorization
    using NationStates API.

    Args:
        nation_name (str): Nation name
        password (str): Password
        user_agent (srt): User agent for API call.

    Returns:
        str: Pin code
    """

    headers = {'User-Agent': user_agent, 'X-Password': password}
    resp = requests.get(NATION_API_PING_URL.format(nation_name=nation_name), headers=headers)
    return resp.headers['X-Pin']


class NsSettingsChangeRequestService:
    """Make settings change requests to NationStates.

    Args:
        user_agent (str): User agent for requests
        nation_pin (str): Pin code for request authorization
    """

    def __init__(self, user_agent: str, nation_pin: str):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.session.cookies = cookies.cookiejar_from_dict({'pin': nation_pin})

        self.localid = self.get_localid()

    def get_localid(self):
        """Get localid value for POST requests to NS's settings page.
        """

        resp_html = self.session.get(NATION_SETTINGS_PAGE_URL).text
        soup = bs4.BeautifulSoup(resp_html, 'html.parser')
        return soup.find('input', attrs={'name': 'localid'})['value']

    def request(self, params: dict):
        params['localid'] = self.localid
        r = self.session.post(NATION_SETTINGS_PAGE_URL, data=params)
