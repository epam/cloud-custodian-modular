from abc import ABC, abstractmethod
from http import HTTPStatus

from modular_sdk.commons import ModularException

ALLOWED_MODES = ["LIVE", "MAINTENANCE", "TESTING"]


class AbstractOperationModeDescriber(ABC):

    @abstractmethod
    def get_mode(self, component_name):
        pass


class AbstractOperationModeManager(AbstractOperationModeDescriber):

    @abstractmethod
    def set_mode(self, mode, component_name, applied_by, description, meta):
        pass

    @abstractmethod
    def check_mode(self, mode):
        if mode not in ALLOWED_MODES:
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=f"Wrong mode '{mode}' selected. Allowed modes are: "
                        f"'{ALLOWED_MODES}'"
            )
