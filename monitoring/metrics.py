import datetime

import googleapiclient.discovery
from google.auth import app_engine

from util import settings

SCOPES = ('https://www.googleapis.com/auth/monitoring',
          'https://www.googleapis.com/auth/cloud-platform')
credentials = app_engine.Credentials(scopes=SCOPES)


def format_rfc3339(datetime_instance=None):
    """Formats a datetime per RFC 3339.
    :param datetime_instance: Datetime instanec to format, defaults to utcnow
    """
    return datetime_instance.isoformat("T") + "Z"


def get_now_rfc3339():
    # Return now
    return format_rfc3339(datetime.datetime.utcnow())


def get_start_time(minutes):
    # Return now- 5 minutes
    start_time = datetime.datetime.utcnow() - datetime.timedelta(
        minutes=minutes)
    return format_rfc3339(start_time)


class Metrics():

    def __init__(self):
        self.monitorservice = googleapiclient.discovery.build('monitoring',
                                                              'v3',
                                                              credentials=credentials)
        self.project_resource = "projects/{0}".format(
            settings.get_key('project_id'))
        self.metric_domain = 'custom.googleapis.com'
        self.cluster_name = settings.get_key('cluster')
        self.region = settings.get_key('cluster')
        self.create_custom_metric('ContainerPendingRatio')
        self.create_custom_metric('YARNMemoryAvailablePercentage')
        self.create_custom_metric('YarnNodes')
        self.project_id = settings.get_key('project_id')


    def write_timeseries_value(self, custom_metric_type, data_point):
        """Write the custom metric obtained."""
        now = get_now_rfc3339()
        custom_metric = "{}/{}".format(self.metric_domain, custom_metric_type)
        timeseries_data = {"metricKind": "GAUGE", "valueType": "DOUBLE",
                           "points": [
                               {
                                   "interval": {
                                       "startTime": now,
                                       "endTime": now
                                   },
                                   "value": {
                                       "doubleValue": data_point
                                   }
                               }
                           ], 'metric': {'type': custom_metric},
                           "resource": {"type": 'global', "labels": {
                               'project_id': self.project_id
                           }}
                           }

        request = self.monitorservice.projects().timeSeries().create(
            name=self.project_resource, body={"timeSeries": [timeseries_data]})
        request.execute()


    def read_timeseries(self, custom_metric_type, minutes):
        custom_metric = "{}/{}".format(self.metric_domain, custom_metric_type)
        request = self.monitorservice.projects().timeSeries().list(
            name=self.project_resource,
            filter='metric.type="{0}"'.format(custom_metric),
            pageSize=100,
            interval_startTime=get_start_time(minutes),
            interval_endTime=get_now_rfc3339())
        response = request.execute()
        return response


    def create_custom_metric(self, custom_metric_type):
        """Create custom metric descriptor"""
        custom_metric = "{}/{}".format(self.metric_domain, custom_metric_type)
        metrics_descriptor = {"type": custom_metric, "metricKind": "GAUGE",
                              "valueType": "DOUBLE",
                              "description": "Shamash Dataproc scaling"}
        metrics_descriptor['name'] = "{}/metricDescriptors/{}".format(
            self.project_resource, custom_metric_type)
        metrics_descriptor['type'] = custom_metric
        return self.monitorservice.projects().metricDescriptors().create(
            name=self.project_resource, body=metrics_descriptor).execute()
