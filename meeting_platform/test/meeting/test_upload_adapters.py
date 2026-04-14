#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for upload adapter implementations.

Tests include:
- BiliUploadAdapterImpl: upload returns replay URL/bvid, add_video
- ObsUploadAdapterImpl: path generation, metadata generation, upload
"""
import datetime
import os
import tempfile
from unittest import mock

from meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl import BiliUploadAdapterImpl
from meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl import ObsUploadAdapterImpl
from meeting_platform.test.meeting.test_base import TestCommonMeeting


class BiliUploadAdapterImplTest(TestCommonMeeting):
    """Test BiliUploadAdapterImpl."""

    def setUp(self):
        super().setUp()
        self.meeting = {
            "community": "openEuler",
            "mid": "test_mid_123",
            "date": "2026-04-15",
            "group_name": "test_group",
            "topic": "Test Meeting",
            "sponsor": "test_sponsor",
            "agenda": "Test Agenda",
            "start": "10:00",
            "end": "11:00",
        }

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl.BiliAdapterImpl')
    def test_upload_returns_replay_url(self, mock_bili_adapter):
        """Test upload returns replay URL when return_replay_url=True."""
        # Mock upload result
        mock_bili_adapter_instance = mock.MagicMock()
        mock_bili_adapter_instance.upload.return_value = {'bvid': 'BV123456'}
        mock_bili_adapter_instance.get_replay_url.return_value = 'https://replay.bili.com/BV123456'
        mock_bili_adapter.return_value = mock_bili_adapter_instance

        adapter = BiliUploadAdapterImpl(self.meeting)
        result = adapter.upload('/path/to/video.mp4', '/path/to/cover.png', return_replay_url=True)

        self.assertEqual(result, 'https://replay.bili.com/BV123456')
        mock_bili_adapter_instance.get_replay_url.assert_called_once_with('BV123456')

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl.BiliAdapterImpl')
    def test_upload_returns_bvid(self, mock_bili_adapter):
        """Test upload returns bvid when return_replay_url=False."""
        mock_bili_adapter_instance = mock.MagicMock()
        mock_bili_adapter_instance.upload.return_value = {'bvid': 'BV123456'}
        mock_bili_adapter.return_value = mock_bili_adapter_instance

        adapter = BiliUploadAdapterImpl(self.meeting)
        result = adapter.upload('/path/to/video.mp4', '/path/to/cover.png', return_replay_url=False)

        self.assertEqual(result, 'BV123456')
        mock_bili_adapter_instance.get_replay_url.assert_not_called()

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl.BiliAdapterImpl')
    def test_upload_returns_none_on_invalid_result(self, mock_bili_adapter):
        """Test upload returns None when result is invalid."""
        mock_bili_adapter_instance = mock.MagicMock()
        mock_bili_adapter_instance.upload.return_value = 'invalid_result'  # Not a dict
        mock_bili_adapter.return_value = mock_bili_adapter_instance

        adapter = BiliUploadAdapterImpl(self.meeting)
        result = adapter.upload('/path/to/video.mp4', '/path/to/cover.png')

        self.assertIsNone(result)

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl.BiliAdapterImpl')
    def test_upload_returns_none_on_missing_bvid(self, mock_bili_adapter):
        """Test upload returns None when bvid is missing."""
        mock_bili_adapter_instance = mock.MagicMock()
        mock_bili_adapter_instance.upload.return_value = {'status': 'success'}  # Missing bvid
        mock_bili_adapter.return_value = mock_bili_adapter_instance

        adapter = BiliUploadAdapterImpl(self.meeting)
        result = adapter.upload('/path/to/video.mp4', '/path/to/cover.png')

        self.assertIsNone(result)

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl.BiliAdapterImpl')
    def test_add_video_success(self, mock_bili_adapter):
        """Test add_video calls BiliAdapterImpl.add_video."""
        mock_bili_adapter_instance = mock.MagicMock()
        mock_bili_adapter_instance.add_video.return_value = {'status': 'success'}
        mock_bili_adapter.return_value = mock_bili_adapter_instance

        adapter = BiliUploadAdapterImpl(self.meeting)
        result = adapter.add_video('BV123456')

        mock_bili_adapter_instance.add_video.assert_called_once_with('BV123456')


class ObsUploadAdapterImplTest(TestCommonMeeting):
    """Test ObsUploadAdapterImpl."""

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.meeting = {
            "community": "openEuler",
            "mid": "test_mid_123",
            "date": "2026-04-15",
            "group_name": "test_group",
            "topic": "Test Meeting",
            "sponsor": "test_sponsor",
            "agenda": "Test Agenda",
            "start": "10:00",
            "end": "11:00",
        }
        # Create a temporary video file
        self.video_path = os.path.join(self.temp_dir, 'test_video.mp4')
        with open(self.video_path, 'wb') as f:
            f.write(b'test video content')

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_get_obs_video_object(self, mock_obs_settings, mock_obs_adapter):
        """Test _get_obs_video_object generates correct path."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })
        mock_obs_adapter.return_value = mock.MagicMock()

        adapter = ObsUploadAdapterImpl(self.meeting)
        video_object = adapter._get_obs_video_object()

        # Should be in format: community/group_name/month/mid_sub_id.mp4
        self.assertIn(self.meeting["community"], video_object)
        self.assertIn(self.meeting["group_name"], video_object)
        self.assertIn(self.meeting["mid"], video_object)
        self.assertTrue(video_object.endswith('.mp4'))

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_get_obs_video_object_with_sub_id(self, mock_obs_settings, mock_obs_adapter):
        """Test _get_obs_video_object includes sub_id for cycle meeting."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })
        mock_obs_adapter.return_value = mock.MagicMock()

        meeting = self.meeting.copy()
        meeting["sub_id"] = "sub_123"

        adapter = ObsUploadAdapterImpl(meeting)
        video_object = adapter._get_obs_video_object()

        # Should include sub_id in path
        self.assertIn("sub_123", video_object)

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_get_obs_cover_object(self, mock_obs_settings, mock_obs_adapter):
        """Test _get_obs_cover_object replaces .mp4 with .png."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })
        mock_obs_adapter.return_value = mock.MagicMock()

        adapter = ObsUploadAdapterImpl(self.meeting)
        video_object = "path/to/video.mp4"
        cover_object = adapter._get_obs_cover_object(video_object)

        self.assertEqual(cover_object, "path/to/video.png")

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_generate_obs_metadata(self, mock_obs_settings, mock_obs_adapter):
        """Test _generate_obs_metadata generates correct metadata."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })
        mock_obs_adapter.return_value = mock.MagicMock()

        adapter = ObsUploadAdapterImpl(self.meeting)
        video_object = "path/to/video.mp4"
        metadata = adapter._generate_obs_metadata(video_object, self.video_path)

        # Should contain required fields
        self.assertEqual(metadata["meeting_id"], self.meeting["mid"])
        self.assertEqual(metadata["meeting_topic"], self.meeting["topic"])
        self.assertEqual(metadata["community"], self.meeting["community"])
        self.assertEqual(metadata["sig"], self.meeting["group_name"])
        self.assertIn("record_start", metadata)
        self.assertIn("record_end", metadata)
        self.assertIn("download_url", metadata)
        self.assertIn("total_size", metadata)

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_get_size_of_file(self, mock_obs_settings, mock_obs_adapter):
        """Test _get_size_of_file returns correct size."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })
        mock_obs_adapter.return_value = mock.MagicMock()

        adapter = ObsUploadAdapterImpl(self.meeting)
        size = adapter._get_size_of_file(self.video_path)

        self.assertIsNotNone(size)
        self.assertGreater(size, 0)

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_get_size_of_file_nonexistent(self, mock_obs_settings, mock_obs_adapter):
        """Test _get_size_of_file returns None for nonexistent file."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })
        mock_obs_adapter.return_value = mock.MagicMock()

        adapter = ObsUploadAdapterImpl(self.meeting)
        size = adapter._get_size_of_file('/nonexistent/path.mp4')

        self.assertIsNone(size)

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_upload_success(self, mock_obs_settings, mock_obs_adapter):
        """Test upload returns video and cover object on success."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })

        mock_obs_adapter_instance = mock.MagicMock()
        mock_obs_adapter_instance.upload_file.return_value = {'status': 200}
        mock_obs_adapter.return_value = mock_obs_adapter_instance

        adapter = ObsUploadAdapterImpl(self.meeting)
        video_object, cover_object = adapter.upload(self.video_path, self.video_path.replace('.mp4', '.png'))

        self.assertIsNotNone(video_object)
        self.assertIsNotNone(cover_object)
        self.assertTrue(video_object.endswith('.mp4'))
        self.assertTrue(cover_object.endswith('.png'))

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_upload_video_failure(self, mock_obs_settings, mock_obs_adapter):
        """Test upload returns None when video upload fails."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })

        mock_obs_adapter_instance = mock.MagicMock()
        mock_obs_adapter_instance.upload_file.return_value = {'status': 500}
        mock_obs_adapter.return_value = mock_obs_adapter_instance

        adapter = ObsUploadAdapterImpl(self.meeting)
        video_object, cover_object = adapter.upload(self.video_path, self.video_path.replace('.mp4', '.png'))

        self.assertIsNone(video_object)
        self.assertIsNone(cover_object)

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_upload_invalid_result_format(self, mock_obs_settings, mock_obs_adapter):
        """Test upload returns None when result format is invalid."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })

        mock_obs_adapter_instance = mock.MagicMock()
        # Return result without 'status' key
        mock_obs_adapter_instance.upload_file.return_value = {'message': 'uploaded'}
        mock_obs_adapter.return_value = mock_obs_adapter_instance

        adapter = ObsUploadAdapterImpl(self.meeting)
        video_object, cover_object = adapter.upload(self.video_path, self.video_path.replace('.mp4', '.png'))

        self.assertIsNone(video_object)
        self.assertIsNone(cover_object)

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_get_obs_video_download_url(self, mock_obs_settings, mock_obs_adapter):
        """Test _get_obs_video_download_url generates correct URL."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })
        mock_obs_adapter.return_value = mock.MagicMock()

        adapter = ObsUploadAdapterImpl(self.meeting)
        url = adapter._get_obs_video_download_url('obs.test.com', 'test_bucket', 'path/to/video.mp4')

        # Should contain bucket, endpoint and object path
        self.assertIn('test_bucket', url)
        self.assertIn('obs.test.com', url)
        self.assertIn('path/to/video.mp4', url)
        self.assertTrue(url.startswith('https://'))


class UploadAdapterInitTest(TestCommonMeeting):
    """Test upload adapter initialization."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl.BiliAdapterImpl')
    def test_bili_adapter_init(self, mock_bili_adapter):
        """Test BiliUploadAdapterImpl initialization."""
        meeting = {
            "community": "openEuler",
            "mid": "test",
            "date": "2026-04-15",
            "group_name": "test",
            "topic": "test",
            "sponsor": "test",
            "agenda": "",
            "start": "10:00",
            "end": "11:00",
        }

        adapter = BiliUploadAdapterImpl(meeting)

        self.assertIsNotNone(adapter.bili_adapter_impl)
        mock_bili_adapter.assert_called_once_with("openEuler")

    @mock.patch('meeting.infrastructure.adapter.obs_adapter_impl.ObsAdapterImp')
    @mock.patch('django.conf.settings.COMMUNITY_OBS')
    def test_obs_adapter_init(self, mock_obs_settings, mock_obs_adapter):
        """Test ObsUploadAdapterImpl initialization."""
        mock_obs_settings.__getitem__ = mock.MagicMock(return_value={
            'AK': 'test_ak',
            'SK': 'test_sk',
            'ENDPOINT': 'obs.test.com',
            'BUCKET': 'test_bucket'
        })

        meeting = {
            "community": "openEuler",
            "mid": "test",
            "date": "2026-04-15",
            "group_name": "test",
            "topic": "test",
            "sponsor": "test",
            "agenda": "",
            "start": "10:00",
            "end": "11:00",
        }

        adapter = ObsUploadAdapterImpl(meeting)

        self.assertIsNotNone(adapter.obs_adapter_imp)
        self.assertEqual(adapter.endpoint, 'obs.test.com')
        self.assertEqual(adapter.bucket, 'test_bucket')