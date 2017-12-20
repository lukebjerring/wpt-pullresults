#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import certifi
import json
import logging
import requests
import urllib3
import wptdash.models as models
from urllib.parse import urlencode
from flask import render_template
from typing import Optional, Tuple

from wptdash.github import GitHub

CONFIG = configparser.ConfigParser()
CONFIG.readfp(open(r'config.txt'))
APP_DOMAIN = CONFIG.get('app', 'APP_DOMAIN')
ORG_NAME = CONFIG.get('GitHub', 'ORG')
REPO_NAME = CONFIG.get('GitHub', 'REPO')


# TODO: make this return some useful JSON
def update_github_comment(pr):
    # type: (models.PullRequest) -> Tuple[str, int]
    resp = None
    build = pr.latest_build
    if build is not None:
        github = GitHub()

        has_unstable = False
        failing_jobs = []
        regressed_jobs = []
        for job in build.jobs:  # type: models.Job
            if job.state.name == 'FAILED':
                failing_jobs.append(job.product.name)
            if not has_unstable:
                for test in job.tests:
                    if not test.consistent:
                        has_unstable = True
                        break

            # Check for pass/fail state changes.
            summary = results_summary(job)
            if summary is not None:
                product = job.product.name.split(":")[0]
                product = 'edge' if product is 'MicrosoftEdge' else product
                results_diff = diff(summary, product)
                if results_diff is not None and len(results_diff) > 0:
                    regressed_jobs.append(job.product.name)

        comment = render_template('comment.md',
                                  build=build,
                                  app_domain=APP_DOMAIN,
                                  org_name=ORG_NAME,
                                  repo_name=REPO_NAME,
                                  has_unstable=has_unstable,
                                  failing_jobs=failing_jobs,
                                  regressed_jobs=regressed_jobs)
        if not github.validate_comment_length(comment):
            comment = render_template('comment-short.md',
                                      build=build,
                                      app_domain=APP_DOMAIN,
                                      org_name=ORG_NAME,
                                      characters=github.max_comment_length,
                                      repo_name=REPO_NAME,
                                      has_unstable=has_unstable,
                                      failing_jobs=failing_jobs,
                                      regressed_jobs=regressed_jobs)
        try:
            resp = github.post_comment(pr.number, comment, pr.comment_url)
            pr.comment_url = resp.json().get('url')
        except requests.RequestException as err:
            logging.error(err.response.text)
            return err.response.text, 500
    return 'OK', 200


def diff(results, product):  # type: (Optional[dict], str) -> Optional[dict]
    """Fetch a python dict representing the differences in run results JSON
    for the given results."""
    if results is None:
        return None

    pool = urllib3.PoolManager(
        cert_reqs='CERT_REQUIRED',
        ca_certs=certifi.where())

    # type: (str, str) -> dict
    # Note that the dict's keys are the test paths, and values are an
    # array of [pass_count, total_test_count].
    # For example JSON output, see https://wpt.fyi/results?platform=chrome

    encoded_args = urlencode({
        'before': ('%s@latest' % product),
        'filter': 'C'  # Changes
    })
    url = 'https://20171213t152016-dot-wptdashboard.appspot.com/api/diff?' + \
          encoded_args
    # url = 'http://wpt.fyi/api/diff?' + encodedArgs

    body = json.dumps(results).encode('utf-8')
    headers = {
        'Content-type': 'application/json',
    }
    logging.debug("Fetching %s" % url)
    try:
        response = pool.request('POST', url, body=body, headers=headers)
    except urllib3.exceptions.SSLError as e:
        logging.warning('SSL error fetching %s: %s' % (url, e.message))
        return None

    if response.status != 200:
        logging.warning('Failed to fetch %s (%d):\n%s'
                       % (url, response.status, response.data.decode('utf-8')))
        return None

    logging.debug('Processing JSON from %s' % url)
    response_body = response.data.decode('utf-8')
    logging.debug(response_body)
    return json.loads(response_body)


def results_summary(job):  # type: (Job) -> Optional[dict]
    """Returns a dict of all the executed tests, and their summary
    pass counts, or None if no tests ran."""
    if not job.tests or len(job.tests) < 1:
        return None

    summary = {}
    results = filter(lambda x: not x.test.parent, job.tests)
    for result in results:  # type: JobResult
        if not result.consistent:
            continue

        test_path = result.test_id
        count = 0
        passes = 1 if is_pass(result) else 0
        subresults = lambda x: x.test.parent_id == result.test_id
        for subresult in filter(subresults, job.tests):  # type: JobResult
            if not subresult.consistent:
                continue

            passes += 1 if is_pass(subresult) else 0
            count = 1
        summary[test_path] = [passes, count]

    if len(summary) < 1:
        return None
    return summary


def is_pass(result):  # type: (models.JobResult) -> bool
    if not result.statuses or len(result.statuses) < 1:
        return False
    passing_statuses = [models.TestStatus.OK, models.TestStatus.PASS]
    return result.statuses[0].status in passing_statuses