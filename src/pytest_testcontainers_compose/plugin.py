from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from _pytest.config import Config

from pytest_testcontainers_compose.utils import (
    DockerComposeBuilder,
    DockerComposeManager,
)


def containers_scope(_fixture_name: str, config: Config) -> Any:
    return config.getoption("--container-scope", "session")  # type: ignore[reportArgumentType]


@pytest.fixture(scope=containers_scope)
def docker_compose_base_config() -> Path:
    return Path("")


@pytest.fixture(scope=containers_scope)
def temp_docker_compose_file_name() -> Path:
    return Path("test-docker-compose-file.yaml")


@pytest.fixture(scope=containers_scope)
def docker_config_builder(docker_compose_base_config) -> DockerComposeBuilder:
    docker_config = DockerComposeBuilder()
    if docker_compose_base_config.name:
        docker_config.from_base(docker_compose_base_config)
    return docker_config


@pytest.fixture(scope=containers_scope)
def docker_compose_build(docker_config_builder) -> DockerComposeBuilder:
    return docker_config_builder


@pytest.fixture(scope=containers_scope)
def docker_compose_config_file(
    docker_compose_build: DockerComposeBuilder, temp_docker_compose_file_name: Path
) -> Generator[Path, None, None]:
    config = docker_compose_build.build_config(exclude_none=True)
    with temp_docker_compose_file_name.open("w") as file:
        file.write(config)
    yield temp_docker_compose_file_name
    temp_docker_compose_file_name.unlink(missing_ok=True)


@pytest.fixture(scope=containers_scope)
def docker_compose(docker_compose_config_file: Path):
    with DockerComposeManager(
        compose_file_name=docker_compose_config_file.name,
        context=docker_compose_config_file.parent,
    ) as compose:
        yield compose
