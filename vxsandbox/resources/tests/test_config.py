from twisted.internet.defer import inlineCallbacks

from vxsandbox.resources.config import FileConfigResource
from vxsandbox.resources.tests.utils import ResourceTestCaseBase


class TestFileConfigResource(ResourceTestCaseBase):

    resource_cls = FileConfigResource

    def create_config_file(self, content):
        filename = self.mktemp()
        with open(filename, 'w') as f:
            f.write(content)
        return filename

    def create_resource(self, **file_mapping):
        config = {
            'keys': file_mapping
        }
        return super(TestFileConfigResource, self).create_resource(config)

    @inlineCallbacks
    def test_get_config(self):
        test_content = 'Test content'
        config_file = self.create_config_file(test_content)
        self.create_resource(config=config_file)
        reply = yield self.dispatch_command('get', key='config')
        self.check_reply(reply, success=True, value=test_content)

    @inlineCallbacks
    def test_get_config_non_existing_file(self):
        self.create_resource(config='foobar')
        reply = yield self.dispatch_command('get', key='config')
        self.check_reply(reply, success=False)
        self.assertTrue('foobar' in reply['reason'])
        self.assertTrue('Cannot read file' in reply['reason'])

    @inlineCallbacks
    def test_get_config_non_existing_key(self):
        self.create_resource()
        reply = yield self.dispatch_command('get', key='bar')
        self.check_reply(reply, success=False)
        self.assertTrue('bar' in reply['reason'])
        self.assertTrue('not found' in reply['reason'])
