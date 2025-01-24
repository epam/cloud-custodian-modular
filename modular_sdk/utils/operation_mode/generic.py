import datetime
from http import HTTPStatus

from modular_sdk.commons import ModularException
from modular_sdk.models.operation_mode import OperationMode
from modular_sdk.utils.operation_mode.abstract import AbstractOperationModeDescriber
from modular_sdk.services.environment_service import EnvironmentService


class ModularOperationModeManagerService(AbstractOperationModeDescriber):

    def __init__(self, environment_service: EnvironmentService = None):
        if not environment_service:
            self.environment_service = EnvironmentService()
        else:
            self.environment_service = environment_service

    def get_mode(self, application_name: str = None) -> dict:
        if not application_name:
            application_name = self.environment_service.application()
            if not application_name:
                raise ModularException(
                    code=HTTPStatus.NOT_FOUND.value,
                    content="Missing environment variable 'application_name'"
                )
        app = self.get_application(application_name=application_name)
        if not app:
            raise ModularException(
                code=HTTPStatus.NOT_FOUND.value,
                content=f"No such component: '{application_name}'"
            )
        result = {
            "code": 200,
            "items": [{"application": app.application, "mode": app.mode}],
            "warnings": []
        }
        return result

    @staticmethod
    def create(name: str, applied_by: str, mode: str, description: str = None,
               meta: dict = None, white_list: list = None) -> OperationMode:

        application = OperationMode(
            application=name, mode=mode, applied_by=applied_by,
            description=description, meta=meta, testing_white_list=white_list,
            last_update_date=datetime.datetime.utcnow()
        )
        return application

    @staticmethod
    def get_application(application_name: str) -> OperationMode:
        return OperationMode.get_nullable(hash_key=application_name)

    @staticmethod
    def save(application: OperationMode) -> None:
        application.save()
