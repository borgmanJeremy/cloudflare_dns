import logging
import os
from typing import Any, Dict, List, Optional, TypedDict

import requests


class DnsInfo(TypedDict):
    id: str
    zone_id: str
    zone_name: str
    name: str
    type: str
    content: str
    proxiable: bool
    proxied: bool
    ttl: int
    locked: bool
    meta: dict
    created_on: str
    modified_on: str


def list_zones() -> List[DnsInfo]:
    """List all zones associated with this cloudflare API key"""

    endpoint = "zones"
    r = requests.get(api_url + endpoint, headers=headers)

    if r.status_code == 200:
        return r.json()["result"]

    else:
        logging.error("HTTP: error listing domain")
        logging.debug(r)
        raise RuntimeError("Listing DNS did not return 200")


def get_zone_id_by_name(name: str) -> Optional[str]:
    """Get a zone id associated with API key and domain name"""

    zone_data = list_zones()
    for zone in zone_data:
        if zone["name"] == name:
            return zone["id"]
    return None


def dns_info(zone_id: str) -> dict:
    """Get all dns information related to this zone id"""

    endpoint = "zones/" + zone_id + "/dns_records"
    r = requests.get(api_url + endpoint, headers=headers)

    if r.status_code == 200:
        return r.json()

    else:
        logging.error("HTTP: error getting dns info")
        logging.debug(r)
        raise RuntimeError("Getting DNS info did not return 200")


def get_a_record_ips(zone_id: str) -> List[str]:
    """Get all ip address associated with all A-records on this zone id"""

    r = dns_info(zone_id)
    ip_list = []
    for record in r["result"]:
        if record["type"] == "A":
            ip_list.append(record["content"])
    return ip_list


def update_a_record_ip(zone_id: str, ip_address: str):
    """This function takes a zone id (represents id for domain name) and new
    ip address. All A-records associated with this ID will be update d
    to the new IP."""

    r = dns_info(zone_id)
    for record in r["result"]:
        if record["type"] == "A":
            record_id = record["id"]
            record_name = record["name"]

            endpoint = "zones/" + zone_id + "/dns_records/" + record_id
            r = requests.put(
                api_url + endpoint,
                headers=headers,
                json={
                    "type": "A",
                    "name": record_name,
                    "ttl": "1",
                    "content": ip_address,
                },
            )

            if r.status_code == 200:
                logging.info(
                    "Successfully Changed {} in zone {}".format(record_name, zone_id)
                )
            else:
                logging.error(
                    "HTTP: {} Failed to change {} in zone {}".format(
                        r.status_code, record_name, zone_id
                    )
                )
                logging.debug(r)
                raise RuntimeError("Failed to change dns information")


def update_ip(domain_name: str, new_ip: str):
    """If IP address in cloudflare does match provided IP, update all A-records
    associated with this domain name on cloudflare"""

    id = get_zone_id_by_name(domain_name)
    ip_addresses = get_a_record_ips(id)
    for address in ip_addresses:
        if address != new_ip:
            update_a_record_ip(id, new_ip)
        else:
            logging.info("{} is up to date".format(domain_name))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    auth_key = os.environ.get("CLOUDFLARE_API_KEY")
    domain_list = os.environ.get("CLOUDFLARE_URL_LIST").split(":")

    api_url = "https://api.cloudflare.com/client/v4/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + auth_key,
    }

    ip = requests.get("https://api.ipify.org").content.decode("utf8")

    for domain in domain_list:
        logging.info("Checking if {} is up to date".format(domain))
        update_ip(domain, ip)
