pdbstore
=============

|Test| |PyPI| |Read the Docs| |Coverage| |Python| |Code Style| |Pre-Commit| |License|

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


.. |Test| image:: https://github.com/crabisoft/pdbstore/workflows/Test/badge.svg
   :target: https://github.com/crabisoft/pdbstore/actions
   :alt: Test

.. |PyPI| image:: https://img.shields.io/pypi/v/pdbstore?label=PyPI&logo=pypi
   :target: https://badge.fury.io/py/pdbstore
   :alt: PyPI

.. |Conda| image:: https://img.shields.io/conda/v/conda-forge/pdbstore?label=Conda
   :target: https://anaconda.org/conda-forge/pdbstore
   :alt: Conda

.. |Read the Docs| image:: https://img.shields.io/readthedocs/pdbstore?label=Read%20the%20Docs&logo=Read%20the%20Docs
   :target: https://pdbstore.readthedocs.org/en/latest
   :alt: Docs

.. |Coverage| image:: https://img.shields.io/codecov/c/github/crabisoft/pdbstore?logo=Codecov&label=Coverage
   :target: https://codecov.io/github/crabisoft/pdbstore?branch=main
   :alt: Cover

.. |Python| image:: https://img.shields.io/pypi/pyversions/pdbstore.svg?label=Python&logo=Python
   :target: https://pypi.python.org/pypi/pdbstore
   :alt: Python

.. |Code Style| image:: https://img.shields.io/badge/code%20style-black-000000.svg?label=Code%20Style
   :target: https://github.com/python/black
   :alt: Code Style

.. |Pre-Commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&label=Pre-Commit
   :target: https://github.com/pre-commit/pre-commit
   :alt: Pre-Commit

.. |License| image:: https://img.shields.io/github/license/crabisoft/pdbstore?label=License
   :target: https://github.com/crabisoft/pdbstore/blob/main/COPYING
   :alt: License
