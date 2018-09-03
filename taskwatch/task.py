#!/usr/bin/env python

import smtplib
import yaml
import os
import subprocess
import argparse
import socket
from email.mime.text import MIMEText

CONFIG = None


def get_config():
    global CONFIG
    if CONFIG is not None:
        return CONFIG

    home = os.environ["HOME"]
    config = os.path.join(home, ".tasks.config")
    with open(config, 'r') as stream:
        try:
            CONFIG = yaml.load(stream)
            return CONFIG
        except yaml.YAMLError as error:
            print("config loading error: {}".format(error))
            return None


def send_email(subject, body):
    config = get_config()
    if not config:
        return

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject 
        msg["From"] = config["from"]
        msg["To"] = config["to"]
        client = smtplib.SMTP(config["smtp"]["host"], config["smtp"]["port"])
        client.ehlo()
        if config["smtp"]["port"] == 587:
            client.starttls()
            client.ehlo()
        if config["smtp"].get("login") and config["smtp"].get("password"):
            client.login(config["smtp"]["login"], config["smtp"]["password"])
        client.send_message(msg)
        client.quit()
    except Exception as error:
        print("sending email failed: {}".format(error))
    

def main():
    parser = argparse.ArgumentParser(description="Long task watcher")
    parser.add_argument("-n", "--name", help="Task name for subject")
    parser.add_argument("-o", "--send-output", help="Send output via email", action="store_true")
    parser.add_argument("cmd", help="Command for run", nargs=1)
    parser.add_argument("argument", help="Argument for command", nargs="*")
    args, unknown = parser.parse_known_args()
    retcode = None
    output = None
    for_run = args.cmd + args.argument + unknown
    try:
        if not args.send_output:
            subprocess.check_call(for_run, shell=False)
            retcode = 0
        else:
            output = subprocess.check_output(for_run, shell=False, encoding="utf-8")
            retcode = 0
    except subprocess.CalledProcessError as error:
        retcode = error.returncode
        if args.send_output:
            output = error.output
    
    hostname = socket.gethostname()
    title = args.name and args.name or ' '.join(for_run)
    status = retcode == 0 and "SUCCESS" or "FAIL"
    subject = "[{2}] Command '{0}' has finished with {1}".format(title, status, hostname)
    body = "command '{0}' return {1}\n".format(' '.join(for_run), retcode)
    if args.send_output and output:
        body += output

    send_email(subject, body)

    if output:
        print(output)
    

if __name__ == '__main__':
    main()