import configparser
import logging
from logging.handlers import RotatingFileHandler
import json
from typing import List

class ServerConfig:
    '''Class for app configuration. Contains main configuration variables that are used for the app.'''
    def __init__(self):
        self.qradar_url:str = None
        self.qradar_api_key:str = None
        self.last_notified_offense_file:str = None
        self.failed_notifications_file:str = None
        self.logging_level:str = None
        self.cli_logging_enabled:bool = None
        self.polling_rate_unescalated_offenses_checking:int = None
        self.polling_rate_offenses_failure_resending:int = None
        self.offense_names_to_evaluate = []
        self.email_sender = None
        self.email_pass = None

def get_logging_level(level:str):
    '''Maps the logging level string to a corresponding logging level integer valule. If an invalid one is passed, will default to INFO.

    Accepted levels:

    - DEBUG/debug: 10
    - INFO/info:  20
    - WARNING/warning: 30
    - ERROR/error: 40
    - CRITICAL/critical: 50
    
    :param: str level: Level of logging to set based on the level received as an string.
    :return: Level of the logging to be used on the files.
    :rtype: int 
    '''
    
    if level is None:
        level = ''
    else:
        level = level.strip().upper()

    log_level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    # Set the logging level for the app logger based on the config value
    if level in log_level_mapping:
        return log_level_mapping[level]
    else:
        print(f"An invalid logging level has been retrieved from the config.ini file. Using default level INFO.")
        return logging.INFO

def init_server_config():
    '''Initializes ServerConfig object to be used by app modules by using the config.ini file and the configparser module.
    
    :return: ServerConfig object with the configuration for the app
    :rtype: ServerConfig'''
    #Read the configuration file
    print('[QRadarOpenUnEscalatedOffenseMonitoring] Building App configparser...')
    config = configparser.ConfigParser()
    print('[QRadarOpenUnEscalatedOffenseMonitoring] Reading config.ini file...')
    config.read('config.ini')
    print('[QRadarOpenUnEscalatedOffenseMonitoring] Config.ini file read succesfully!...')

    # Create an instance of server_config
    server_config = ServerConfig()

    # Retrieve the variables and assign them to server_config
    server_config.qradar_url = config.get('MainConfig', 'qradar_url')
    server_config.qradar_api_key = config.get('MainConfig', 'qradar_api_key')
    server_config.last_notified_offense_file = config.get('MainConfig', 'last_notified_offense_file')
    server_config.failed_notifications_file = config.get('MainConfig', 'failed_notifications_file')
    server_config.email_sender = config.get("MainConfig","email_user")
    server_config.email_pass = config.get("MainConfig","email_pass")


    config_level = config.get('Logging','logging_level')
    server_config.logging_level = get_logging_level(config_level)
    # Get the 'enabled CLI logging' value from the config, defaulting to 'True'
    enabled_value = config.get('Logging', 'cli_logging_enabled', fallback='True')
    
    # Convert the value to a boolean
    try:
        cli_logs_enabled = (enabled_value is not None and enabled_value.lower() == 'true')
    except ValueError as e:
        print(e)
        # Handle invalid boolean values
        cli_logs_enabled = True  # Default to True if the value is invalid

    server_config.cli_logging_enabled = cli_logs_enabled

    try:
        server_config.polling_rate_unescalated_offenses_checking = config.getint("OffensesPollingRate",'polling_rate_non_escalated_offenses_checking')
        if (server_config.polling_rate_unescalated_offenses_checking is None or server_config.polling_rate_unescalated_offenses_checking < 1):
            print(f"[QRadarOpenUnEscalatedOffenseMonitoring] WARNING Open/UnEscalated offenses polling time in seconds is misconfigured. Should be an integer value bigger or equal than 1. Defaulting to 5 (seconds)")
            server_config.polling_rate_unescalated_offenses_checking = 5
    except:
        print(f"[QRadarOpenUnEscalatedOffenseMonitoring] WARNING Open/UnEscalated offenses polling time in seconds is misconfigured. Should be an integer value from 5 to 3600. Defaulting to 15 (seconds)")
        server_config.polling_rate_unescalated_offenses_checking = 5

    try:
        server_config.polling_rate_offenses_failure_resending = config.getint("OffensesPollingRate",'polling_rate_trying_to_resend_offenses_notifications')
        if (server_config.polling_rate_offenses_failure_resending is None or server_config.polling_rate_offenses_failure_resending < 1):
            print(f"[QRadarOpenUnEscalatedOffenseMonitoring] WARNING Renotifying failed offenses polling time in seconds is misconfigured. Should be an integer value bigger or equal than 1. Defaulting to 10 (seconds)")
            server_config.polling_rate_offenses_failure_resending = 120
    except:
        print(f"[QRadarOpenUnEscalatedOffenseMonitoring]  WARNING Renotifying failed offenses time in seconds is misconfigured. Should be an integer value from 5 to 3600. Defaulting to 120 (seconds)")
        server_config.polling_rate_offenses_failure_resending = 120

    offenses_names_to_check: List[str] = json.loads(config.get("OffensesToNotify","offense_names_to_check"))

    if isinstance(offenses_names_to_check, List) == False or len(offenses_names_to_check) == 0:
        raise Exception("Please, pass a valid list of offense names to search for notifying them of being unescalated or unclosed")
    else:
        server_config.offense_names_to_evaluate = offenses_names_to_check


    return server_config

