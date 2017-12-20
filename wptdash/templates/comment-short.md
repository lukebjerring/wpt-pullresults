# Build {{ build.status.name }}

Started: {{ build.started_at }}
Finished: {{ build.finished_at }}

> This report has been truncated because the number of unstable tests exceeds GitHub.com's character limit for comments ({{characters}} characters).

{% if failing_jobs|length %}
<h2>Failing Jobs</h2>
<ul>
{% for job_name in failing_jobs %}
<li>{{ job_name }}</li>
{% endfor %}
</ul>
{% endif %}

{% if regressed_jobs|length %}
<h2>Changed Jobs</h2>
<ul>
{% for job_name in regressed_jobs %}
<li>{{ job_name }}</li>
{% endfor %}
</ul>
{% endif %}

{% if has_unstable %}
<h2>Unstable Browsers</h2>
  {% for job in build.jobs|sort(attribute='id') %}
  {% set inconsistent_tests = job.tests|selectattr("consistent", "sameas", false)|list %}
  {% if inconsistent_tests|length %}
  <h3>Browser: "{{ job.product.name|replace(':', ' ')|title }}"<small>{{' (failures allowed)' if job.allow_failure else ''}}</small></h3>
  <p>View in: <a href="http://{{app_domain}}/job/{{job.number}}">WPT PR Status</a> |
      <a href="https://travis-ci.org/{{org_name}}/{{repo_name}}/jobs/{{job.id}}">TravisCI</a></p>
  {% endif %}
  {% endfor %}
{% else %}

View more information about this build on:

- [WPT PR Status](http://{{app_domain}}/build/{{build.number}})
- [TravisCI](https://travis-ci.org/{{org_name}}/{{repo_name}}/builds/{{build.id}})

{% endif %}
