#This is the first stage, it is named requirements-stage.
FROM python:3.10.12-slim as requirements-stage

# Set the working directory in the container
WORKDIR /tmp

# Install Poetry in this Docker stage.
RUN pip install poetry

# Copy the pyproject.toml and poetry.lock files to the /tmp directory.
COPY ./pyproject.toml ./poetry.lock* /tmp/

# Generate the requirements.txt file.
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes



# This is the final stage, anything here will be preserved in the final container image.
FROM python:3.10.12-slim

# Set the current working directory to /code.
WORKDIR /code

# Copy the requirements.txt file to the /code directory.
# This file only lives in the previous Docker stage, that's why we use --from-requirements-stage to copy it.
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

# Update the package lists for upgrades for packages and install gcc and libpq-dev
RUN apt-get update && apt-get install -y gcc libpq-dev

# Install the package dependencies in the generated requirements.txt file.
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Create a user named appuser with UID 5678 and change ownership of the /code directory to appuser
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /code

COPY ./alembic /code/alembic
COPY ./alembic.ini /code
COPY ./app /code/app

# Copy the app directory to the /code directory.



# Copy the entrypoint script into the Docker image
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# EXPOSE 8000


# Set the entry point to the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]


# Run the uvicorn command, telling it to use the app object imported from app.main.
CMD ["uvicorn", "app.main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
