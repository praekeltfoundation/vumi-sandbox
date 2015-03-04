.. vxsandbox documentation master file, created by
   sphinx-quickstart on Wed Mar  4 20:45:06 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to vxsandbox's documentation!
=====================================

.. py:module:: vxsandbox

This library provides Vumi application workers that launch sandboxed
processes when messages are received.

Sandboxed processes communicate with the controlling worker via simple
JSON-formatted commands that are send and received over ``stdin`` and
``stdout``. Errors may be logged over ``stderr``.

Sandboxed processes are given access to additional functionality using
``resources``. Resources provide additional commands.

In addition to the generic sandbox worker, a custom Javascript sandbox
worker is provided that launches sandboxed Javascript code using
Node.js.

Contents
^^^^^^^^

.. toctree::
   :maxdepth: 2

   workers/index.rst
   resources/index.rst


Indices and tables
^^^^^^^^^^^^^^^^^^

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

