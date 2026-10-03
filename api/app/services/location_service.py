"""Turn a US ZIP code or city + state into coordinates, a readable label and a time zone.

1. Zippopotam.us (free, no key) resolves ZIP codes and city/state -> place, lat, lng.
2. Aladhan (already used for prayer times) gives the time zone for those coordinates.
Aladhan's own address lookup is kept as a fallback.
"""
import re
from datetime import datetime
from urllib.parse import quote
import httpx

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA","KS",
    "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC",
    "ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","PR",
}


class LocationLookupError(Exception):
    """The lookup services could not be reached."""


def _get(url, params=None):
    r = httpx.get(url, params=params, follow_redirects=True, timeout=12)
    return r


def _zippopotam_zip(zip_code):
    r = _get(f"https://api.zippopotam.us/us/{zip_code}")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    place = (r.json().get("places") or [None])[0]
    if not place:
        return None
    return {
        "city": place.get("place name"),
        "state": place.get("state abbreviation"),
        "latitude": float(place["latitude"]),
        "longitude": float(place["longitude"]),
    }


def _zippopotam_city(city, state):
    r = _get(f"https://api.zippopotam.us/us/{state.lower()}/{quote(city.lower())}")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    places = r.json().get("places") or []
    if not places:
        return None
    lat = sum(float(p["latitude"]) for p in places) / len(places)
    lng = sum(float(p["longitude"]) for p in places) / len(places)
    return {"city": city.title(), "state": state, "latitude": lat, "longitude": lng}


def _timezone_for(lat, lng):
    date_str = datetime.utcnow().strftime("%d-%m-%Y")
    r = _get(f"https://api.aladhan.com/v1/timings/{date_str}",
             {"latitude": lat, "longitude": lng, "method": 2})
    meta = (r.json().get("data") or {}).get("meta") or {}
    return meta.get("timezone")


def _aladhan_address(address):
    r = _get("https://api.aladhan.com/v1/timingsByAddress", {"address": address, "method": 2})
    data = r.json()
    if data.get("code") != 200 or not isinstance(data.get("data"), dict):
        return None
    meta = data["data"].get("meta") or {}
    if meta.get("latitude") is None or not meta.get("timezone"):
        return None
    return float(meta["latitude"]), float(meta["longitude"]), meta["timezone"]


def resolve_location(zip_code=None, city=None, state=None, country: str = "US"):
    """Returns a dict of user fields, None if the place can't be found,
    or raises LocationLookupError if the services are unreachable."""
    zip_code = (zip_code or "").strip()
    city = " ".join((city or "").split())
    state = (state or "").strip().upper()
    if zip_code and (city or state):
        return None  # exactly one option: ZIP code OR city + state

    if zip_code:
        if not re.fullmatch(r"\d{5}", zip_code):
            return None
    elif not (city and state in US_STATES):
        return None

    try:
        place = _zippopotam_zip(zip_code) if zip_code else _zippopotam_city(city, state)
        tz = _timezone_for(place["latitude"], place["longitude"]) if place else None
        if place and tz:
            return {
                "zip_code": zip_code or None,
                "city": place["city"],
                "state": place["state"],
                "location_label": f"{place['city']}, {place['state']}",
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "timezone": tz,
            }
        # Fallback: Aladhan's own address lookup
        address = f"{zip_code}, {country}" if zip_code else f"{city}, {state}, {country}"
        found = _aladhan_address(address)
        if not found:
            return None
        lat, lng, tz = found
        return {
            "zip_code": zip_code or None,
            "city": city.title() if city else None,
            "state": state or None,
            "location_label": f"ZIP {zip_code}" if zip_code else f"{city.title()}, {state}",
            "latitude": lat,
            "longitude": lng,
            "timezone": tz,
        }
    except Exception as e:
        print(f"location lookup error: {e}")
        raise LocationLookupError(str(e))
