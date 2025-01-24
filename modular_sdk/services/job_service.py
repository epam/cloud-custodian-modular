from datetime import datetime
from http import HTTPStatus
from typing import Optional, List

from pynamodb.exceptions import DoesNotExist

from modular_sdk.commons import generate_id
from modular_sdk.commons import ModularException
from modular_sdk.commons.log_helper import get_logger
from modular_sdk.models.job import Job

_LOG = get_logger(__name__)


class JobService:
    @staticmethod
    def create(job: str, job_id: str, application: str, started_at: datetime, 
               state: str, stopped_at: Optional[datetime] = None,
               error_type: Optional[str] = None, 
               error_reason: Optional[str] = None, 
               meta: Optional[dict] = None) -> Job:
        job_id = job_id or generate_id()
        return Job(job=job, job_id=job_id, application=application, 
            started_at=started_at, state=state, stopped_at=stopped_at, 
            error_type=error_type, error_reason=error_reason, meta=meta)
        
    @staticmethod
    def get_by_id(job: str, job_id: str) -> Optional[Job]:
        try:
            job_item = Job.get(hash_key=job, range_key=job_id)
        except DoesNotExist:
            job_does_not_exist_message = f'Job with {job} name and {job_id} ' \
                                    f'id does not exists'
            _LOG.error(job_does_not_exist_message)
            raise ModularException(
                code=HTTPStatus.NOT_FOUND.value,
                content=job_does_not_exist_message
            )
        return job_item

    @staticmethod
    def list(job: str) -> List[Job]:
        jobs = Job.query(hash_key=job)
        return list(jobs)

    @staticmethod
    def list_within_daterange(job: str, start_date: datetime, 
                              end_date: datetime) -> List[Job]:
        jobs = Job.job_started_at_index.query(
            hash_key=job,
            range_key_condition=Job.started_at.between(start_date, end_date)
        )
        return list(jobs)

    @staticmethod
    def save(job: Job):
        job.save()

    @staticmethod
    def update(job: Job, started_at: Optional[datetime] = None, 
               state: Optional[str] = None, 
               stopped_at: Optional[datetime] = None,
               error_type: Optional[str] = None, 
               error_reason: Optional[str] = None, 
               meta: Optional[dict] = None):
        attributes = {
            'started_at': started_at,
            'state': state,
            'stopped_at': stopped_at,
            'error_type': error_type,
            'error_reason': error_reason,
            'meta': meta
        }
        actions = [
            getattr(Job, attr).set(value or getattr(job, attr))
            for attr, value in attributes.items() 
            if value or getattr(job, attr)
        ]
        job.update(actions=actions)

    @staticmethod
    def get_dto(Job: Job) -> dict:
        return Job.get_json()
