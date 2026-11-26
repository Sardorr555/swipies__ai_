"""Regression tests for fail-closed delivery and encrypted channel credentials."""
import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import requests

from api.db.services.codeexec_service import attachment
from api.db.services.telegram_delivery_service import deliver, authorized_channel
from api.utils.key_crypto import encrypt_connector_config, decrypt_connector_config

class CodeExecPlatformTests(unittest.TestCase):
    def setUp(self):
        self.uri='data:text/plain;base64,'+base64.b64encode(b'TEST ONLY').decode()
        self.config=encrypt_connector_config({'credential':{'token':'unit-test-placeholder'}})
        self.channel=SimpleNamespace(config=self.config,tenant_id='owner',channel='telegram')
        self.spec={'attachment':self.uri,'caption':'TEST ONLY, manual review','filename':'test.txt','kind':'document'}
    def response(self,status,data):
        return SimpleNamespace(status_code=status,json=lambda:data)
    def test_valid_data_uri(self):
        raw,name,mime=attachment(self.uri,'../../test.txt')
        self.assertEqual((raw,name,mime),(b'TEST ONLY','test.txt','text/plain'))
    def test_invalid_base64(self):
        with self.assertRaises(ValueError): attachment('data:image/png;base64,NOT VALID')
    def test_remote_attachment_not_fetched(self):
        with self.assertRaises(ValueError): attachment('http://169.254.169.254/credentials')
    def test_oversized_attachment(self):
        with self.assertRaises(ValueError): attachment('data:text/plain;base64,'+'A'*(14*1024*1024+1))
    def test_secret_encrypted_at_rest(self):
        self.assertTrue(self.config['credential']['token'].startswith('enc:v2:'))
        self.assertNotIn('unit-test-placeholder',json.dumps(self.config))
        self.assertEqual(decrypt_connector_config(self.config)['credential']['token'],'unit-test-placeholder')
    def test_success_requires_message_id(self):
        send=Mock(return_value=self.response(200,{'ok':True,'result':{}}))
        self.assertFalse(deliver(self.channel,'1',self.spec,send)['ok'])
    def test_telegram_false_does_not_succeed(self):
        send=Mock(return_value=self.response(200,{'ok':False,'result':{'message_id':99}}))
        self.assertFalse(deliver(self.channel,'1',self.spec,send)['ok'])
    def test_timeout_does_not_confirm(self):
        send=Mock(side_effect=requests.Timeout())
        result=deliver(self.channel,'1',self.spec,send)
        self.assertFalse(result['ok']); self.assertEqual(result['delivery_status'],'unknown')
    def test_redirect_does_not_follow_or_confirm(self):
        send=Mock(return_value=self.response(302,{}))
        self.assertFalse(deliver(self.channel,'1',self.spec,send)['ok'])
        self.assertIs(send.call_args.kwargs['allow_redirects'],False)
    def test_multipart_and_manual_review(self):
        send=Mock(return_value=self.response(200,{'ok':True,'result':{'message_id':99}}))
        result=deliver(self.channel,'1',self.spec,send)
        self.assertEqual(result,{'ok':True,'message_id':99,'payment_status':'pending_manual_review'})
        self.assertEqual(send.call_args.kwargs['files']['document'][1],b'TEST ONLY')
        self.assertNotIn('token',json.dumps(result))
    def test_invalid_attachment_never_sends(self):
        send=Mock()
        self.assertFalse(deliver(self.channel,'1',{**self.spec,'attachment':''},send)['ok'])
        send.assert_not_called()
    def test_foreign_channel_never_resolves_credential(self):
        with patch('api.db.services.chat_channel_service.ChatChannelService.get_by_id',return_value=(True,self.channel)):
            with self.assertRaises(PermissionError): authorized_channel('attacker','channel')
    def test_channel_insert_encrypts_credential(self):
        from api.db.services.chat_channel_service import ChatChannelService
        with patch('api.db.services.common_service.CommonService.insert',return_value=True) as write:
            ChatChannelService.insert(config={'credential':{'token':'unit-test-placeholder'}})
            self.assertTrue(write.call_args.kwargs['config']['credential']['token'].startswith('enc:v2:'))

if __name__=='__main__': unittest.main()
