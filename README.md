# pytest-testcontainers-compose

pytest-testcontainers-compose is a pytest plugin built on top of python-testcontainers that
builds and manages a Docker Compose stack as part of the test execution.

## Key Features

- **Pytest-based Docker Compose lifecycle management**
  Integrates directly with pytest using fixtures to automatically start and stop
  Docker Compose services as part of the test lifecycle.

- **Dynamic Compose Configuration**
  Allows modifying Docker Compose configurations at runtime, such as removing
  services, exposing ports, or merging partial configurations for test setups.

- **Service Readiness Handling**
  Provides utilities to wait until services are actually responsive, not just
  running, before executing tests.

- **Host and Port Resolution**
  Resolves service hostnames and ports correctly across different environments,
  including local development, CI, and Docker-in-Docker setups.

## Instalation

```sh
pip install pytest-testcontainers-compose
```

## Basis Usage

```python
from pathlib import Path
import pytest
from pytest_testcontainers_compose.utils import (
    DockerComposeBuilder,
    DockerComposeManager
)

# Enable the plugin
pytest_plugins = ("pytest_testcontainers_compose.plugin",)

# Provide base compose file and a temp output file
@pytest.fixture(scope="session")
def docker_compose_base_config() -> Path:
    return Path("../docker-compose.yaml")

@pytest.fixture(scope="session")
def temp_docker_compose_file_name() -> Path:
    return Path("../test-docker-compose-file.yaml")

# Adjust compose configuration for tests
@pytest.fixture(scope="session")
def docker_compose_build(docker_config_builder: DockerComposeBuilder) -> DockerComposeBuilder:
    return(
        docker_config_builder
        .remove_service("api")
        .remove_service("web")
        .set_ports("postgres", ["5432"])
    )

# Consume docker_compose and resolve host/port
@pytest.fixture(scope="session")
def postgres_host_port(docker_compose: DockerComposeManager) -> tuple[str, int]:
    host, port = docker_compose.get_service_host_and_port("postgres", 5432)
    assert host
    assert port
    return host, int(port)

```

## Advanced Usage

### Reuse existing infrastructure

```python
import os
import pytest

REUSE_CONTAINERS = os.environ.get("REUSE_CONTAINERS", False)

if REUSE_CONTAINERS:
    # Fixtures pointing to existing services
    ...
else:
    pytest_plugins = ("pytest_testcontainers_compose.plugin",)
    # Docker Compose–based fixtures
    ...

```

### Build a minimal test compose

Large docker-compose.yaml files often contain services that are not required for
integration tests. Starting unnecessary services increases startup time and
resource usage.

```python
from pathlib import Path
import pytest
from pytest_testcontainers_compose.utils import DockerComposeBuilder

@pytest.fixture(scope="session")
def docker_compose_base_config() -> Path:
    return Path("../docker-compose.yaml")

@pytest.fixture(scope="session")
def docker_compose_build(
    docker_config_builder: DockerComposeBuilder,
) -> DockerComposeBuilder:
    return (
        docker_config_builder
        .remove_service("api")
        .remove_service("web")
        .remove_service("oauth2-proxy")
        .remove_service("mssql")
        .set_ports("postgres", ["5432"])
        .set_ports("keycloak", ["8180"])
        .set_ports("minio", ["9000", "9001"])
    )

```

### Service fixtures with readiness checks

Containers being “running” does not mean the service is ready.
Use wait_until_responsive to block until the service is actually usable.

```python
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from pytest_testcontainers_compose.utils import DockerComposeManager

@pytest.fixture(scope="session")
def postgres(docker_compose: DockerComposeManager):
    host, port = docker_compose.get_service_host_and_port("postgres", 5432)
    assert host and port

    engine = create_engine(
        f"postgresql+psycopg://postgres:postgres@{host}:{port}/app"
    )

    def is_responsive() -> bool:
        try:
            with Session(engine) as session:
                session.execute(text("select 1"))
            return True
        except Exception:
            return False

    docker_compose.wait_until_responsive(
        timeout=120.0,
        pause=10,
        check=is_responsive,
    )

    return engine
```

### Derived fixtures

Once core services are running, additional fixtures can be derived from them.
Example: S3 client backed by MinIO

```python
import pytest
from s3_utils.client import S3Client
from s3_utils.model import S3Settings

@pytest.fixture(scope="session")
def s3_client(minio: str) -> S3Client:
    return S3Client(
        S3Settings(
            access_key="your_minio_access_key",
            secret_key="your_minio_secret_key",
            endpoint=minio,
            verify=False,
        )
    )

```

### Database isolation per test

A common pattern is to keep containers running for the entire session
but isolate database state per test using transactions and savepoints.

```python
import pytest
from sqlalchemy import Connection, Engine
from sqlalchemy.orm import Session

@pytest.fixture()
def db_connection(postgres: Engine) -> Connection:
    return postgres.connect()

@pytest.fixture()
def db(db_connection: Connection) -> Session:
    transaction = db_connection.begin()
    try:
        yield Session(bind=db_connection)
    finally:
        transaction.rollback()

```

## Contributing

We are happy if you want to contribute to this project. If you find any bugs or have suggestions for improvements, please open an issue. We are also happy to accept your PRs. Just open an issue beforehand and let us know what you want to do and why.

## License

pytest_testcontainers_compose is licensed under the MIT License.
