Javascript Sandbox
==================

The Javascript sandbox worker runs Javascript code in a Node.js
instance. The provided Javascript code is run inside a thin wrapper
which handles sending and receiving sandbox commands.

People writing Javascript code for the sandbox are strongly encouraged
to use `vumi-jssandbox-toolkit`_ which provides a rich set of features
for interacting with the sandbox resources.

.. _vumi-jssandbox-toolkit: http://vumi-jssandox-toolkit.readthedocs.org/


Configuration options
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: vxsandbox.worker.JsSandboxConfig


Worker class
^^^^^^^^^^^^

.. autoclass:: vxsandbox.worker.JsSandbox
   :members:


Javascript sandbox resources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This special resource provides a means of sending the Javascript code
to be executed into the Node.js process. It is automatically included
by the Javascript sandbox worker.

.. autoclass:: vxsandbox.worker.JsSandboxResource
