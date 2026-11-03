import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from telegram_research.local_login import Login

class LocalLoginTests(unittest.TestCase):
    def test_private_credential_storage_and_no_echo(self):
        with TemporaryDirectory() as folder, patch('telegram_research.local_login.PRIVATE_DIR', Path(folder)), patch('telegram_research.local_login.credentials', side_effect=RuntimeError('missing')):
            login = Login()
            self.assertEqual(login.phase, 'credentials')
            value = 'a' * 32
            asyncio.run(login.submit({'api_id': '12345', 'api_hash': value}))
            self.assertEqual(login.phase, 'phone')
            path = Path(folder) / 'credentials.env'
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(value, login.page('testcsrf').decode())
            self.assertNotIn('12345', login.page('testcsrf').decode())

    def test_invalid_credential_does_not_echo_or_write(self):
        with TemporaryDirectory() as folder, patch('telegram_research.local_login.PRIVATE_DIR', Path(folder)), patch('telegram_research.local_login.credentials', side_effect=RuntimeError('missing')):
            login = Login()
            asyncio.run(login.submit({'api_id': 'sensitive-invalid-value', 'api_hash': 'secret'}))
            self.assertEqual(login.error, 'ValueError')
            self.assertFalse((Path(folder) / 'credentials.env').exists())
            self.assertNotIn('sensitive-invalid-value', login.page('csrf').decode())
