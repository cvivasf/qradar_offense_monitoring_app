from email.mime.text import MIMEText
import smtplib
from app_config import offenses_notified_logger,failed_notifications_of_unescalated_offenses_retries_logger
from typing import Literal

def notify_via_email(config, offense, logger: Literal["offense_monitoring","retry_notifications"] = "offense_monitoring"):
    '''Sends en email to the SOC account using an automated Gmail account. The email will contain the offense information passed by parameter

    :param config ServerConfig: Configuration Object of the app, obtained from the app_config module
    :param offense: Offense object/dictionary obtained from the SIEM. The email data will be generated from the offense information
    :param logger: Logger to use to log the email errors or messages. By default will use the offenses_notified_logger from the app_config module
    :return: True if sent succesfully, False otherwise
    :rtype: bool
    '''

    logger = offenses_notified_logger
    if logger == "retry_notifications":
        logger = failed_notifications_of_unescalated_offenses_retries_logger

    recipients = ["recipient@mail.com"]
    body = f'''Hello, a QRADAR SIEM offense with monitored autoescalation and closure status has been detected to be still OPEN 15 minutes after the offense was created.
    This probably means the QRADAR SOAR plugin for QRADAR SIEM for automated escalations failed and the offense was probably not escalated to IBM SOAR and automatically closed. 
    Please, access QRADAR SIEM and check if it has been escalated. If it has not, please, manually escalate it. Also, check any IBM SOAR playbook which might have failed and not closed the offense automatically. 
    
    Offense Details:

        Offense ID: { str(offense.get("id","")) }
        Offense Description: { offense.get("description","") }

        Magnitude: { str(offense.get("magnitude","")) }
        Relevance: { str(offense.get("relevance","")) }
        Severity: { str(offense.get("severity","")) }
        Credibility: { str(offense.get("credibility","")) }

        Source network: { offense.get("source_network","") }


    Please, check and edit the Python QRADAR SIEM Offenses Monitoring script's config.ini file if you want to exclude this type of offense from being monitored. 
    
    Thank you,
    '''
    
    msg = MIMEText(body)
    msg['Subject'] = f"Detected a potential failure of SIEM offense autoescalation. [ {str( offense.get('id','') )} ] - { offense.get('description','') }"
    msg['From'] = config.email_sender
    msg['To'] = ', '.join(recipients)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(config.email_sender, config.email_pass)
            smtp_server.sendmail(config.email_sender, recipients, msg.as_string())
            smtp_server.quit()
            logger.info("Message succesfully sent!")
        return True
    except Exception as e:
        logger.error("Error sending email with offense information: " + str(type(e)) + " | Detail: " + str(e))
        return False