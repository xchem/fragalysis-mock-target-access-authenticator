# The default base image
ARG from_image=python:3.12.11-alpine3.22
FROM ${from_image} AS python-base

# Force the binary layer of the stdout and stderr streams
# to be unbuffered
ENV PYTHONUNBUFFERED=1

# Base directory for the application
# Also used for user directory
ENV APP_ROOT=/home/taa

WORKDIR ${APP_ROOT}

# another stage for uv installation. this ensures uv won't end
# up in final image where it's not needed
FROM python-base AS uv-base
ARG UV_VERSION=0.11.21

RUN pip install --no-cache-dir uv==${UV_VERSION}

WORKDIR /
COPY uv.lock pyproject.toml /

# uv creates the venv in the working directory (.venv), so the location
# is predictable. '--locked' fails the build if uv.lock is out of step with
# pyproject.toml, and '--no-dev' leaves the dev group out of the image.
# UV_PYTHON_DOWNLOADS=never keeps uv on the image's own interpreter rather
# than fetching one of its own (the base image decides the Python version).
ENV UV_PYTHON_DOWNLOADS=never
RUN uv sync --locked --no-dev

# final stage. only copy the venv with installed packages and point
# paths to it
FROM python-base AS final

COPY --from=uv-base /.venv /.venv

ENV PYTHONPATH="/.venv/lib/python3.12/site-packages/"
ENV PATH=/.venv/bin:$PATH

COPY app/ ./app/
COPY logging.config .
COPY docker-entrypoint.sh .
COPY VERSION .

# Create a base directory for file-based logging
WORKDIR /logs

# Switch to container user
ENV HOME=${APP_ROOT}
WORKDIR ${APP_ROOT}

# Start the application
CMD ["./docker-entrypoint.sh"]
