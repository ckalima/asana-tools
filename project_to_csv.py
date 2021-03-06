import argparse
import csv
import datetime
import dateutil.parser
import json
import os
import re
import sys

import asana

DEBUG = False
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y%m%d_%H%M'

# workspace specific tag IDs
TAGS = {'core': 28556938640340,
        'custom': 28556938640337,
       }

parser = argparse.ArgumentParser(description='This script generates a burndown chart from Asana tasks. The asana python module is required.')
parser.add_argument('-i', '--input', help='JSON file representing an Asana project. These can be generated by using the View As JSON feature in Asana.', required=False)
parser.add_argument('-k', '--key', help='Your Asana API key. Attempts to use ASANA_API_KEY environment variable by default.')
parser.add_argument('-p', '--projectid', help='Asana project id to pull tasks from.', required=False)
parser.add_argument('-s', '--start', help='Sprint start date in YYYY-MM-DD.', required=False)
parser.add_argument('-e', '--end', help='Sprint end date in YYYY-MM-DD.', required=False)
parser.add_argument('-d', '--debug', help='Enable Asana API debugging.', required=False)
args = parser.parse_args()


# time estimatation regex (e.g. [2:1.5], [estimated:actual])
pattern_estimate = '^\s*\[\s*(\?|\d+\.?\d*|\.?\d+)(?:[-:|/\s]+(\d*\.?\d*))?'
# iteration date pattern (e.g. 2014-03-01 - 2014-03-08, start date - end date)
pattern_dates = '\[(20\d{2}-\d{1,2}-\d{1,2})[-:|\s]+(20\d{2}-\d{1,2}-\d{1,2})\]'

# initialize counts
points_estimated, points_actual = 0, 0
points_core, points_custom = 0, 0
estimated_points_completed, actual_points_completed = 0, 0

# output setup
tasks_list, burndown = [], []
now = datetime.datetime.utcnow()
tasks_list_csv = 'project_task_%s.csv' % now.strftime(DATETIME_FORMAT)
burndown_csv = 'burndown_%s.csv' % now.strftime(DATETIME_FORMAT)
points_completed_by_date, points_completed_by_date_actual = {}, {}
tasks_list.append(['assignee', 'task', 'estimated', 'actual', 'created at', 'due on', 'completed at'])

if not args.input and not args.projectid:
    print "An input file or Asana project ID must be specified."
    sys.exit(2)

if args.debug:
    DEBUG = True

if not args.key:
    ASANA_API_KEY = os.environ.get('ASANA_API_KEY')
    if not ASANA_API_KEY:
        print "Please set ASANA_API_KEY in your environment or pass at execution using the -k flag."
        sys.exit(2)
else:
    ASANA_API_KEY = args.key

if args.input:
    f = json.load(open(args.input))
    tasks = f['data']
    if args.start:
        start = args.start
    else:
        start = raw_input("Sprint start date (YYYY-MM-DD): ")
    if args.end:
        end = args.end
    else:
        end = raw_input("Sprint end date (YYYY-MM-DD): ")
elif args.projectid:
    client = asana.Client.basic_auth(ASANA_API_KEY)
    asana_project = client.projects.find_by_id(int(args.projectid, 10))
    # update default file names
    tasks_list_csv = '%s_tasks_%s.csv' % (asana_project['id'], now.strftime(DATETIME_FORMAT))
    burndown_csv = '%s_burndown_%s.csv' % (asana_project['id'], now.strftime(DATETIME_FORMAT))
    # parse start and end dates
    match = re.search(pattern_dates, asana_project['name'])
    if match:
        start = match.group(1)
        end = match.group(2)
    else:
        start = raw_input("Sprint start date (YYYY-MM-DD): ")
        end = raw_input("Sprint end date (YYYY-MM-DD): ")
    # only a summary of tasks is returned by project query
    # for additional task details, need to query individual tasks
    print "Gathering tasks from '%s'\nhttps://app.asana.com/0/%s" % (asana_project['name'], args.projectid)
    tasks = []
    project_tasks = client.tasks.find_by_project(int(args.projectid, 10))
    for task in project_tasks:
        tasks.append(client.tasks.find_by_id(task['id']))

# convert start/end to datetime
start_date = dateutil.parser.parse(start)
end_date = dateutil.parser.parse(end)

