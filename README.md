# The Fragalysis Mock Target Access Authenticator

![GitHub Release](https://img.shields.io/github/v/release/xchem/fragalysis-mock-target-access-authenticator?include_prereleases)

[![build](https://github.com/xchem/fragalysis-mock-target-access-authenticator/actions/workflows/build.yaml/badge.svg)](https://github.com/xchem/fragalysis-mock-target-access-authenticator/actions/workflows/build.yaml)
[![tag](https://github.com/xchem/fragalysis-mock-target-access-authenticator/actions/workflows/tag.yaml/badge.svg)](https://github.com/xchem/fragalysis-mock-target-access-authenticator/actions/workflows/tag.yaml)

[![License](http://img.shields.io/badge/license-Apache%202.0-blue.svg?style=flat)](https://github.com/xchem/fragalysis-mock-target-access-authenticator/blob/master/LICENSE.txt)

[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Packaged with uv](https://img.shields.io/badge/packaging-uv-cyan.svg)](https://docs.astral.sh/uv/)

A **Mock** implementation of the official ISPyB authenticator.

For a complete description of the purpose of the authenticator please refer to its
official repository at https://github.com/xchem/fragalysis-ispyb-target-access-authenticator.

**This is simplified Mock version used for developer testing.**

## Contributing
The project uses: -

- [pre-commit] to enforce linting of files prior to committing them to the
  upstream repository
- [Commitizen] to enforce a [Conventional Commit] commit message format
- [Black] as a code formatter
- [uv] as a package manager (for the b/e)

You **MUST** comply with these choices in order to  contribute to the project.

To get started review the pre-commit utility and the conventional commit style
and then set-up your local clone by following the **Installation** and
**Quick Start** sections: -

    uv sync
    uv run pre-commit install -t commit-msg -t pre-commit

Now the project's rules will run on every commit, and you can check the
current health of your clone with: -

    uv run pre-commit run --all-files

`uv sync` creates a `.venv` in the clone from the `uv.lock` file. Prefix
commands with `uv run` to use it, or activate it with
`source .venv/bin/activate`. The Python version is pinned by `.python-version`,
and matches the version used by the container image.

If you change a dependency in `pyproject.toml` run `uv lock` and commit the
updated `uv.lock` - the image build uses `uv sync --locked`, which fails if the
two are out of step.

## Design
We use Python's [FastAPI] framework to offer a lightweight (**Mock**) implementation of
the HTTP service expected by the official authenticator.

The image relies on a list of Target Access Strings that are present in a file
mounted into the container at `/hom/taa/ta-map.txt`. It is a string representation
of a Python dictionary using username as keys and a `set` of strings used as the
Target Access Strings for the user. By providing your own `ta-map.txt` you can
associate any user with any set of Target Access Strings.

There's an example file (`ta-map.txt`) in the project root that is
mounted into the image by the `docker-compose.yml`.

### `/users/{tas}` **[GET]**
As well as returning the target access strings for a user, the mock answers the
reverse question - which users are members of a given target access string: -

```json
{
  "count": 2,
  "users": [ "dave lister", "rimmer" ],
  "members": [
    { "login": "dave lister", "given_name": "Dave", "family_name": "Lister" },
    { "login": "rimmer", "given_name": "Arnold", "family_name": "Rimmer" }
  ]
}
```

The users are simply the target-access map inverted, so a user is a member of
every target access string the map gives them. With the example file above,
`/users/sb99999-9` returns `dave lister` and `rimmer`.

`members` (sorted by `login`) carries each user's given and family names. These
come from an **optional** file mounted at `/home/taa/ta-names.txt` - a string
representation of a Python dictionary of username and a `(given name, family name)`
tuple: -

```
{
  'dave lister': ('Dave', 'Lister'),
  'rimmer': ('Arnold', 'Rimmer')
}
```

A user without an entry (or every user, if there is no file) has `null` names.
There's an example (`ta-names.txt`) in the project root that is mounted into the
image by the `docker-compose.yml`.

A **400** is returned if the value provided is not a target access string
(`<code><proposalNumber>-<visitNumber>`, i.e. `lb12345-1`), and an empty set if
no user in the map is a member of it. As with `/target-access/{username}` the
caller must provide the `X-TAAQueryKey` header.

>   The official (ISPyB) authenticator also returns a **503** when it cannot
    reach ISPyB. The mock has no such service to fail, so it never does.

## Local development
There's a `docker-compose.yml` file to deploy the authenticator and memcached.
It also relies on [environment variables] that you can easily set using a `.env` file
(which is excluded from any repository commits).

Build and launch the code using the `docker compose` file: -

    docker compose up --build --detach

## Using the mock authenticator (Fragalysis)
You can use the mock authenticator as part of your local fragalysis development
workflow to simulate a _real_ service.

You will need a text file of users and target-access strings that you want to
test against, a string representation of a python dictionary. Something like this: -

```
{
  'dave-lister': {'sb99999-9', 'sb99999-99'},
  'rimmer': {'sb99999-9'},
  'cat': {'sb99999-9'}
}
```

You need to add the mock service to your Fragalysis `docker-compose` file.
Assuming your file of target access strings is called `ta-map.txt` and is present in the
same directory as your compose file, the following should be sufficient: -

```yaml
ta-authenticator:
  image: xchem/fragalysis-mock-target-access-authenticator:1.1.0
  container_name: ta-authenticator
  environment:
    TAA_QUERY_KEY: blob1234
  ports:
  - '8081:8080'
  volumes:
  - ${PWD}/ta-map.txt:/home/taa/ta-map.txt
  - ${PWD}/ta-names.txt:/home/taa/ta-names.txt
```

This creates a service at `ta-authenticator` on port `8081`. You then
just need to add a couple of variables to the stack's variables.
For the above these would be: -

```yaml
environment:
  TA_AUTH_QUERY_KEY : blob1234
  TA_AUTH_SERVICE: ta-authenticator
```

With this done your stack should be able to obtain results from the
mock service.

---

[black]: https://black.readthedocs.io/en/stable
[commitizen]: https://commitizen-tools.github.io/commitizen/
[conventional commit]: https://www.conventionalcommits.org/en/v1.0.0/
[environment variables]: https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/
[fastapi]: https://fastapi.tiangolo.com
[uv]: https://docs.astral.sh/uv
[pre-commit]: https://pre-commit.com
