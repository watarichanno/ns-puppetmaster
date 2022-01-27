from unicodedata import name
import urllib.parse
import toml

import utils

CONFIG_PATH = 'config.toml'
NATION_SETTINGS_URL = "page=settings"


class AppError(Exception):
    """Application-specific exceptions.
    """


class NsSettingsUpdater:
    """Update the settings of a nation.

    Args:
        ns_form_sender (utils.NsFormSender): NS form sender object
    """

    def __init__(self, ns_form_sender: utils.NsFormSender) -> None:
        self.ns_form_sender = ns_form_sender
        self.oldemail = None

    def set_nation(self, nation_pin) -> None:
        form_params = self.ns_form_sender.create_session(nation_pin)
        self.oldemail = form_params['oldemail']

    def update_settings(self, settings: dict) -> None:
        form_params = settings
        form_params['oldemail'] = self.oldemail
        form_params['update'] = ' Update '
        self.ns_form_sender.send_form(form_params)


class NsPuppetUpdater:
    def __init__(self, ns_api: utils.NsApi, settings_updater: NsSettingsUpdater) -> None:
        self.ns_api = ns_api
        self.settings_updater = settings_updater
        self.nation_pin = None

    def login(self, nation_name, password) -> None:
        self.nation_pin = self.ns_api.login(nation_name, password)

    def update_settings(self, settings: dict) -> None:
        self.settings_updater.set_nation(self.nation_pin)
        self.settings_updater.update_settings(settings)


def get_puppet_names_from_file(file_path: str) -> list:
    """Get a list of puppet names from a text file.

    Args:
        file_path (str): Path to the file

    Returns:
        list: Puppet names
    """

    with open(file_path) as file:
        return file.readlines()


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
        settings = urllib.parse.parse_qs(group_config['settings'])
        update_settings = True

    for nation_name in get_puppet_names(group_config, group_name):
        password = group_config['password']
        puppet_updater.login(nation_name, password)
        print("Puppet {} logged in.".format(nation_name))
        if update_settings:
            puppet_updater.update_settings(settings)
            print("Puppet {}'s settings updated.".format(nation_name))


def update_puppets(puppet_groups: dict, puppet_updater: NsPuppetUpdater):
    for name, config in puppet_groups.items():
        update_puppet_group(config, name, puppet_updater)


def main():
    config = toml.load(CONFIG_PATH)
    general_conf = config['general']
    user_agent = general_conf['user_agent']
    ns_api = utils.NsApi(user_agent)
    ns_form_sender = utils.NsFormSender(user_agent, NATION_SETTINGS_URL)
    settings_updater = NsSettingsUpdater(ns_form_sender)
    puppet_updater = NsPuppetUpdater(ns_api, settings_updater)
    update_puppets(config['puppets'], puppet_updater)


if __name__ == '__main__':
    main()