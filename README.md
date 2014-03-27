asana-tools
===========

Some helpful Asana scripts.

### Requirements

[Asana API python wrapper](https://github.com/pandemicsyn/asana/)

`pip install asana`

### project_to_csv.py

Generates task and burndown .csv files that can be imported into spreadsheet software for sprint tracking and analysis. A specific syntax should be used in your Asana project and task names to enable time estimation and date ranges.

**Setup**

This script uses the Asana API to dynamically access your project. It will look for your API key in the **ASANA_API_KEY** environment variable. You can also pass it in at runtime using the -k flag:

`python project_to_csv.py -p 1000 -k YOUR_API_KEY`

Read the [Asana API Keys documentation](http://developer.asana.com/documentation/#api_keys) for more information, including where to find your key.

**Usage**

You must pass a project ID using the -p flag when running the script.

You can locate a project's ID by selecting the project in the left sidebar of Asana. Once clicked, the project name text field will gain focus, and the URL will update to something like **https://app.asana.com/0/123456789/123456789**, where the project ID is **123456789**.

As you select tasks within a project, the URL will update to maintain the following form **https://app.asana.com/0/PROJECT_ID/TASK_ID**. Knowing this, you can also extract the project ID while viewing any task within a project.

Once you have the project ID of interest, running the script is easy:

`python project_to_csv.py -p 123456789`

**Project Name**

The script assumes sprints are broken down into discrete projects, and parses the project name to determine the start and end dates. To be successful, the project name should look something like the following, with the start date first, followed by the end date, both in YYYY-MM-DD format:

`Iteration 21 [2014-03-25 - 2014-04-01]`

**Task Name**

To track story points, estimates must be included in the individual task names. A task with an estimated value of 50 would look like this:

`[50] enable purchase without being logged in`

If you are tracking time instead of points, you can also add an _actual_ value to the task if the time spent is greater or less than that estimated. Continuing with the example above, if the task took 60 units to complete, I would represent that as follows:

`[50:60] enable purchase without being logged in`

The pattern is [estimated:actual]. If no actual time is given, it is assumed the estimated time was taken.

It's generally bad form to add tasks during a sprint, but if you must, it is recommended that an estimated time of 0 is used to protect the estimates established at the start of the sprint. If the task is completed, it is also a recommended to use the actual value to represent the effort required. Below is an example task that was not present in sprint planning and required 30 units to complete:

`[0:30] fix issue with user avatars`

### todo

* generate burndown plots
* create automated web dashboard
