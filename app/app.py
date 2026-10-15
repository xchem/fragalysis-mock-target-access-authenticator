"""The entrypoint for the Fragalysis Stack FastAPI Mock ISPyB Target Access Authenticator."""

import ast
import json
import logging
import os
import re
from collections import defaultdict
from logging.config import dictConfig
from typing import Annotated, Any

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    status,
)
from pydantic import BaseModel

from .config import Config

# Configure logging
print("Configuring logging...")
_LOGGING_CONFIG: dict[str, Any] = {}
with open("logging.config", "r", encoding="utf8") as stream:
    try:
        _LOGGING_CONFIG = json.loads(stream.read())
    except json.decoder.JSONDecodeError as exc:
        print(exc)
dictConfig(_LOGGING_CONFIG)
print("Configured logging.")

_LOGGER = logging.getLogger(__name__)

app = FastAPI()

_VERSION_KIND: str = "MOCK"
_VERSION_NAME: str = "XChem Python FastAPI Mock TAS Authenticator"
with open("VERSION", "r", encoding="utf-8") as version_file:
    _VERSION: str = version_file.read().strip()

# Read the 'expected' target-access map.
# It is a string representation of a Python dictionary of usernames
# and the set of target access strings each user is a member of.
with open("ta-map.txt", "r", encoding="utf-8") as version_file:
    _TA_MAP: dict[str, set[str]] = ast.literal_eval(version_file.read().strip())

# The users for each target access string - the target-access map inverted.
# The map is the only source of truth we have, so a user in it is a member of
# every target access string it gives them.
_TAS_MAP: dict[str, set[str]] = defaultdict(set)
for _username, _user_tas in _TA_MAP.items():
    for _tas in _user_tas:
        _TAS_MAP[_tas].add(_username)
_LOGGER.info(
    "Mapped %s users onto %s target access strings", len(_TA_MAP), len(_TAS_MAP)
)

# Read the (optional) names map.
# It is a string representation of a Python dictionary of usernames
# and a (given name, family name) tuple. Users that are not in it
# (or every user, if there is no file) have no names.
_NAMES_FILE: str = "ta-names.txt"
_NAMES_MAP: dict[str, tuple[str, str]] = {}
if os.path.isfile(_NAMES_FILE):
    with open(_NAMES_FILE, "r", encoding="utf-8") as names_file:
        _NAMES_MAP = ast.literal_eval(names_file.read().strip())
_LOGGER.info("Read names for %s users", len(_NAMES_MAP))

# A target access string is a proposal code, a proposal number and a visit
# number, i.e. "lb12345-1" is code "lb", proposal "12345", visit "1".
_TAS_PATTERN: re.Pattern = re.compile(r"^([a-zA-Z]+)(\d+)-(\d+)$")


class TargetAccessGetVersionResponse(BaseModel):
    """/version/ GET response."""

    kind: str
    name: str
    version: str


class TargetAccessGetPingResponse(BaseModel):
    """/ping/ GET response."""

    ping: str


class TargetAccessGetUserTasResponse(BaseModel):
    """/target-access/{username}/ GET response."""

    count: int
    target_access: set[str]


class TargetAccessTasMember(BaseModel):
    """A member of a target access string."""

    login: str
    given_name: str | None
    family_name: str | None


class TargetAccessGetTasUsersResponse(BaseModel):
    """/users/{tas} GET response."""

    count: int
    users: set[str]
    # The same users, with their names, sorted by login
    members: list[TargetAccessTasMember]


# Endpoints (in-cluster) for the ISPyP Authenticator -----------------------------------


@app.get("/version/", status_code=status.HTTP_200_OK)
def get_taa_version() -> TargetAccessGetVersionResponse:
    """Returns our version information"""
    return TargetAccessGetVersionResponse(
        kind=_VERSION_KIND,
        name=_VERSION_NAME,
        version=_VERSION,
    )


@app.get("/ping/", status_code=status.HTTP_200_OK)
def ping():
    """Returns 'OK' if we can communicate with the underlying ISPyB service
    (i.e. create a connector). Anything other than 'OK' indicates a problem.
    """
    return TargetAccessGetPingResponse(ping="OK")


@app.get("/target-access/{username}", status_code=status.HTTP_200_OK)
def get_taa_user_tas(
    username: str,
    x_taaquerykey: Annotated[str | None, Header()] = None,
):
    """Returns the list of target access strings for a user.
    Target access strings are contained in string representation of a Python
    dictionary in the file expected to be mounted into $HOME/ta.txt. A default
    copy is contained in the image.
    """
    # We can only continue if the correct query key has been provided.
    if Config.QUERY_KEY and x_taaquerykey != Config.QUERY_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid/missing X_TAAQueryKey",
        )
    _LOGGER.debug("Request for '%s'", username)

    user_tas: set[str] = _TA_MAP.get(username) or set()
    count: int = len(user_tas)
    record: str = "record" if count == 1 else "records"
    _LOGGER.debug("Returning %s %s for '%s'", count, record, username)
    return TargetAccessGetUserTasResponse(
        count=count,
        target_access=user_tas,
    )


@app.get("/users/{tas}", status_code=status.HTTP_200_OK)
def get_taa_tas_users(
    tas: str,
    x_taaquerykey: Annotated[str | None, Header()] = None,
):
    """Returns the set of users that are members of a target access string.
    This is the target-access map (see above) inverted - a user is a member of
    every target access string the map gives them.
    """
    # We can only continue if the correct query key has been provided.
    if Config.QUERY_KEY and x_taaquerykey != Config.QUERY_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid/missing X_TAAQueryKey",
        )
    _LOGGER.debug("Request for '%s'", tas)

    if not _TAS_PATTERN.match(tas):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not a target access string ('{tas}')",
        )

    tas_users: set[str] = _TAS_MAP.get(tas) or set()
    members: list[TargetAccessTasMember] = []
    for login in sorted(tas_users):
        given_name, family_name = _NAMES_MAP.get(login, (None, None))
        members.append(
            TargetAccessTasMember(
                login=login, given_name=given_name, family_name=family_name
            )
        )
    count: int = len(tas_users)
    user: str = "user" if count == 1 else "users"
    _LOGGER.debug("Returning %s %s for '%s'", count, user, tas)
    return TargetAccessGetTasUsersResponse(
        count=count,
        users=tas_users,
        members=members,
    )