server_config = init_server_config()

########################################LOGGERS CONFIGURATION!!!!!##################################################

def get_formatter_for_logger(formatter_identifier:str = None):
    '''Generates a formatter for a handler inside a logger. Pass a formatter identifier to identify the handler in a unique way
    
    :param str formatter_identifier: Identifier to add at the start of the formatted log
    :return: Formatter to be used when generating logs in the file
    :rtype: Formatter
    '''
    if formatter_identifier:
        formatter = logging.Formatter(formatter_identifier  + ' %(asctime)s %(levelname)s: %(message)s [in %(funcName)s():%(lineno)d] [%(filename)s]')
    else:
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    return formatter

def configure_logger(logger_to_config:logging.Logger, handler_formatter_identifier:str,log_file_name:str):
    '''
    Configures a logger. Pass a Logger Instance, an identifier to use on the handler formatter and the file name where to store the logs.
    
    :param  Logger logger_to_config: Logger to configure.
    :param str handler_formatter_identifier:  Handler formatter identifier to add in the logger configured. get_formatter_for_logger(formatter) is called to configure the format of the logs for the affected logger.
    :param str log_file_name: Log file to use to store the logs for the configured logger.
    :return: None
    :rtype: None
    '''
    handler_formatter = get_formatter_for_logger(handler_formatter_identifier)
    #By default files will have a max of 15MB and rotate when reached. 3 historical rotated files will be stored.
    handler = RotatingFileHandler('logs/' + log_file_name, maxBytes=15728640, backupCount=3)
    handler.setLevel(server_config.logging_level)
    handler.setFormatter(handler_formatter)
    logger_to_config.addHandler(handler)

    if (server_config.cli_logging_enabled == True):
        print("Logging seems to be enabled...")
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(server_config.logging_level)
        stream_handler.setFormatter(handler_formatter)
        logger_to_config.addHandler(stream_handler)
    else:
        print("You seem to have disabled CLI logging. Most logs will no longer appear on the CLI. Check log files for log information.")
    #Test handler
    logger_to_config.debug(f'{handler_formatter_identifier} is properly configured and working.')

# Defined loggers for different server processes
app_bootstrap_logger = logging.getLogger("app_bootstraping")
offenses_notified_logger = logging.getLogger("offenses_notified_logger")
failed_notifications_of_unescalated_offenses_retries_logger = logging.getLogger("failed_notifications_of_unescalated_offenses_retries_logger")
logging.getLogger().setLevel(server_config.logging_level)
configure_logger(app_bootstrap_logger, '[app_bootstrap_logger]','app_bootstrap.log')
configure_logger(offenses_notified_logger, '[offenses_notified_logger]','offenses_notified.log')
configure_logger(failed_notifications_of_unescalated_offenses_retries_logger, '[failed_notifications_of_unescalated_offenses_retries_logger]','failed_offenses_to_notify.log')

###FINAL MESSAGE:
app_bootstrap_logger.critical(f'''
QRADAR SOAR Plugin Offense Escalation Failures Monitoring                                                                                                                                                                                                                                                             
Developed by cvivasf
''')
app_bootstrap_logger.critical(f"#######################################################################")
app_bootstrap_logger.critical('[QRadarOpenUnEscalatedOffenseMonitoring] Configuration of QRADAR Open/Unescalated offense monitoring:')
app_bootstrap_logger.critical(f"    Current LOG LEVEL: {server_config.logging_level}")
app_bootstrap_logger.critical(f"    CLI Logging enabled?: {server_config.cli_logging_enabled}")
app_bootstrap_logger.critical(f"    QRADAR URL: {server_config.qradar_url}")
app_bootstrap_logger.critical(f"    Last Notified Offense ID file location: {server_config.last_notified_offense_file}")
app_bootstrap_logger.critical(f"    Failed Escalated Offense notification IDs file location: {server_config.failed_notifications_file}")
app_bootstrap_logger.critical(f"    Time to wait for polling new offenses from QRADAR and notifing them via email: {server_config.polling_rate_unescalated_offenses_checking}")
app_bootstrap_logger.critical(f"    Time to wait for sending new failed to notify offenses from QRADAR via Email: {server_config.polling_rate_offenses_failure_resending}")
app_bootstrap_logger.critical(f"    Unescalated/Open offenses names being monitored: {str(server_config.offense_names_to_evaluate)}")
app_bootstrap_logger.critical(f"Notifying unescalated/open offenses via email Now!...")
app_bootstrap_logger.critical(f"#######################################################################")