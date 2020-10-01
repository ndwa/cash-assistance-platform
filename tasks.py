# tasks.py
# See COPYRIGHT and LICENSE for details.

import os
from invoke import task

# TODO: review the need for these tasks and update if more useful tasks are needed.

@task(
    help={
        'app_label': "Specify the app label(s) to create migrations for.",
    }
)
def migrations(c, app_label):
    """
    Creates new migration(s) for a given app.
    """
    c.run('python manage.py makemigrations {0}'.format(app_label,),
          pty=True)


@task
def migrate(c):
    c.run('python manage.py migrate', pty=True)


@task
def run(c):
    c.run('python manage.py runserver', pty=True)


@task
def sass(c):
    c.run('sass alia/scss/_alia.scss alia/static/alia/css/alia.css', pty=True)


# TESTS
APPS_TO_TEST = [
]


def _test_app(c, app_label):
    print("TESTING APP:", app_label)
    c.run('python manage.py test {0}'.format(app_label,),
          pty=True,
          warn=True,
          )
    print()


@task
def unit_tests(c):
    for app in APPS_TO_TEST:
        _test_app(c, app)


@task
def functional_tests(c):
    print("RUNNING FUNCTIONAL TESTS.")
    c.run('python manage.py test', pty=True, warn=True)


@task(pre=[unit_tests, functional_tests])
def tests(c):
    print("Done.")

