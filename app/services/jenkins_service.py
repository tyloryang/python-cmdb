import jenkins
import time
from app.config import settings

class JenkinsService:
    def __init__(self):
        if settings.JENKINS_URL:
            self.server = jenkins.Jenkins(
                settings.JENKINS_URL,
                username=settings.JENKINS_USER,
                password=settings.JENKINS_TOKEN
            )
        else:
            self.server = None

    def trigger_job(self, job_name, params=None):
        if not self.server:
            return None
        return self.server.build_job(job_name, parameters=params)

    def get_build_info(self, job_name, build_number):
        if not self.server:
            return None
        return self.server.get_build_info(job_name, build_number)

    def get_build_console_output(self, job_name, build_number):
        if not self.server:
            return None
        return self.server.get_build_console_output(job_name, build_number)

    def get_last_build_number(self, job_name):
        if not self.server:
            return None
        return self.server.get_job_info(job_name)['lastBuild']['number']

jenkins_service = JenkinsService()
