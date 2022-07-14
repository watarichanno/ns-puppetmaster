"""A script to update settings of many NationStates puppet nations.
"""

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


class NsFormUpdater:
    """Update HTML forms on NationStates with new values.

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
        form_params = {}
        for tag in input_tags:
            # <input> tags with type="checkbox" only add POST parameter when they are checked.
            # We need to only include their POST value if they are checked.
            if tag.get('type') == 'checkbox':
                if tag.has_attr('checked'):
                    form_params[tag['name']] = tag.get('value', 'yes')
            elif tag.has_attr('value'):
                form_params[tag['name']] = tag['value']
        return form_params

    def create_session(self, nation_pin: str) -> None:
        """Create a new session authorized by a nation's pin
        and get current parameters of the form.

        Args:
            nation_pin (str): Nation's pin
        """

        self.session.cookies = cookies.cookiejar_from_dict({'pin': nation_pin})
        resp = self.session.get(self.form_url)
        self.current_params = NsFormUpdater.get_form_params_from_html(resp.text)

    def update_form(self, new_params: dict) -> None:
        """Send form data.

        Args:
            new_params (dict): New form values
        """

        post_params = {**self.current_params, **new_params}
        # Boolean false value means the user wants to remove the corresponding parameter.
        post_params = dict(filter(lambda value : value != False, post_params.items()))
        self.session.post(self.form_url, data=post_params)
        time.sleep(SETTINGS_UPDATE_SLEEP_TIME)


class NsPuppetUpdater:
    """Update a puppet's settings.
    """

    def __init__(self, ns_api: NsApi, form_updater: NsFormUpdater) -> None:
        """Update settings of a puppet.

        Args:
            ns_api (NsApi): NationStates API wrapper
            form_updater (NsFormUpdater): NS form updater
        """

        self.ns_api = ns_api
        self.form_updater = form_updater
        self.nation_pin = None

    def login(self, nation_name: str, password: str) -> None:
        """Log in to a puppet.

        Args:
            nation_name (str): Nation name
            password (str): Password
        """

        self.nation_pin = self.ns_api.login(nation_name, password)

    def update_settings(self, settings: dict) -> None:
        """Update a puppet's settings

        Args:
            settings (dict): New settings values
        """

        self.form_updater.create_session(self.nation_pin)
        self.form_updater.update_form(settings)


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

    if 'nation_name_file' in group_config:
        return get_puppet_names_from_file(group_config['nation_name_file'])

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
    if 'new_settings' in group_config:
        update_settings = True

    for nation_name in get_puppet_names(group_config, group_name):
        password = group_config['password']
        puppet_updater.login(nation_name, password)
        print("Puppet {} logged in.".format(nation_name))
        if update_settings:
            puppet_updater.update_settings(group_config['new_settings'])
            print("Puppet {}'s settings updated.".format(nation_name))


def update_puppet_groups(puppet_groups: dict, puppet_updater: NsPuppetUpdater):
    """Update provided puppet groups.

    Args:
        puppet_groups (dict): Configurations of puppet groups
        puppet_updater (NsPuppetUpdater): Puppet updater
    """

    for name, config in puppet_groups.items():
        update_puppet_group(config, name, puppet_updater)


def main():
    config = toml.load(CONFIG_PATH)
    general_config = config['general']
    user_agent = general_config['user_agent']

    ns_api = NsApi(user_agent)
    form_updater = NsFormUpdater(user_agent, NATION_SETTINGS_URL)
    puppet_updater = NsPuppetUpdater(ns_api, form_updater)

    update_puppet_groups(config['puppets'], puppet_updater)


if __name__ == '__main__':
    main()