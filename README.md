### QRADAR Offense Escalation Monitoring Script

This script simply checks for offenses that have been opened for more than 15 minutes and sends en EMAIL notification via SMTP. This is mainly used to monitored offenses that should be automatically closed from other systems like SOARS or ITSMS after a proper cyber-reponse playbook has run.

Please, configure the recipients of the email on the utils/email_notification.py module and set the needed credentials on the config.ini file for this to work.

Python 3.11> required