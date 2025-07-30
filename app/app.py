"""The entrypoint for the Fragalysis Stack FastAPI Mock ISPyB Target Access Authenticator."""

import ast
import json
import logging
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

# Read the 'expected' target-access map
with open("ta-map.txt", "r", encoding="utf-8") as version_file:
    _TA_MAP: str = ast.literal_eval(version_file.read().strip())


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
