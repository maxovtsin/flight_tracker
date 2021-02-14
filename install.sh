#!/bin/bash

user_check() {
	if [ $(id -u) -ne 0 ]; then
		printf "Script must be run as root. Try 'sudo ./install.sh'\n"
		exit 1
	fi
}

success() {
	echo -e "$(tput setaf 2)$1$(tput sgr0)"
}

inform() {
	echo -e "$(tput setaf 6)$1$(tput sgr0)"
}

warning() {
	echo -e "$(tput setaf 1)$1$(tput sgr0)"
}

user_check

inform "Copying icons to /usr/share/flight_tracker...\n"
mkdir -p /usr/share/flight_tracker/resources
cp resources/* /usr/share/flight_tracker/resources

inform "Installing flight_tracker to /usr/bin/flight_tracker...\n"
cp flight_tracker.py /usr/bin/flight_tracker
chmod +x /usr/bin/flight_tracker

inform "Installing systemd service...\n"
cp flight_tracker.service /etc/systemd/system/
systemctl reenable flight_tracker.service
systemctl start flight_tracker.service

inform "\nTo see grow debug output, run: \"journalctl --no-pager --unit flight_tracker.service\"\n"
