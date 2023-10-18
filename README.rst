pdbstore
=============

.. image:: https://github.com/crabisoft/pdbstore/workflows/Test/badge.svg
   :target: https://github.com/crabisoft/pdbstore/actions

.. image:: https://badge.fury.io/py/pdbstore.svg
   :target: https://badge.fury.io/py/pdbstore

.. image:: https://readthedocs.org/projects/pdbstore/badge/?version=latest
   :target: https://pdbstore.readthedocs.org/en/latest/?badge=latest

.. image:: https://codecov.io/github/crabisoft/pdbstore/coverage.svg?branch=main
    :target: https://codecov.io/github/crabisoft/pdbstore?branch=main

.. image:: https://img.shields.io/pypi/pyversions/pdbstore.svg
   :target: https://pypi.python.org/pypi/pdbstore

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/python/black

.. image:: https://img.shields.io/github/license/crabisoft/pdbstore
   :target: https://github.com/crabisoft/pdbstore/blob/main/COPYING

``pdbstore`` is a Python package providing command-line utility to manage PDB symbol store.


Installation
------------

As of first version, ``pdbstore`` is compatible with Python 3.8+.

Use ``pip`` to install the latest stable version of ``pdbstore``:

.. code-block:: console

   $ pip install --upgrade pdbstore

The current development version is available on both `GitHub.com
<https://github.com/crabisoft/pdbstore>`__ and can be
installed directly from the git repository:

.. code-block:: console

   $ pip install git+https://github.com/crabisoft/pdbstore.git


Bug reports
-----------

Please report bugs and feature requests at
https://github.com/crabisoft/pdbstore/issues.


Documentation
-------------

The full documentation for CLI and API is available on `readthedocs
<http://pdbstore.readthedocs.org/en/stable/>`_.

Build the docs
~~~~~~~~~~~~~~

We use ``tox`` to manage our environment and build the documentation::

    pip install tox
    tox -e docs

Contributing
------------

For guidelines for contributing to ``pdbstore``, refer to `CONTRIBUTING.rst <https://github.com/crabisoft/pdbstore/blob/main/CONTRIBUTING.rst>`_.

