import pytest
from main import create_scheduler

@pytest.fixture
def scheduler():
    sched = create_scheduler()
    return sched

def test_scheduler_jobs_exist(scheduler):
    jobs = scheduler.get_jobs()
    job_ids = {job.id for job in jobs}
    assert job_ids == {'bias', 'strategy', 'news'}

def test_scheduler_job_intervals(scheduler):
    jobs = {job.id: job for job in scheduler.get_jobs()}
    # bias every 60 minutes
    bias_job = jobs['bias']
    assert hasattr(bias_job.trigger, 'interval')
    assert bias_job.trigger.interval.total_seconds() / 60 == 60
    # strategy every 5 minutes
    strat_job = jobs['strategy']
    assert strat_job.trigger.interval.total_seconds() / 60 == 5
    # news every 15 minutes
    news_job = jobs['news']
    assert news_job.trigger.interval.total_seconds() / 60 == 15
