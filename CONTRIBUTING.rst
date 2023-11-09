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

We enforce commit messages to be formatted using the `Conventional Commits <https://www.conventionalcommits.org/>`_.

We have very precise rules over how our Git commit messages must be formatted.
This format leads to **easier to read commit history**.

Each commit message consists of a **header**, a **body**, and a **footer**.

.. code-block:: text

   <header>
   <BLANK LINE>
   <body>
   <BLANK LINE>
   <footer>


The `header` is mandatory and must conform to the `Commit Message Header`_ format.

The `body` is *optional* for all commits except for those of type "docs" for **main** branch only, else it is *optional*
When the body is present it must be at least 20 characters long and must conform to the `Commit Message Body`_ format.

The `footer` is optional. The `Commit Message Footer`_ format describes what the footer is used for and the structure it must have.


Commit Message Header
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   <type>(<scope>): <short summary>
   │       │             │
   │       │             └─⫸ Summary in present tense. Not capitalized. No period at the end.
   │       │
   │       └─⫸ Commit Scope: cli|io|report|store|packaging|changelog
   │
   └─⫸ Commit Type: build|ci|chore|doc|feat|fix|perf|refactor|test

The `<type>` and `<summary>` fields are mandatory, the `(<scope>)` field is optional.


Type
""""

Must be one of the following:

* **ci**: Changes to our CI configuration files and scripts (examples: GitHub actions)
* **chore**: Changes to the build process or auxiliary tools and libraries such as documentation generation
* **docs**: Documentation only changes
* **feat**: A new feature
* **fix**: A bug fix
* **perf**: A code change that improves performance
* **refactor**: A code change that neither fixes a bug nor adds a feature
* **test**: Adding missing tests or correcting existing tests


Scope
"""""

The scope should be the name of the npm package affected (as perceived by the person reading the changelog generated from commit messages).

The following is the list of supported scopes:

* `cli`
* `io`
* `report`
* `store`
* `templates`

There are currently a few exceptions to the "use package name" rule:

* `packaging`: used for changes that change the pyhton package layout in all of our packages, e.g. changes to bundles, etc.

* `changelog`: used for updating the release notes in CHANGELOG.md or its associated template file

Summary
"""""""

Use the summary field to provide a succinct description of the change:

* use the imperative, present tense: "change" not "changed" nor "changes"
* don't capitalize the first letter
* no dot (.) at the end


Commit Message Body
^^^^^^^^^^^^^^^^^^^

Just as in the summary, use the imperative, present tense: "fix" not "fixed" nor "fixes".

Explain the motivation for the change in the commit message body. This commit message should explain _why_ you are making the change.
You can include a comparison of the previous behavior with the new behavior in order to illustrate the impact of the change.


Commit Message Footer
^^^^^^^^^^^^^^^^^^^^^

The footer can contain information about breaking changes and deprecations and is also the place to reference GitHub issues, Jira tickets, and other PRs that this commit closes or is related to.
For example:

.. code-block:: text

   BREAKING CHANGE: <breaking change summary>
   <BLANK LINE>
   <breaking change description + migration instructions>
   <BLANK LINE>
   <BLANK LINE>
   Fixes #<issue number>

or

.. code-block:: text

   DEPRECATED: <what is deprecated>
   <BLANK LINE>
   <deprecation description + recommended update path>
   <BLANK LINE>
   <BLANK LINE>
   Closes #<pr number>

Breaking Change section should start with the phrase "BREAKING CHANGE: " followed by a summary of the breaking change, a blank line, and a detailed description of the breaking change that also includes migration instructions.

Similarly, a Deprecation section should start with "DEPRECATED: " followed by a short description of what is deprecated, a blank line, and a detailed description of the deprecation that also mentions the recommended update path.


Revert commits
^^^^^^^^^^^^^^

If the commit reverts a previous commit, it should begin with ``revert:``, followed by the header of the reverted commit.

The content of the commit message body should contain:

- information about the SHA of the commit being reverted in the following format: `This reverts commit <SHA>`,
- a clear description of the reason for reverting the commit message.


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
