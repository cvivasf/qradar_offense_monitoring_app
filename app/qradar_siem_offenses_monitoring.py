import requests
import time
import os
import json
from typing import Dict, List
from utils.email_notification import notify_via_email
from app_config import ServerConfig, offenses_notified_logger

qradar_headers = {'SEC': None, 'Accept': 'application/json'} #Headers for QRadar API. Paritally obtained from config.ini file
config: ServerConfig = None

def load_last_processed_id()-> int:
    """Load the last notified offense ID from a file.
    
    :return: ID of the last notified offense ID.
    :rtype: int
    :raises OSError,FileNotFoundError,ValueError: if an error occurs when opening/reading the file
    """
    if os.path.exists(config.last_notified_offense_file):
        with open(config.last_notified_offense_file, 'r') as file:
            return int(file.read().strip())
    return None

def save_last_processed_id(offense_id:int) -> None:
    """Save the last processed offense ID to a file and updates the script variable
    
    :param int offense_id: The ID of the offense to write on the file as the latest offense processed.
    :return: Nothing.
    :rtype: None
    :raises OSError,FileNotFoundError,ValueError: if an error occurs when opening/writing the file"""
    with open(config.last_notified_offense_file, 'w') as file:
        file.write(str(offense_id))
    global last_processed_id
    last_processed_id = offense_id

def save_failed_offense_notification(offense_id_that_failed:int) -> None:
    """Appends a numeric offense ID to the failed notified offenses file, separated by commas.

    :param int offense_id_that_failed: The ID of the offense to write on the Failed Offenses file as the latest offense that failed to be notified.
    :return: Nothing.
    :rtype: None
    :raises OSError,FileNotFoundError,ValueError: if an error occurs when opening/writing the file"""
    with open(config.failed_notifications_file, 'a') as file:
        if file.tell() > 0:  # Check if the file is not empty
            file.write(',')
        file.write(str(offense_id_that_failed))

def current_milli_time_minus_15_mins():
    return round(time.time() * 1000 - 900000)

def get_latest_offenses() -> List[Dict[any,any]]:
    """Retrieve the latest offense from QRadar. Filtering by status as OPEN, 
    the ID being bigger than the offset ID of the last processed ID from QRADAR, and filtering by start_time in ascendant mode to get the latest one.
    
    :return: JSON response of the offenses obtained.
    :rtype: Dict[any,any]
    :raises HttpError: if an error occurred making the HTTP request"""
    params = { "filter": 'status=OPEN and id > ' + str(last_processed_id) + "and start_time <= " + str(current_milli_time_minus_15_mins()), "sort": "+start_time" }
    global qradar_headers
    qradar_headers = qradar_headers.copy()
    qradar_headers["RANGE"] = "items=0-100"
    qradar_headers["VERSION"] = "20.0"
    response = requests.get(config.qradar_url, headers=qradar_headers, verify=False, params=params)
    response.raise_for_status()
    return response.json()

def process_offenses():
    """Process the next 100 unescalated offenses and notify via Email."""
    global last_processed_id
    last_processed_id = load_last_processed_id()
    if not last_processed_id:
        raise Exception("ERROR! Provide a minimum Offense ID on the Offense ID index File!")
    
    offenses_notified_logger.info("Last processed Offense ID stored on memory file: " + str(last_processed_id) + " . Getting offense from QRADAR SIEM...")
    latest_offenses = get_latest_offenses()
    offenses_notified_logger.info("Call succesfully made to QRADAR SIEM...")
    
    #Filter out offenses that only contain any of the titles specified in the config.ini's OffensesToNotify.offense_names_to_check array variable that holds the monitored offense descriptions.
    filtered_offenses = [item for item in latest_offenses if item['description'] in config.offense_names_to_evaluate]
    #filtered_offenses = latest_offenses

    offenses_notified_logger.debug(json.dumps(latest_offenses))
    offenses_notified_logger.debug("Unclosed / Unescalated Offense to process and notify via email: " + json.dumps(filtered_offenses))
    
    if (not filtered_offenses or len(filtered_offenses) == 0):
        offenses_notified_logger.info("No offenses obtained from QRADAR SIEM.")
    else:
        #For each offense obtained, notify via email and update the file containing the last processed ID.
        for offense in filtered_offenses:
            offense_id = offense.get('id', None)
            if last_processed_id is not None and offense_id > last_processed_id:
                offenses_notified_logger.info(f"Processing offense with ID. About to notify for unescalated / unclosed offense via email!: {offense_id}")
                try:
                    sent_succesful = notify_via_email(config, offense, "offense_monitoring")
                    if sent_succesful:
                        save_last_processed_id(offense_id)
                    else:
                        raise Exception("Error sending notification email for the offense. Check previous/following logs for more info.")
                except Exception as e:
                    offenses_notified_logger.error(f"Exception notifying via email for offense with ID: {str(offense_id)}: {str(e)}")
                    save_failed_offense_notification(offense_id) #store the failed offense  in a file to be renotified
            else:
                offenses_notified_logger.error(f"Offense {offense_id} has already been processed. Please, increase the Offense ID offset on the file to start scanning new offenses!.")
        
def init_vars(passedconfig: ServerConfig):
    '''
    Initializates variables for the script

    :param int passedconfig: Configuration received from the config.ini file
    :return: None
    :rtype: None
    '''
    global config
    config = passedconfig
    global qradar_headers
    qradar_headers = {'SEC': config.qradar_api_key, 'Accept': 'application/json'}

def main(passedconfig: ServerConfig):
    
    init_vars(passedconfig)
    """Main loop to continuously check for new offenses and process them."""
    while True:
        try:
            process_offenses()
        except Exception as e:
            offenses_notified_logger.error(f"Error pulling and/or notifying for unescalated offenses from QRADAR SIEM Offenses obtention: {str(e)}")
        time.sleep(config.polling_rate_unescalated_offenses_checking)

if __name__ == "__main__":
    main()