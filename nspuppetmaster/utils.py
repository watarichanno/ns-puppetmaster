"""Contains helpful classes and functions for API access, sending HTML forms,...
"""

import bs4
from requests import cookies
import requests


NATION_API_PING_URL = "https://www.nationstates.net/cgi-bin/api.cgi?nation={nation_name}&q=ping"
NS_URL = 'https://www.nationstates.net/{form_url}'


class NsApi:
    """NationStates API access.

    Args:
        user_agent (str): User agent
    """

    def __init__(self, user_agent) -> None:
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})

    def login(self, nation_name, password):
        """Login a nation and get pin code for future private requests.

        Args:
            nation_name (str): Nation's name
            password (str): Nation's password

        Returns:
            str: Pin code
        """

        resp = self.session.get(NATION_API_PING_URL.format(nation_name=nation_name),
                                headers={'X-Password': password})
        return resp.headers['X-Pin']


class NsFormSender:
    """Send HTML forms to NationStates.

    Args:
        form_url (str): Relative URL of the form to send
        user_agent (str): User agent
    """

    def __init__(self, user_agent: str, form_url: str) -> None:
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.localid = None
        self.set_form_url(form_url)

    def set_form_url(self, relative_url: str) -> None:
        """Set URL of the form to send.
        The URL is relative to NationStates domain name.

        Args:
            relative_url (str): Relative URL
        """

        self.form_url = NS_URL.format(form_url=relative_url)

    @staticmethod
    def get_form_params_from_html(html: str) -> dict:
        """Get a dict of form parameters from HTML text.

        Args:
            html (str): HTML text

        Returns:
            dict: Form parameters
        """

        form_params = {}
        soup = bs4.BeautifulSoup(html, 'html.parser')
        input_tags = soup.find_all('input')
        return {tag['name']: tag['value'] for tag in input_tags if tag.has_attr('value')}

    def get_current_form_params(self) -> None:
        """Get current parameters of the form.
        """

        resp = self.session.get(self.form_url)
        form_params = NsFormSender.get_form_params_from_html(resp.text)
        return form_params

    def create_session(self, nation_pin: str) -> dict:
        """Create a new session authorized by a nation's pin
        and get current parameters of the form.

        Args:
            nation_pin (str): Nation's pin

        Returns:
            dict: Form parameters
        """

        self.session.cookies = cookies.cookiejar_from_dict({'pin': nation_pin})
        form_params = self.get_current_form_params()
        self.localid = form_params['localid']
        return form_params

    def refresh_session(self, resp: requests.Response) -> None:
        """Refresh the current session.

        Args:
            resp (requests.Response): Response object
        """

        form_params = NsFormSender.get_form_params_from_html(resp.text)
        self.localid = form_params['localid']

    def send_form(self, params: dict) -> None:
        """Send form data.

        Args:
            params (dict): Form parameters
        """

        params['localid'] = self.localid
        resp = self.session.post(self.form_url, data=params)
        self.refresh_session(resp)
