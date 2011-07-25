#!/usr/bin/env python
#
# Copyright 2011 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import urllib2, sys
import splunk.client, utils
import splunk.results as results

ANALYTICS_INDEX_NAME = "sample_analytics"
ANALYTICS_SOURCETYPE = "sample_analytics"
APPLICATION_KEY = "application"
EVENT_KEY = "event"
DISTINCT_KEY = "distinct_id"
EVENT_TERMINATOR = "\\r\\n-----end-event-----\\r\\n"
PROPERTY_PREFIX = "analytics_prop__"

class TimeRange:
    DAY="1d"
    WEEK="1w"
    MONTH="1mon"    

class AnalyticsRetriever:
    def __init__(self, application_name, splunk_info):
        self.application_name = application_name
        self.splunk = splunk.client.connect(**splunk_info)

    def applications(self):
        query = "search index=%s | stats count by application" % (ANALYTICS_INDEX_NAME)
        job = self.splunk.jobs.create(query, exec_mode="blocking")

        applications = []
        reader = results.ResultsReader(job.results())
        for kind,result in reader:
            if kind == results.RESULT:
                applications.append({
                    "name": result["application"],
                    "count": int(result["count"] or 0)
                })

        return applications

    def events(self):
        query = "search index=%s application=%s | stats count by event" % (ANALYTICS_INDEX_NAME, self.application_name)
        job = self.splunk.jobs.create(query, exec_mode="blocking")

        events = []
        reader = results.ResultsReader(job.results())
        for kind,result in reader:
            if kind == results.RESULT:
                events.append({
                    "name": result["event"],
                    "count": int(result["count"] or 0)
                })

        return events

    def properties(self, event_name):
        query = 'search index=%s application=%s event="%s" | stats dc(%s*) as *' % (
            ANALYTICS_INDEX_NAME, self.application_name, event_name, PROPERTY_PREFIX
        )
        job = self.splunk.jobs.create(query, exec_mode="blocking")

        properties = []
        reader = results.ResultsReader(job.results())
        for kind,result in reader:
            if kind == results.RESULT:
                for field, count in result.iteritems():
                    properties.append({
                        "name": field,
                        "count": int(count or 0)
                    })

        return properties

    def property_values(self, event_name, property):
        query = 'search index=%s application=%s event="%s" | stats count by %s | rename %s as %s' % (
            ANALYTICS_INDEX_NAME, self.application_name, event_name, 
            PROPERTY_PREFIX + property,
            PROPERTY_PREFIX + property, property
        )
        job = self.splunk.jobs.create(query, exec_mode="blocking")

        values = []
        reader = results.ResultsReader(job.results())
        for kind,result in reader:
            if kind == results.RESULT:
                if result[property]:
                    values.append({
                        "name": result[property],
                        "count": int(result["count"] or 0)
                    })

        return values

    def events_over_time(self, event_name = "", time_range = TimeRange.MONTH, property = ""):
        query = 'search index=%s application=%s event="%s" | timechart span=%s count by %s | fields - _span*' % (
            ANALYTICS_INDEX_NAME, self.application_name, (event_name or "*"), 
            time_range,
            (PROPERTY_PREFIX + property) if property else "event",
        )
        job = self.splunk.jobs.create(query, exec_mode="blocking")

        over_time = {}
        reader = results.ResultsReader(job.results())
        for kind,result in reader:
            if kind == results.RESULT:
                # Get the time for this entry
                time = result["_time"]
                del result["_time"]

                # The rest is in the form of [event/property]:count
                # pairs, so we decode those
                for key,count in result.iteritems():
                    entry = over_time.get(key, [])
                    entry.append({
                        "count": int(count or 0),
                        "time": time,
                    })
                    over_time[key] = entry

        return over_time

    def events_summary(self):
        query = 'search index="%s" application="%s" | timechart span=1w count by event | rename _time as time | eval time=strftime(time, "%%a, %%d %%B") | fields - _*' % (
            ANALYTICS_INDEX_NAME, self.application_name, 
        )
        job = self.splunk.jobs.create(query, exec_mode="blocking")

        summary = {}
        reader = results.ResultsReader(job.results())
        for kind,result in reader:
            if kind == results.RESULT:
                print result

def main():
    usage = ""

    argv = sys.argv[1:]

    opts = utils.parse(argv, {}, ".splunkrc", usage=usage)
    retriever = AnalyticsRetriever(opts.args[0], opts.kwargs)    

    #events = retriever.events()
    #print events
    #for event in events:
    #    print retriever.properties(event["name"])

    #print retriever.property_values("critical", "version")
    #print retriever.events_over_time(time_range = TimeRange.MONTH)
    #print retriever.applications()
    #print retriever.events_over_time()
    #print retriever.events_summary()

if __name__ == "__main__":
    main()