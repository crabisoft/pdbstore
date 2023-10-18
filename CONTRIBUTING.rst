Contributing
=============

You can contribute to the project in multiple ways:

* Fix bugs
* Add unit and functional tests
* Everything else you can think of

--------------------

Before contributing, install `tox <https://tox.wiki/>`_ and `pre-commit <https://pre-commit.com>`_.

It is strongly recommended to have a global installation for **tox** and **pre-commit**, but it is also 
possible to use a virtual environment.

Before contributing, please make sure you have `pre-commit <https://pre-commit.com>`_
installed and configured. This will help automate adhering to code style and commit
message guidelines described below:

.. code-block:: bash
  :caption: Global user installation

  cd pdbstore/
  pip3 install --user pre-commit tox
  pre-commit install -t pre-commit -t commit-msg --install-hooks

.. code-block:: bash
  :caption: Using venv

  cd pdbstore/
  make setup-venv && source .venv/bin/activate
  pip3 install --user pre-commit tox
  pre-commit install -t pre-commit -t commit-msg --install-hooks


Please provide your patches as GitHub pull requests. Thanks!

Commit message guidelines
-------------------------

We enforce commit messages to be formatted using the `conventional-changelog <https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit>`_.
This leads to more readable messages that are easy to follow when looking through the project history.

Code-Style
----------

We use black as code formatter, so you'll need to format your changes using the
`black code formatter
<https://github.com/python/black>`_. Pre-commit hooks will validate/format your code
when committing. You can then stage any changes ``black`` added if the commit failed.

To format your code according to our guidelines before committing, run:

.. code-block:: bash

  cd pdbstore/
  pip3 install --user black
  black .

or you can use make to run **black** using **tox**

.. code-block:: bash

  cd pdbstore/
  make setup-env
  source .venv/scripts/activate
  make black

Running unit tests
------------------

Before submitting a pull request make sure that the tests and lint checks still succeed with
your change. Unit tests and functional tests run in GitHub Actions and
passing checks are mandatory to get merge requests accepted.

Please write new unit tests with pytest.

You need to install ``tox`` using one of the following approach:

* ``pip3 install --user tox`` to install as user packages from global python installation:
* ``make setup-env && source .venv/bin/activate`` to create and activate a local virtual environment


.. code-block:: bash

   # run unit tests using your installed python3, and all lint checks:
   tox -s

   # run unit tests for all supported python3 versions, and all lint checks:
   tox

   # run tests in one environment only:
   tox -epy38

   # build the documentation, the result will be generated in
   # doc/_build/sphinx/html/
   tox -edoc

Running integration tests
-------------------------

Integration tests run against a local symbol store. 

To run these tests:

.. code-block:: bash

   # run the CLI tests:
   tox -e cli


Releases
--------

The release workflow can be run manually by maintainers to publish urgent
fixes, either on GitHub or using the ``gh`` CLI with ``gh workflow run release.yml``.

**Note:** As a maintainer, this means you should carefully review commit messages
used by contributors in their pull requests. If scopes such as ``fix`` and ``feat``
are applied to trivial commits not relevant to end users, it's best to squash their
pull requests and summarize the addition in a single conventional commit.
This avoids triggering incorrect version bumps and releases without functional changes.

The release workflow uses `python-semantic-release
<https://python-semantic-release.readthedocs.io>`_ and does the following:

* Bumps the version in ``_version.py`` and adds an entry in ``CHANGELOG.md``,
* Commits and tags the changes, then pushes to the master branch as the ``github-actions`` user,
* Creates a release from the tag and adds the changelog entry to the release notes,
* Uploads the package as assets to the GitHub release,
* Uploads the package to PyPI.
