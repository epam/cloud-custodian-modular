from datetime import datetime
from modular_sdk.commons.constants import JOB_RUNNING_STATE, JOB_FAIL_STATE, \
    JOB_SUCCESS_STATE
from http import HTTPStatus

from modular_sdk.commons import ModularException

from modular_sdk.commons.log_helper import get_logger
from modular_sdk.services.environment_service import EnvironmentService
from modular_sdk.services.job_service import JobService
from modular_sdk.utils.operation_mode.generic import \
    ModularOperationModeManagerService
from modular_sdk.utils.job_tracer.abstract import AbstractJobTracer

_LOG = get_logger(__name__)


class ModularJobTracer(AbstractJobTracer):
    def __init__(self, operation_mode_service: ModularOperationModeManagerService,
                 environment_service: EnvironmentService, component=None):
        self.operation_mode_service = operation_mode_service
        self.environment_service = environment_service
        self.application = self.environment_service.application()
        self.component = component or self.environment_service.component()

    def start(self, job_id, meta=None):
        _LOG.debug(f'Going to mark Job {self.component} and {job_id} id as '
                   f'started')

        if meta is None:
            meta = {}

        # self.is_permitted_to_start()
        job = JobService.create(job=self.component, job_id=job_id,
                                application=self.application,
                                started_at=datetime.utcnow(),
                                state=JOB_RUNNING_STATE, meta=meta)
        JobService.save(job=job)

    def is_permitted_to_start(self):
        result = self.operation_mode_service.get_mode(
            application_name=self.application
        )
        if result.get('items', {})[0].get('mode', '') == 'LIVE':
            return
        unappropriated_mode_message = f'{self.application} can not be traced ' \
                                      f'due to unappropriated mode'
        _LOG.error(unappropriated_mode_message)
        raise ModularException(
            code=HTTPStatus.FORBIDDEN.value,
            content=unappropriated_mode_message
        )

    @staticmethod
    def __get_job(job, job_id):
        job_item = JobService.get_by_id(job=job, job_id=job_id)
        if job_item.state in ['SUCCESS', 'FAIL']:
            job_invalid_state_message = f'Job with {job_id} id and ' \
                                        f'{job} name with state ' \
                                        f'not equal to RUNNING can not be ' \
                                        f'changed'

            _LOG.error(job_invalid_state_message)
            raise ModularException(
                code=HTTPStatus.BAD_REQUEST.value,
                content=job_invalid_state_message
            )
        return job_item

    def fail(self, job_id, error):
        _LOG.debug(f'Going to mark Job {self.component} and {job_id} id as '
                   f'failed')

        job_item = self.__get_job(job=self.component, job_id=job_id)

        stopped_at = datetime.utcnow()
        state = JOB_FAIL_STATE
        error_type = error.__class__.__name__
        error_reason = error.__str__()
        JobService.update(job=job_item, stopped_at=stopped_at, state=state,
                          error_type=error_type, error_reason=error_reason)

    def succeed(self, job_id, meta):
        _LOG.debug(f'Going to mark Job {self.component} and {job_id} id as '
                   f'succeeded')
        job_item = self.__get_job(job=self.component, job_id=job_id)

        stopped_at = datetime.utcnow()
        state = JOB_SUCCESS_STATE
        JobService.update(job=job_item, stopped_at=stopped_at, state=state,
                          meta=meta)

    def track_error(self):
        # todo submit error to aggregation pipeline
        pass
