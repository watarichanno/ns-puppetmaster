import bs4
from requests import cookies
import requests
import toml
import time


CONFIG_PATH = 'config.toml'
NATION_SETTINGS_URL = "page=settings"
NS_URL = 'https://www.nationstates.net/{form_url}'
NATION_API_PING_URL = "https://www.nationstates.net/cgi-bin/api.cgi?nation={nation_name}&q=ping"
SETTINGS_UPDATE_SLEEP_TIME = 6


class AppError(Exception):
    """Application-specific exceptions.
    """


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


class NsSettingsUpdater:
    """Send HTML forms to NationStates.

    Args:
        form_url (str): Relative URL of the form to send
        user_agent (str): User agent
    """

    def __init__(self, user_agent: str, form_url: str) -> None:
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.current_params = None
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

        soup = bs4.BeautifulSoup(html, 'html.parser')
        input_tags = soup.find('form', attrs={"name": 'form'}).find_all('input')
        return {tag['name']: tag['value'] for tag in input_tags if tag.has_attr('value')}

    def create_session(self, nation_pin: str) -> None:
        """Create a new session authorized by a nation's pin
        and get current parameters of the form.

        Args:
            nation_pin (str): Nation's pin
        """

        self.session.cookies = cookies.cookiejar_from_dict({'pin': nation_pin})
        resp = self.session.get(self.form_url)
        self.current_params = NsSettingsUpdater.get_form_params_from_html(resp.text)

    def refresh_session(self, resp: requests.Response) -> None:
        """Refresh the current session.

        Args:
            resp (requests.Response): Response object
        """

        self.current_params = NsSettingsUpdater.get_form_params_from_html(resp.text)

    def update_settings(self, params: dict) -> None:
        """Send form data.

        Args:
            params (dict): Form parameters
        """

        params = {**self.current_params, **params}
        resp = self.session.post(self.form_url, data=params)
        self.refresh_session(resp)
        time.sleep(SETTINGS_UPDATE_SLEEP_TIME)


class NsPuppetUpdater:
    def __init__(self, ns_api: NsApi, settings_updater: NsSettingsUpdater) -> None:
        self.ns_api = ns_api
        self.settings_updater = settings_updater
        self.nation_pin = None

    def login(self, nation_name, password) -> None:
        self.nation_pin = self.ns_api.login(nation_name, password)

    def update_settings(self, settings: dict) -> None:
        self.settings_updater.create_session(self.nation_pin)
        self.settings_updater.update_settings(settings)


def get_puppet_names_from_file(file_path: str) -> list:
    """Get a list of puppet names from a text file.

    Args:
        file_path (str): Path to the file

    Returns:
        list: Puppet names
    """

    with open(file_path) as file:
        return file.read().splitlines()


def get_puppet_names(group_config: dict, group_name: str) -> list:
    """Get a list of puppet names.

    Args:
        group_config (dict): Puppet group config
        group_name (dict): Group name

    Returns:
        list: Puppet names
    """

    if 'nation_names_from_file' in group_config:
        return get_puppet_names_from_file(group_config['nation_names_from_file'])

    if 'nation_names' in group_config:
        return group_config['nation_names']

    raise AppError("Puppet group {} does not have nation names".format(group_name))


def update_puppet_group(group_config: dict, group_name: str, puppet_updater: NsPuppetUpdater):
    """Update a puppet group.

    Args:
        puppet_config (dict): Group config
        puppet_name (str): Group name
        puppet_updater (NsPuppetUpdater): NS puppet updater object
    """

    update_settings = False
    if 'settings' in group_config:
        update_settings = True

    for nation_name in get_puppet_names(group_config, group_name):
        password = group_config['password']
        puppet_updater.login(nation_name, password)
        print("Puppet {} logged in.".format(nation_name))
        if update_settings:
            puppet_updater.update_settings(group_config['settings'])
            print("Puppet {}'s settings updated.".format(nation_name))


def update_puppets(puppet_groups: dict, puppet_updater: NsPuppetUpdater):
    for name, config in puppet_groups.items():
        update_puppet_group(config, name, puppet_updater)


def main():
    config = toml.load(CONFIG_PATH)
    general_conf = config['general']
    user_agent = general_conf['user_agent']
    ns_api = NsApi(user_agent)
    settings_updater = NsSettingsUpdater(user_agent, NATION_SETTINGS_URL)
    puppet_updater = NsPuppetUpdater(ns_api, settings_updater)
    update_puppets(config['puppets'], puppet_updater)


if __name__ == '__main__':
    main()