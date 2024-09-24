import requests
import time
import os
import json
from typing import Dict
from utils.email_notification import notify_via_email
from app_config import ServerConfig, failed_notifications_of_unescalated_offenses_retries_logger

qradar_headers = {'SEC': None, 'Accept': 'application/json'} #Headers for QRadar API. Paritally obtained from config.ini file
failed_offenses_ids_list = [] #do not edit! Used to temporary store in memory the failed offenses IDs obtained from the file
config: ServerConfig = None

def load_failed_ids_from_file() -> str:
    """Load the ids of the failed offenses from the failed offenses file.
    
    :return: A string of the content in the file
    :rtype: Str
    :raises OSError,FileNotFoundError,ValueError: if an error occurs when opening/reading the file
    """
    if os.path.exists(config.failed_notifications_file):
        with open(config.failed_notifications_file, 'r') as file:
            return (file.read().strip())
    return None

def remove_offense_id_from_failed_offenses_file(offense_id:int) -> None:
    """Remove the offense Id from the failed offense file and from memory and rewrites the file with the failed missing offenses (if any)
    
    :param int offense_id: The ID of the offense to remove from the file and memory.
    :return: Nothing
    :rtype: None
    :raises OSError,FileNotFoundError,ValueError: if an error occurs when opening/editing the file
    """
    global failed_offenses_ids_list

    try:
        failed_offenses_ids_list.remove(offense_id)
    except:
        failed_notifications_of_unescalated_offenses_retries_logger.warning("Error removing failed offense ID from file. The offense ID did not exist on the file. Was the file manipulated by a user?.")
    
    failed_offenses_ids_as_string = [str(id) for id in failed_offenses_ids_list]
    comma_separated_string_of_failed_offense_ids = ",".join(failed_offenses_ids_as_string)

    with open(config.failed_notifications_file, 'w') as file:
        if comma_separated_string_of_failed_offense_ids:
            file.write(comma_separated_string_of_failed_offense_ids)
        else:
            file.write("")

    failed_notifications_of_unescalated_offenses_retries_logger.info(f"Deleted succcesfully offense ID from the failed offenses file with ID {str(offense_id)}")

def get_offense(offense_id: int)-> Dict[any,any]: 
    """Retrieve an offense from QRADAR.

    :param int offense_id: The ID of the offense to get it's data from QRADAR.
    :return: The json response from obtaining the offense.
    :rtype: Dict[any,any]
    :raises HttpError: if an error occurs obtaining the offense info
    """
    global qradar_headers
    qradar_headers = qradar_headers.copy()
    qradar_headers["VERSION"] = "20.0"
    response = requests.get(config.qradar_url + "/" + str(offense_id), headers=qradar_headers, verify=False)
    response.raise_for_status()
    return response.json()

def process_offense(offense_id: int) -> None:
    """Process the next unprocessed offense and sends an email notification for it.

    :param int offense_id: Receives the Offense ID of the offense to notify via email
    :return: None
    :rtype: None
    """
    failed_notifications_of_unescalated_offenses_retries_logger.info("Processing and sending notifications emails for failed-to-notify offense_id via email with ID: " + str(offense_id))
    latest_offense = get_offense(offense_id)
    failed_notifications_of_unescalated_offenses_retries_logger.debug("Offense obtained from QRADAR SIEM: " + json.dumps(latest_offense))

    if latest_offense and latest_offense.get("status", None) == "OPEN":
        offense_id = latest_offense.get('id',None)
        failed_notifications_of_unescalated_offenses_retries_logger.info(f"Processing offense with ID. About to send fallback email reminding offense is still open!: {str(offense_id)}")
        try:
            sent_succesful = notify_via_email(config,latest_offense,"retry_notifications")
            if sent_succesful:
                failed_notifications_of_unescalated_offenses_retries_logger.info(f"Sent fallback email succesfully for for offense with ID: " + str(offense_id) + " . Proceeding to delete the ID of the offense from the failed offenses file.")
                remove_offense_id_from_failed_offenses_file(offense_id)
            else:
                raise Exception("Error sending notification email for the offense. Check logs for more info.")
        except Exception as e:
            failed_notifications_of_unescalated_offenses_retries_logger.error(f"Error sending fallback notification email for offense with id {offense_id} . Error: {str(e)}" )
    else:
        failed_notifications_of_unescalated_offenses_retries_logger.warning(f"Offense {offense_id} is closed or non-existent in QRADAR. Removing the offense ID from the file.")
        remove_offense_id_from_failed_offenses_file(offense_id)

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

def safe_convert_offense_id(id_str):
    try:
        return int(id_str)
    except ValueError:
        return None

def main(passedconfig: ServerConfig):
    
    init_vars(passedconfig)

    """Main loop to continuously check for open offenses (and supposely unescalated offenses) and try renotifying them via email."""
    while True:

        ids_as_string = load_failed_ids_from_file().split(",")
        missing_failed_offenses_mssg = "No failed offense IDs to retry notifying were found on the Failed Offense Notifications File."
        if (ids_as_string and len(ids_as_string) > 0):
            global failed_offenses_ids_list
            # Use a set to avoid duplicates
            failed_offenses_ids_set = {
                safe_convert_offense_id(id_str) for id_str in ids_as_string if id_str.strip() != ""
            }
            # Filter out None values and convert back to a list
            failed_offenses_ids_list = [id for id in failed_offenses_ids_set if id is not None]
            if (len(failed_offenses_ids_list) > 0):
                for id in failed_offenses_ids_list:
                    try:
                        process_offense(id)
                    except Exception as e:
                        failed_notifications_of_unescalated_offenses_retries_logger.error(f"Error pulling and/or sending previously failed offense to be notified with ID: {e}. Advancing to next offense.")
            else:
                failed_notifications_of_unescalated_offenses_retries_logger.error(missing_failed_offenses_mssg)
        else:
            failed_notifications_of_unescalated_offenses_retries_logger.error(missing_failed_offenses_mssg)
        time.sleep(config.polling_rate_offenses_failure_resending)

if __name__ == "__main__":
    main()