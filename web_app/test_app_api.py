import os
import sys
import unittest
from unittest.mock import Mock, patch

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import app as web_app


class WebAppAPITestCase(unittest.TestCase):
    def setUp(self):
        web_app.app.config['TESTING'] = True
        self.client = web_app.app.test_client()

    def test_python_tool_test_success(self):
        response = self.client.post('/api/python/tool-test', json={'product_name': '苹果手机'})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['category'], 'electronics')

    def test_python_tool_test_missing_name(self):
        response = self.client.post('/api/python/tool-test', json={})
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload['ok'])

    @patch('app.requests.get')
    def test_gateway_health_success(self, mock_get):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'ok'}
        mock_get.return_value = mock_response

        response = self.client.get('/api/gateway/health?gateway_url=http://127.0.0.1:8080')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['payload']['status'], 'ok')

    @patch('app.requests.get')
    def test_integration_test_gateway_fail(self, mock_get):
        mock_get.side_effect = web_app.requests.RequestException('connect failed')

        response = self.client.post('/api/integration/test', json={
            'gateway_url': 'http://127.0.0.1:8080',
            'product_name': '蓝月亮洗衣液',
        })
        self.assertEqual(response.status_code, 502)
        payload = response.get_json()
        self.assertFalse(payload['ok'])
        self.assertIn('error', payload['gateway'])
        self.assertEqual(payload['python_tool']['category'], 'electronics')


if __name__ == '__main__':
    unittest.main()
