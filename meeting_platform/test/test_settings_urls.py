#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Tests for settings/prod.py and urls.py to cover configuration changes.

Covers:
- prod.py lines 205, 209-210, 215, 217, 286
- urls.py line 47
"""
import os
import tempfile
import unittest
from unittest import mock
import yaml

from django.test.utils import override_settings


class TestProdSettings(unittest.TestCase):
    """Test prod.py settings configuration lines."""

    def test_prod_settings_static_root_line(self):
        """Test prod.py STATIC_ROOT assignment (line 205)."""
        # Create mock config files
        config_content = {
            'DEBUG': False,
            'IS_DELETE_CONFIG': False,
            'COMMUNITY_SUPPORT': ['openEuler'],
            'MYSQL_TLS_PEM_PATH': '/tmp/tls.pem',
            'UWSGI_TLS_CRT_PATH': None,
            'UWSGI_TLS_KEY_PATH': None,
            'KAFKA_CRT_PATH': None,
            'TEMPLATE': {},
            'API_PREFIX': {},
            'COMMUNITY_PORTAL': {},
            'COMMUNITY_PRIVATE_MEETING_EMAIL_SUFFIX': {},
            'IS_UPLOAD_BILI': False,
            'IS_UPLOAD_OBS': False,
            'CRONJOB_FORCE_END_MEETING': False,
        }

        vault_content = {
            'SECRET_KEY': 'test-secret-key-for-coverage',
            'DB': {
                'NAME': 'test_db',
                'USER': 'test_user',
                'PASSWORD': 'test_pass',
                'HOST': 'localhost',
                'PORT': '3306',
            },
            'COMMUNITY_ZOOM_OBS': {},
            'COMMUNITY_HOST': {},
            'COMMUNITY_SMTP': {},
            'COMMUNITY_KAFKA': {},
            'COMMUNITY_OBS': {},
            'COMMUNITY_BILI': {},
            'COMMUNITY_AUDIT': {},
            'COMMUNITY_TRANSLATE': {},
            'HANDLE_MEETING_SCHEDULE_PLAN': 'windows',
            'FORCE_MEETING_END_TIME': 30,  # Line 286
        }

        # Create temporary config files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            yaml.dump(config_content, config_file)
            config_path = config_file.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as vault_file:
            yaml.dump(vault_content, vault_file)
            vault_path = vault_file.name

        # Create empty TLS PEM file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as tls_file:
            tls_file.write('')
            tls_path = tls_file.name

        try:
            # Update config with actual TLS path
            config_content['MYSQL_TLS_PEM_PATH'] = tls_path
            with open(config_path, 'w') as f:
                yaml.dump(config_content, f)

            # Mock environment variables
            env_mock = {
                'CONFIG_PATH': config_path,
                'VAULT_PATH': vault_path,
            }

            with mock.patch.dict(os.environ, env_mock, clear=True):
                # Import prod.py - this executes all the assignment lines
                # Lines 205, 215, 217, 286 are executed during import
                import importlib
                import meeting_platform.settings.prod as prod_settings

                # Force reimport to get coverage
                importlib.reload(prod_settings)

                # Verify settings values exist (proves lines were executed)
                self.assertEqual(prod_settings.STATIC_ROOT, os.path.join(os.path.dirname(prod_settings.BASE_DIR), 'static'))
                self.assertEqual(prod_settings.LOGIN_URL, '/admin/login/')
                self.assertEqual(prod_settings.DEFAULT_AUTO_FIELD, 'django.db.models.AutoField')
                self.assertEqual(prod_settings.FORCE_MEETING_END_TIME, 30)

        finally:
            # Cleanup temporary files
            os.unlink(config_path)
            os.unlink(vault_path)
            os.unlink(tls_path)

    def test_prod_settings_force_meeting_end_time_default(self):
        """Test prod.py FORCE_MEETING_END_TIME default value (line 286)."""
        config_content = {
            'DEBUG': False,
            'IS_DELETE_CONFIG': False,
            'COMMUNITY_SUPPORT': ['openEuler'],
            'MYSQL_TLS_PEM_PATH': '/tmp/tls.pem',
            'UWSGI_TLS_CRT_PATH': None,
            'UWSGI_TLS_KEY_PATH': None,
            'KAFKA_CRT_PATH': None,
            'TEMPLATE': {},
            'API_PREFIX': {},
            'COMMUNITY_PORTAL': {},
            'COMMUNITY_PRIVATE_MEETING_EMAIL_SUFFIX': {},
            'IS_UPLOAD_BILI': False,
            'IS_UPLOAD_OBS': False,
            'CRONJOB_FORCE_END_MEETING': False,
        }

        vault_content = {
            'SECRET_KEY': 'test-secret-key',
            'DB': {
                'NAME': 'test_db',
                'USER': 'test_user',
                'PASSWORD': 'test_pass',
                'HOST': 'localhost',
                'PORT': '3306',
            },
            'COMMUNITY_ZOOM_OBS': {},
            'COMMUNITY_HOST': {},
            'COMMUNITY_SMTP': {},
            'COMMUNITY_KAFKA': {},
            'COMMUNITY_OBS': {},
            'COMMUNITY_BILI': {},
            'COMMUNITY_AUDIT': {},
            'COMMUNITY_TRANSLATE': {},
            'HANDLE_MEETING_SCHEDULE_PLAN': 'windows',
            # No FORCE_MEETING_END_TIME - tests default value
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            yaml.dump(config_content, config_file)
            config_path = config_file.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as vault_file:
            yaml.dump(vault_content, vault_file)
            vault_path = vault_file.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as tls_file:
            tls_file.write('')
            tls_path = tls_file.name

        try:
            config_content['MYSQL_TLS_PEM_PATH'] = tls_path
            with open(config_path, 'w') as f:
                yaml.dump(config_content, f)

            env_mock = {
                'CONFIG_PATH': config_path,
                'VAULT_PATH': vault_path,
            }

            with mock.patch.dict(os.environ, env_mock, clear=True):
                import importlib
                import meeting_platform.settings.prod as prod_settings
                importlib.reload(prod_settings)

                # Default value should be 30 (from VAULT_CONF.get("FORCE_MEETING_END_TIME", 30))
                self.assertEqual(prod_settings.FORCE_MEETING_END_TIME, 30)

        finally:
            os.unlink(config_path)
            os.unlink(vault_path)
            os.unlink(tls_path)


class TestUrlsCoverage(unittest.TestCase):
    """Test urls.py to cover line 47 - static files URL pattern."""

    @override_settings(DEBUG=True, STATIC_ROOT='/tmp/static', STATIC_URL='/static/')
    def test_urls_static_in_debug_mode(self):
        """Test urls.py static() extension in DEBUG mode (line 47).

        Note: We use override_settings to ensure DEBUG=True for this test.
        Force a reload of urls.py to capture coverage for the DEBUG block.
        """
        from django.conf import settings

        # Verify our override settings are in effect
        self.assertTrue(settings.DEBUG)

        # Force reload urls.py to capture coverage with DEBUG=True
        import importlib
        import meeting_platform.urls as urls_module
        importlib.reload(urls_module)

        # Verify urlpatterns exist and contain patterns
        self.assertTrue(len(urls_module.urlpatterns) > 0)
        self.assertIsNotNone(urls_module.urlpatterns)