=================
Parameter Manager
=================

.. image:: https://img.shields.io/github/workflow/status/epcpower/m-pm/CI/master?color=seagreen&logo=GitHub-Actions&logoColor=whitesmoke
   :alt: tests on GitHub Actions
   :target: https://github.com/epcpower/m-pm/actions?query=branch%3Amaster

.. image:: https://img.shields.io/github/last-commit/epcpower/m-pm/master.svg
   :alt: source on GitHub
   :target: https://github.com/epcpower/m-pm

.. image:: screenshot.png
   :alt: Parameter Manager screenshot

-------------------
Running From Binary
-------------------

Windows
=======

- Download artifact from the `build history on Github`_
- Extract contents of the ``.zip`` file
- Run ``mpm.exe``

A minimal sample project is available at ``src/mpm/tests/project/project.pmp``.

.. _`build history on Github`: https://github.com/epcpower/m-pm/actions

-------------------
Running From Source
-------------------

Windows
=======

- Install `Python 3.8`_
- Install `Poetry`_
- Install `Git`_
- ``git clone https://github.com/epcpower/m-pm``
- ``cd m-pm``
- ``git submodule update --init``
- ``poetry@1.5.1 install``
- ``poetry@1.5.1 run builduimpm``
- ``poetry@1.5.1 run builduiepyqlib``

To launch M-PM run ``poetry@1.5.1 run mpm``.

.. _`Python 3.8`: https://www.python.org/downloads/
.. _`Poetry`: https://python-poetry.org/docs/
.. _`Git`: https://git-scm.com/download

Linux
=====

- Install Python 3.8

  - pyenv_ to get Python versions

- Install git
- ``git clone https://github.com/epcpower/m-pm``
- ``cd m-pm``
- ``git submodule update --init``
- ``poetry@1.5.1 install``
- ``poetry@1.5.1 run builduimpm``
- ``poetry@1.5.1 run builduiepyqlib``

To launch M-PM run ``poetry@1.5.1 run mpm``

A minimal sample project is available at ``src/mpm/tests/project/project.pmp``.

.. _pyenv: https://github.com/pyenv/pyenv
