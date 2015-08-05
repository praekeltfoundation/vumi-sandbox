# -*- test-case-name: vxsandbox.resources.tests.test_config -*-

"""A file-based configuration resource for Vumi's application sandbox."""

from .utils import SandboxResource


class FileConfigResource(SandboxResource):
    """
    Resource that provides access to a file-based configuration resource

    Configuration options:

    :param dict keys:
        A mapping between configuration keys and filenames
    """

    def handle_get(self, api, command):
        """
        Retrieve the value of a configuration specified by a key.

        Command fields:
            - ``key``: The key whose configuration should be retrieved.

        Reply:
            - The contents of the file specified by the configuration mapping
              for the given key.
        """
        key = command.get('key')
        filename = self.config.get('keys').get(key)
        if filename is None:
            return self.reply_error(
                command, reason='Configuration key %r not found' % (key,))
        try:
            with open(filename, 'r') as f:
                value = f.read()
            return self.reply(command, value=value, success=True)
        except EnvironmentError:
            return self.reply_error(
                command,
                reason='Cannot read file %r' % (filename,))
