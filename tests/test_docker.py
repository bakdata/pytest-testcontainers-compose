from pytest_testcontainers_compose.models.docker import ComposeSpecification, Service
from pytest_testcontainers_compose.utils import (
    DockerComposeBuilder,
)


def test_simple_docker_file():
    docker = DockerComposeBuilder()
    partial = ComposeSpecification(
        services={"test-service": Service(image="python:3.10")}
    )  # type: ignore[reportCallIssue]
    config = (
        docker.merge_partial(partial)
        .set_ports("test-service", ["8080:8080", "8081:8081"])
        .build_config(exclude_none=True)
    )
    assert (
        config
        == """services:
  test-service:
    image: python:3.10
    ports:
    - 8080:8080
    - 8081:8081
"""
    )


def test_from_base_docker_file():
    docker = DockerComposeBuilder().from_base(
        "tests/resources/docker-compose.base.yaml"
    )
    assert (
        docker.build_config(exclude_none=True)
        == """services:
  test-service:
    image: test-image
    ports:
    - 2020:2020
"""
    )
    config = docker.set_ports("test-service", ["8080:8080", "8081:8081"]).build_config(
        exclude_none=True
    )
    assert (
        config
        == """services:
  test-service:
    image: test-image
    ports:
    - 8080:8080
    - 8081:8081
"""
    )


def test_merge_base_docker_file_with_partial_merge_strategy():
    docker = DockerComposeBuilder().from_base(
        "tests/resources/docker-compose.base.yaml"
    )
    partial = ComposeSpecification(
        services={"test-service": Service(image="python:3.10")}
    )  # type: ignore[reportCallIssue]
    build_config = docker.merge_partial(partial).build_config(exclude_none=True)
    assert (
        build_config
        == """services:
  test-service:
    image: python:3.10
    ports:
    - 2020:2020
"""
    )