# process asana tasks
for task in tasks:
    # task metadata
    name = task['name'].encode('ascii', 'replace')
    completed = task['completed']
    created_at = dateutil.parser.parse(task['created_at']).strftime(DATE_FORMAT)
    # check tags
    tags = task['tags']
    is_core = any(tag['id'] == TAGS['core'] for tag in tags)
    is_custom = any(tag['id'] == TAGS['custom'] for tag in tags)

    try:
        assignee = task['assignee']['name'].encode('ascii', 'replace')
    except TypeError:
        assignee = None
    # dates
    try:
        due_on = dateutil.parser.parse(task['due_on']).strftime(DATE_FORMAT)
    except AttributeError:
        due_on = None
    try:
        completed_at = dateutil.parser.parse(task['completed_at']).strftime(DATE_FORMAT)
    except AttributeError:
        completed_at = None

    # time estimation
    match = re.search(pattern_estimate, name)
    estimated, actual = 0, 0
    if match:
        if match.group(1) == '?': # unknown
            estimated = 0.0
        else:
            estimated = float(match.group(1))
        if completed:
            actual = float(match.group(2) or estimated)
        else:
            actual = float(match.group(2) or 0.0)
    if completed:
        estimated_points_completed += estimated
        actual_points_completed += actual
        # estimated points
        if points_completed_by_date.get(completed_at):
            points_completed_by_date[completed_at] += estimated
        else:
            points_completed_by_date[completed_at] = estimated

        # actual points
        if points_completed_by_date_actual.get(completed_at):
            points_completed_by_date_actual[completed_at] += actual
        else:
            points_completed_by_date_actual[completed_at] = actual

    # update totals
    points_estimated += float(estimated)
    points_actual += float(actual)

    if is_core:
        points_core += float(actual)

    if is_custom:
        points_custom += float(actual)

    tasks_list.append([assignee, name, estimated, actual, created_at, due_on, completed_at])

# stats
completed_percentage = round((float(estimated_points_completed) / points_estimated) * 100.0, 2)
percentage_core = round((float(points_core) / points_actual) * 100.0, 2)
percentage_custom = round((float(points_custom) / points_actual) * 100.0, 2)
points_product = points_core + points_custom
percentage_product = percentage_core + percentage_custom

# dump task list to csv
with open(tasks_list_csv, 'w') as fp:
    a = csv.writer(fp, delimiter=',')
    a.writerows(tasks_list)

# compute burndown
day_before_start = start_date - datetime.timedelta(days=1)
days = (end_date - start_date).days
points_remaining = points_estimated
points_remaining_actual = points_estimated
current_date = start_date
days_remaining = days
avg_points_per_day = points_estimated / days

burndown.append(['date', 'estimated', 'actual', 'ideal'])
while current_date <= end_date:
    # estimated
    points_on_day = (points_completed_by_date.get(current_date.strftime(DATE_FORMAT)) or 0)
    points_remaining -= points_on_day
    # actual
    points_on_day_actual = (points_completed_by_date_actual.get(current_date.strftime(DATE_FORMAT)) or 0)
    points_remaining_actual -= points_on_day_actual
    # linear
    if days_remaining == days:
        linear_burn = points_estimated
    else:
        linear_burn = days_remaining * avg_points_per_day

    if current_date <= datetime.datetime.today():
        burndown.append([current_date.strftime(DATE_FORMAT), points_remaining, points_remaining_actual, linear_burn])
    else:
        burndown.append([current_date.strftime(DATE_FORMAT), None, None, linear_burn])

    days_remaining -= 1
    current_date += datetime.timedelta(days=1)
with open(burndown_csv, 'w') as fp:
    a = csv.writer(fp, delimiter=',')
    a.writerows(burndown)

print "Sprint from %s to %s (%s days)" % (start, end, days)
print "Estimated: %s" % points_estimated
print "Actual: %s" % points_actual
print "Completed [Estimated]: %s (%s%%)" % (estimated_points_completed, completed_percentage)
print "Completed [Actual]: %s" % actual_points_completed
print "Actual points on Core: %s (%s%%)" % (points_core, percentage_core)
print "Actual points on Custom: %s (%s%%)" % (points_custom, percentage_custom)
print "Actual points on Product: %s (%s%%)" % (points_product, percentage_product)
