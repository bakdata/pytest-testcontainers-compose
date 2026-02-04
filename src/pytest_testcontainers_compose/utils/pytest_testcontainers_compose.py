import pathlib
import random
import string
import time
import timeit
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from deepmerge import Merger, always_merger
from pydantic import BaseModel, TypeAdapter, constr
from testcontainers.compose import DockerCompose
from testcontainers.core.docker_client import DockerClient
from testcontainers.core.utils import inside_container

from pytest_testcontainers_compose.models.docker import (
    ComposeSpecification,
    ListOfStrings,
    Network,
    Networks,
    Ports,
    Service,
)


# TODO: re-evaluate pydantic-yaml once they add support for Python 3.14
def parse_yaml_raw_as[T: BaseModel](Model: type[T], yaml_string: str) -> T:
    return TypeAdapter(Model).validate_python(yaml.safe_load(yaml_string))


def to_yaml_str(model_instance: BaseModel, **kwargs: Any) -> str:
    return yaml.safe_dump(model_instance.model_dump(**kwargs))


def load_docker_file(file_path: pathlib.Path) -> ComposeSpecification:
    with file_path.open() as file:
        return parse_yaml_raw_as(ComposeSpecification, file.read())


class DockerComposeBuilder:
    def __init__(self):
        self.spec = ComposeSpecification()  # type: ignore[reportCallIssue]

    def from_base(self, file: str | Path):
        if isinstance(file, str):
            self.spec = load_docker_file(Path(file))
        elif isinstance(file, Path):
            self.spec = load_docker_file(file)
        else:
            raise ValueError("file must be a string or Path")

        return self

    def set_networks(self, network_name: str, network: Network):
        if self.spec.networks is None:
            self.spec.networks = {}
        self.spec.networks[network_name] = network
        return self

    def set_service_networks(
        self,
        service: str,
        networks: ListOfStrings
        | dict[constr(pattern="^[a-zA-Z0-9._-]+$"), Networks | None]  # type: ignore[reportInvalidTypeForm]
        | None,
    ):
        if self.spec.services is None:
            self.spec.services = {}
        self.spec.services[service].networks = networks
        return self

    def set_ports(self, service: str, ports: list[float | str | Ports]):
        if self.spec.services is None:
            self.spec.services = {}
        self.spec.services[service].ports = ports
        return self

    def add_service(self, name: str, service: Service):
        if self.spec.services is None:
            self.spec.services = {}
        self.spec.services[name] = service
        return self

    def remove_service(self, name: str):
        if self.spec.services is not None:
            self.spec.services.pop(name)
        return self

    def remove_ports(self, service: str):
        if self.spec.services is not None:
            self.spec.services[service].ports = None
        return self

    def _merge_partial_specs(self, partial: ComposeSpecification, strategy: Merger):
        current = self.spec.model_dump(exclude_none=True)
        partial_dump = partial.model_dump(exclude_none=True)
        merged = strategy.merge(current, partial_dump)
        self.spec = ComposeSpecification.parse_obj(merged)
        return self

    def merge_partial_with_strategy(
        self, partial: ComposeSpecification, strategy: Merger
    ):
        return self._merge_partial_specs(partial, strategy)

    def merge_partial(self, partial: ComposeSpecification):
        return self._merge_partial_specs(partial, always_merger)

    def build_config(self, **kwargs):
        return to_yaml_str(self.spec, **kwargs)


class DockerComposeManager(DockerCompose):
    def __post_init__(self):
        super().__post_init__()
        self._docker = DockerClient()

    @cached_property
    def compose_command_property(self) -> list[str]:
        prefix = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(5)
        )
        command = super().compose_command_property
        command += ["-p", prefix]
        return command

    def _get_docker_client(self):
        return self._docker

    def wait_until_responsive(
        self,
        check: Any,
        timeout: float,
        pause: float,
        clock: Any = timeit.default_timer,
    ) -> None:
        """Wait until a service is responsive."""

        ref = clock()
        now = ref
        while (now - ref) < timeout:
            if check():
                return
            time.sleep(pause)
            now = clock()

        raise Exception("Timeout reached while waiting on service!")

    def get_service_host(
        self,
        service_name: str | None = None,
        port: int | None = None,
    ):
        container = self.get_container(service_name)
        if inside_container() and Path("/run/docker.sock").exists():
            if container.ID is None:
                raise ValueError("Container ID is not available")
            return self._get_docker_client().gateway_ip(container.ID)

        return super().get_service_host(service_name, port)

    def get_service_host_and_port(
        self,
        service_name: str | None = None,
        port: int | None = None,
    ) -> tuple[str | None, str | None]:
        port_service = self.get_service_port(service_name, port)
        host_service = self.get_service_host(service_name, port)
        return host_service, port_service
