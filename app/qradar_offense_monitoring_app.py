import threading
from qradar_siem_offenses_monitoring import main as notify_unescalated_offenses
from retry_notifying_failed_offenses import main as retry_uploading_failed_offenses_run
from app_config import server_config

def notify_of_unescalated_offenses_via_email(server_config):
    '''Calls the main method for the notifying of unescalated/open offenses via email, which runs in a separate thread.
    
    :param ServerConfig server_config: Configuration needed for the thread
    '''
    notify_unescalated_offenses(server_config)

def retry_notifying_failed_escalated_offenses(server_config):
    '''Calls the main method of the retry sending notifications for failed offenses that were not notified, which runs in a separate thread.
    
    :param ServerConfig server_config: Configuration needed for the thread
    '''
    retry_uploading_failed_offenses_run(server_config)

def main():
    '''Main method. Runs both threads (offenses and failed offenses) in daemon mode. '''
    t1 = threading.Thread(target=notify_of_unescalated_offenses_via_email, args=(server_config,), daemon=True)
    t2 = threading.Thread(target=retry_notifying_failed_escalated_offenses, args=(server_config,), daemon=True)

    t1.start()
    t2.start()
    
    # #List all threads currently running
    #print(threading.enumerate())

    try:
        while t1.is_alive() or t2.is_alive():
            t1.join(timeout=1)
            t2.join(timeout=1)
    except KeyboardInterrupt:
        print("Program interrupted! Exiting...")  

    # try:
    #     while t1.is_alive():
    #         t1.join(timeout=1)
    # except KeyboardInterrupt:
    #     print("Program interrupted! Exiting...")  

if __name__ == "__main__":
    main()