"""
  Script: nmap_oui_update.py

  Author: Travis Phillips

  Date: 06/08/2022

  Purpose: This script is used to update the MAC address OUI file for
           NMAP.  This file is what helps tie MAC Addresses to vendors
           and having this file current can help determine what a device
           is.  This script will download the latest information from
           the IEEE website and parse it into a format useable by NMAP
           and place it into the /usr/share/nmap/ directory while keeping
           a backup of the original file
"""
import sys
import os
import shutil
import re
import datetime
import requests

##############################################
#                CONSTANTS
##############################################
IEEE_URL = "https://standards-oui.ieee.org/"
NMAP_OUI = "/usr/share/nmap/nmap-mac-prefixes"
OUI_DATA = "ieee_oui_data.txt"
RED = "\033[31;1m"
GRN = "\033[32;1m"
YLW = "\033[33;1m"
BLU = "\033[34;1m"
NC = "\033[m"
BANNER = r"""
       _____ ______________  ______  ______
      / ___// ____/ ____/ / / / __ \/ ____/
      \__ \/ __/ / /   / / / / /_/ / __/
     ___/ / /___/ /___/ /_/ / _, _/ /___
    /____/_____/\____/\____/_/ |_/_____/

        ________  __________  _____
       /  _/ __ \/ ____/   | / ___/
       / // / / / __/ / /| | \__ \
     _/ // /_/ / /___/ ___ |___/ /
    /___/_____/_____/_/  |_/____/
"""
SCRIPT = "\n  ---===[ NMAP OUI UPDATE SCRIPT V1.0 ]===---\n"

##############################################
#             PRINT FUNCTIONS
##############################################
def print_info(msg: str, endline="\n") -> None:
    """ Prints a formatted error message. """
    sys.stdout.write(f" [{BLU}*{NC}] {msg}{endline}")

def print_success(msg: str) -> None:
    """ Prints a formatted error message. """
    print(f" [{GRN}+{NC}] {GRN}{msg}{NC}")

def print_error(msg: str) -> None:
    """ Prints a formatted error message. """
    print(f" [{RED}-{NC}] {RED}ERROR:{NC} {msg}")

##############################################
#            SUPPORT FUNCTIONS
##############################################
def is_root() -> bool:
    """ Sanity check: Ensure user is root. """
    return os.geteuid() == 0

def get_root_program_path() -> str:
    """
    Finds the root path of the Nessus Wrangler application folder and
    returns the full path to it.
    """
    return os.path.realpath(os.path.dirname(__file__))

def get_timestamp() -> str:
    """ Gets a timestamp in YYYYMMDD.HHMMSS format """
    return datetime.datetime.now().strftime("%Y%m%d.%H%M%S")

def backup_nmap_oui_file() -> str:
    """
    Make a backup of the nmap oui file return the path to the backup.
    """
    backup_dir = os.path.join(get_root_program_path(), "backups")
    if not os.path.isdir(backup_dir):
        print_info(f"Creating backup directory: {BLU}{backup_dir}{NC}")
        os.mkdir(backup_dir)
    backup_filename = f"nmap-mac-prefixes.{get_timestamp()}"
    dst = os.path.join(backup_dir, backup_filename)
    print_info(f"Creating backup of nmap-mac-prefixes: {BLU}{backup_filename}{NC}")
    shutil.copyfile(NMAP_OUI, dst)
    return dst

def download_ieee_oui_file() -> bool:
    """ Downloads the OUI data from the IEEE """
    print_info("Downloading latest copy of OUI data from IEEE...")
    dst = os.path.join(get_root_program_path(), OUI_DATA)
    res = requests.get(IEEE_URL)
    if res.status_code == 200 and "(base 16)" in res.text:
        with open(dst, 'wt', encoding='utf-8') as fil:
            fil.write(res.text)
            fil.flush()
        print_success(f"Downloaded to {BLU}{dst}{NC} ({len(res.text)} bytes)")
    else:
        print_error(f"Got status code {res.status_code} while downloading")
        return False
    return True

def parse_oui_file(backup: str) -> bool:
    """
    Parse the IEEE OUI file and look for missing records in the nmap OUI
    file and add them as needed, then write it to a new file in the root
    program directory.
    """
    print_info("Processing data: ", endline="\r")
    oui_file = os.path.join(get_root_program_path(), OUI_DATA)

    with open(backup, 'rt', encoding='utf-8') as fil:
        backup_data = fil.read()

    with open(oui_file, 'rt', encoding='utf-8') as fil:
        oui_data = fil.read()

    new_count = 0

    for line in oui_data.split("\n"):
        if "(base 16)" in line:
            match = re.search(r"^([0-9A-Fa-f]{6}) +\(base 16\)\t\t(.*)",line)
            oui, org = match.groups()
            if oui not in backup_data:
                record = f"{oui} {org.strip()}\n"
                backup_data += record
                sys.stdout.write("\033[K")
                print_info(f"Processing data: {GRN}{oui} {BLU}=> {GRN}{org}{NC}",
                           endline="\r")
                new_count += 1
    sys.stdout.write("\033[K")
    print_success(f"{NC}Processing data: [{GRN}DONE{NC}]")

    if new_count != 0:
        print_success(f"Found {new_count} new OUIs")
        updated = os.path.join(get_root_program_path(), 'nmap-mac-prefixes_updated')
        print_info(f"Writing new data to {BLU}{updated}{NC}")
        with open(updated, 'wt', encoding='utf-8') as fil:
            fil.write(backup_data)
            fil.flush()
        return True

    print_info("No new records!")
    return False

def apply_updated_file() -> bool:
    """ Copies the nmap-mac-prefixes_updated file to the real nmap folder. """
    updated = os.path.join(get_root_program_path(), 'nmap-mac-prefixes_updated')
    print_info(f"Copying {GRN}{updated}{NC} to {BLU}{NMAP_OUI}{NC}")
    shutil.copyfile(updated, NMAP_OUI)
    return True

def main() -> int:
    """ The main application logic. """
    # Print the Banner.
    print(f"{RED}{BANNER}{YLW}{SCRIPT}{NC}")

    # Ensure we are running as root.
    if not is_root():
        print_error("This script must be run as root!")
        return 1

    # Copy the nmap file to our local directory.
    backup_copy = backup_nmap_oui_file()

    # Attempt to download a copy of the IEEE OUI data.
    if not download_ieee_oui_file():
        return 2

    # Parse the OUI File data and add new records if needed.
    if parse_oui_file(backup_copy):
        # Attempt to Copy the nmap OUI file to /usr/share/nmap/
        if not apply_updated_file():
            return 4

    # Finally, return 0 if everything when well.
    print_success("Done son!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
