# Cash Assistance Platform (CAP)

## Overview

The Cash Assistance Platform (CAP) is a software platform built to support the
distribution of cash funds. The platform takes an opinionated approach to use
voucher codes as means to distribute cash in a scalable and decentralized way.
An applicant who receives a code can proceed to fill out a form that is then
approved in a staff portal by the administrator.

The diagram below illustrates the typical process of distributing funds. The
blue boxes reflect where CAP is used as part of the flow. Keep in mind that to
run a successful cash assistance program, engineering along with operations and
customer service is critical. You can read more about this in
[research we did with New America](https://www.newamerica.org/public-interest-technology/reports/establishing-emergency-cash-assistance-funds/).

![image](https://user-images.githubusercontent.com/25941287/94732111-acea4780-031a-11eb-9f47-7dfdd80be0f9.png)

### History

CAP was built to support the distribution of cash funds to those in need during
the COVID-19 pandemic. The Google.org fellowship team collaborated with NDWA to
develop a system that would quickly distribute money to domestic workers across
the country. The platform internally was known as the CCF (Coronavirus Care
Fund). You will see the acronym CCF throughout the codebase.

## Documentation

This `README` covers developer setup necessary to run the code locally. For a
detailed overview of supported features and instructions on forking & deploying
the code, visit the
[Wiki](https://github.com/ndwa/cash-assistance-platform/wiki) for this repo.

## Development

If you are contributing to this repository regularly for an extended period of
time,
[request GitHub collaborator access](https://github.com/ndwa/cash-assistance-platform/issues/new)
to commit directly to the main repository. If you are contributing on occasion,
[fork this repository](https://github.com/ndwa/cash-assistance-platform/fork)
before making any commits.

### Environment Setup

CAP is a [Django](https://www.djangoproject.com/start/) web application that
uses a PostgreSQL database. This section will walk through the installation and
setup needed to run CAP on your local machine. Instructions are catered toward
Mac users.

#### 1. Install Python + Setup a Virtual Environment

On a Mac with [Homebrew](https://brew.sh/), you can install `python3.7`,
`libpq`, and `openssl` with:

```
$ brew install python3 postgresql openssl
```

You will also need a Python virtual environment. Our recommendation is
[`virtualenvwrapper`](https://virtualenvwrapper.readthedocs.io/en/latest/). See
the `virtualenvwrapper` docs for
[installation & setup](https://virtualenvwrapper.readthedocs.io/en/latest/install.html).

After installing `virtualenvwrapper`, create and activate your virtual
environment (replace `myenv` with desired environment name):

```
$ mkvirtualenv myenv -p python3.7
$ workon myenv
```

#### 2. Fork the Code

[Fork this repository](https://github.com/ndwa/cash-assistance-platform/fork),
clone it locally, and enter the directory:

```
$ git clone git@github.com:your_github_username/cash-assistance-platform.git
$ cd django-ccf
```

#### 3. Install dependencies

With your virtual environment activated (see Step 1), install the Python
requirements for the Django project.

```
$ pip install -r requirements.txt
```

#### 4. Setup environment variables

To add the repo to your Python path, run the following command. **Tip**:
`path_to_source` should end in `django-ccf/`.

```
$ add2virtualenv path_to_source
```

Include the rest of the required environment variables in the
[postactivate](https://virtualenvwrapper.readthedocs.io/en/latest/scripts.html#postactivate)
script of your virtual environment (found in `$VIRTUAL_ENV/bin/postactivate`) by
copy/pasting the below code snippet, updating `DJANGO_SECRET_KEY` as described
below, and

```
# Django
export DJANGO_DEBUG=True
export DJANGO_SETTINGS_MODULE="ccf.settings"
export DJANGO_SECRET_KEY=  # Run the code snippet below to generate a unique value
export SECURE_COOKIE=False

# AWS RDS - Leave blank for local development!
export RDS_HOSTNAME=
export RDS_PORT=
export RDS_DB_NAME=
export RDS_USERNAME=
export RDS_PASSWORD=

# USPS verification - Required
export USPS_USER_ID=  # [Free USPS Registration URL](https://registration.shippingapis.com/) - API key will be emailed

# Twilio - Optional variables to support text messaging with a Twilio account
# export TWILIO_SMS_SENDER=
# export TWILIO_ACCOUNT_SID=
# export TWILIO_AUTH_TOKEN=
# export TWILIO_SERVICE_SID=
```

For the `DJANGO_SECRET_KEY`, run the following line to generate a unique value:

```
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

#### 5. Create log files

CAP expects the following log files: `/var/log/ccf/ccf.log` and
`/var/log/ccf/info.log`. To create them, run:

```
sudo mkdir -p /var/app/log/
sudo chown `whoami` /var/app/log/
touch /var/app/log/ccf.log
touch /var/app/log/info.log
```

#### 6. Install PostgreSQL

Install `postgres` and create a local PostgreSQL db:

```
$ brew install postgresql
$ brew services start postgresql
$ psql postgres
psql (12.3)
Type "help" for help.

postgres=# CREATE DATABASE myproject;
postgres=# CREATE USER myprojectuser WITH PASSWORD 'password';
postgres=# ALTER USER myprojectuser CREATEDB;
postgres=# ALTER ROLE myprojectuser SUPERUSER;
postgres=# \q
```

On linux, you can follow the instructions
[here](https://www.digitalocean.com/community/tutorials/how-to-use-postgresql-with-your-django-application-on-ubuntu-14-04)
(stop before “Install Django within a Virtual Environment”).

**Important**: You must use the specified names (`myproject`, `myprojectuser`,
`password`) as these are used specifically in `ccf/settings.py`, or else
reconfigure the settings file to your specification.

```
$ ./manage.py makemigrations # should do nothing
$ ./manage.py migrate
```

#### 7. Compile messages for translations

```
$ ./manage.py compilemessages
```

**Tip**: you may have to install `gettext` first.

```
$ brew install gettext
```

#### 8. Create a staff user

Create a Django super user with the following command. These credentials will
allow you to access the Staff Portal.

```
$ ./manage.py createsuperuser
```

### Running the server

Use `inv run` or `./manage.py runserver` to start up the application locally.

Visit `localhost:8000` in a browser to access the Applicant Form, and
`localhost:8000/staff` to access the Staff Portal, where you can generate
voucher codes necessary to complete the form (see detailed instructions in the
[Wiki](https://github.com/ndwa/cash-assistance-platform/wiki)).

### Running the tests

To run the Django unit tests, run `./manage.py test`.

**Tip**: You may first need to compile messages (`./manage.py compilemessages`)
and collect static files (`./manage.py collectstatic`)
