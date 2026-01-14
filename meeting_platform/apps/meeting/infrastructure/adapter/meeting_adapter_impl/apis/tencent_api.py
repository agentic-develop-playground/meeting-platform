#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import base64
import hashlib
import hmac
import json
import logging
import requests
import time
from datetime import datetime

from django.conf import settings
from rest_framework import status

from meeting_platform.utils.common import make_nonce, get_video_path
from meeting_platform.utils.file_stream import download_big_file
from meeting.domain.repository.meeting_adapter import MeetingAdapter
from meeting.infrastructure.adapter.meeting_adapter_impl.actions.tencent_action import TencentCreateAction, \
    TencentDeleteAction, TencentGetParticipantsAction, TencentGetVideo, TencentUpdateAction, TencentForceEndAction
from meeting_platform.utils.ret_api import MyValidationError
from meeting_platform.utils.ret_code import RetCode

logger = logging.getLogger('log')


class TencentApi(MeetingAdapter):
    meeting_type = "tencent"  # it is platform

    create_path = "/v1/meetings"
    update_path = "/v1/meetings/{}"
    delete_path = "/v1/meetings/{}/cancel"
    participants_path = "/v1/meetings/{}/participants?userid={}"
    record_path = "/v1/records?start_time={}&end_time={}&page_size=20&page={}&operator_id_type=1&operator_id={}&query_record_type=1"
    video_download_path = "/v1/addresses/{}?userid={}"
    force_end_path = "/v1/meetings/{}/dismiss"

    def __init__(self, community, platform, host_id):
        platform_info = settings.COMMUNITY_HOST[community][platform]
        cur_platforms = [i for i in platform_info if i["HOST"] == host_id]
        if len(cur_platforms) == 1:
            cur_platform_info = cur_platforms[0]
        else:
            raise RuntimeError("[TencentApi] init TencentApi failed, and get config({}) failed."
                               .format(len(cur_platforms)))
        self.app_id = cur_platform_info["TENCENT_APP_ID"]
        self.sdk_id = cur_platform_info["TENCENT_SDK_ID"]
        self.secret_id = cur_platform_info["TENCENT_SECRET_ID"]
        self.secret_key = cur_platform_info["TENCENT_SECRET_KEY"]
        self.host_key = cur_platform_info["TENCENT_HOST_KEY"]
        self.api_prefix = settings.API_PREFIX["TENCENT_API_PREFIX"]
        self.community = community
        self.platform = platform
        self.host_id = host_id
        self.time_out = settings.REQUEST_TIMEOUT
        self.bili_upload_date = settings.BILI_UPLOAD_DATE
        self.bili_video_min_size = settings.BILI_VIDEO_MIN_SIZE

    def _get_url(self, uri):
        """request url"""
        return self.api_prefix + uri

    def _get_time(self, time_temp):
        """get time"""
        return str(int(time.mktime(time.strptime(time_temp, '%Y-%m-%d %H:%M'))))

    def _get_signature(self, method, uri, body):
        """get signature"""
        timestamp = str(int(time.time()))
        nonce = make_nonce()
        headers = {
            "X-TC-Key": self.secret_id,
            "X-TC-Nonce": nonce,
            "X-TC-Timestamp": timestamp,
            "X-TC-Signature": "",
            "AppId": self.app_id,
            "SdkId": self.sdk_id,
            "X-TC-Registered": "1"
        }
        header = 'X-TC-Key=' + self.secret_id + '&X-TC-Nonce=' + nonce + '&X-TC-Timestamp=' + timestamp
        msg = (method + '\n' + header + '\n' + uri + '\n' + body).encode('utf-8')
        key = self.secret_key.encode('utf-8')
        signature = base64.b64encode(hmac.new(key, msg, digestmod=hashlib.sha256).hexdigest().encode()).decode('utf-8')
        headers['X-TC-Signature'] = signature
        return signature, headers

    # noinspection SpellCheckingInspection
    def create(self, action):
        """create meeting"""
        if not isinstance(action, TencentCreateAction):
            raise RuntimeError("[TencentApi] action must be the subclass of TencentCreateAction")
        date = action.date
        start_time = date + ' ' + action.start
        end_time = date + ' ' + action.end
        start_time = self._get_time(start_time)
        end_time = self._get_time(end_time)
        payload = {
            "userid": self.host_id,
            "instanceid": 1,
            "subject": action.topic,
            "type": 0,
            "start_time": start_time,
            "end_time": end_time,
            "settings": {
                "mute_enable_join": True
            },
            "enable_host_key": True,
            "host_key": self.host_key
        }
        if action.is_record:
            payload['settings']['auto_record_type'] = 'cloud'
            payload['settings']['participant_join_auto_record'] = True
            payload['settings']['enable_host_pause_auto_record'] = True
        uri = self.create_path
        url = self._get_url(uri)
        signature, headers = self._get_signature('POST', uri, json.dumps(payload))
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self.time_out)
        resp_dict = {
            'host_id': self.host_id
        }
        if r.status_code != 200:
            logger.error('[TencentApi] Fail to create meeting, status_code is {} and content:{}'
                         .format(r.status_code, r.content.decode("utf-8")))
            return r.status_code, resp_dict
        ret_json = r.json()
        resp_dict['mid'] = ret_json['meeting_info_list'][0]['meeting_code']
        resp_dict['m_mid'] = ret_json['meeting_info_list'][0]['meeting_id']
        resp_dict['join_url'] = ret_json['meeting_info_list'][0]['join_url']
        return r.status_code, resp_dict

    # noinspection SpellCheckingInspection
    def update(self, action):
        if not isinstance(action, TencentUpdateAction):
            raise RuntimeError("[TencentApi] action must be the subclass of TencentUpdateAction")
        date = action.date
        start_time = date + ' ' + action.start
        end_time = date + ' ' + action.end
        start_time = self._get_time(start_time)
        end_time = self._get_time(end_time)
        payload = {
            "userid": self.host_id,
            "instanceid": 1,
            "subject": action.topic,
            "type": 0,
            "start_time": start_time,
            "end_time": end_time,
            "settings": {
                "mute_enable_join": True
            },
            "enable_host_key": True,
            "host_key": self.host_key
        }
        if action.is_record:
            payload['settings']['auto_record_type'] = 'cloud'
            payload['settings']['participant_join_auto_record'] = True
            payload['settings']['enable_host_pause_auto_record'] = True
        else:
            payload['settings']['auto_record_type'] = 'none'
        uri = self.update_path.format(action.m_mid)
        url = self._get_url(uri)
        signature, headers = self._get_signature('PUT', uri, json.dumps(payload))
        r = requests.put(url, headers=headers, data=json.dumps(payload), timeout=self.time_out)
        if r.status_code != 200:
            logger.error('[TencentApi] Fail to update meeting, status_code is {},and err:{}'
                         .format(r.status_code, r.content.decode("utf-8")))
            resp_json = r.json()
            if isinstance(resp_json, dict) and resp_json.get("error_info") is not None:
                if resp_json["error_info"].get("new_error_code") == 101014151:
                    raise MyValidationError(RetCode.STATUS_MEETING_PUT_RUNNING)
            return r.status_code
        return r.status_code

    # noinspection SpellCheckingInspection
    def delete(self, action):
        if not isinstance(action, TencentDeleteAction):
            raise RuntimeError("[TencentApi] action must be the subclass of TencentDeleteAction")
        payload = json.dumps({
            "userid": self.host_id,
            "instanceid": 1,
            "reason_code": 1
        })
        mid = action.mid
        uri = self.delete_path.format(action.m_mid)
        url = self._get_url(uri)
        signature, headers = self._get_signature('POST', uri, payload)
        r = requests.post(url, headers=headers, data=payload,
                          timeout=self.time_out)
        if r.status_code != 200:
            logger.error('Fail to cancel meeting {}, and detail is:{}'.format(mid,  r.content.decode("utf-8")))
            resp_json = r.json()
            if isinstance(resp_json, dict) and resp_json.get("error_info") is not None:
                if resp_json["error_info"].get("new_error_code") == 101013603:
                    return status.HTTP_200_OK
        logger.info('[TencentApi] Cancel meeting {}'.format(mid))
        return r.status_code

    # noinspection SpellCheckingInspection
    def get_participants(self, action):
        if not isinstance(action, TencentGetParticipantsAction):
            raise RuntimeError("[TencentApi] action must be the subclass of TencentGetParticipantsAction")
        m_mid = action.m_mid
        uri = self.participants_path.format(m_mid, self.host_id)
        url = self._get_url(uri)
        signature, headers = self._get_signature('GET', uri, "")
        r = requests.get(url, headers=headers, timeout=self.time_out)
        if r.status_code == 200:
            res = {
                'total_records': r.json()['total_count'],
                'participants': [{'name': base64.b64decode(x['user_name'].encode()).decode()} for x in
                                 r.json()['participants']]
            }
            return r.status_code, res
        return r.status_code, r.json()

    def _get_records(self):
        """get records"""
        end_time = int(time.time())
        start_time = end_time - 3600 * 24 * self.bili_upload_date
        page = 1
        records = []
        while True:
            uri = self.record_path.format(start_time, end_time, page, self.host_id)
            signature, headers = self._get_signature('GET', uri, "")
            r = requests.get(self._get_url(uri), headers=headers, timeout=self.time_out)
            if r.status_code != 200:
                logger.error("[TencentApi/_get_records] {}/{} request record failed, and return is:{}."
                             .format(self.community, self.platform, r.content.decode("utf-8")))
                return []
            if 'record_meetings' not in r.json().keys():
                logger.info("[TencentApi/_get_records] {}/{} request record format failed, and return is:{}."
                            .format(self.community, self.platform, r.content.decode("utf-8")))
                break
            record_meetings = r.json().get('record_meetings')
            records.extend(record_meetings)
            page += 1
        return records

    # noinspection SpellCheckingInspection
    def _filter_records(self, action, recordings):
        """filter the available record"""
        match_record = dict()
        mid = action.mid
        m_mid = action.m_mid
        date = action.date
        start = action.start
        start_time = ' '.join([date, start])
        start_timestamp = int(datetime.timestamp(datetime.strptime(start_time, '%Y-%m-%d %H:%M')))
        for record in recordings:
            if record.get('meeting_id') != m_mid:
                continue
            if record.get('state') != 3:
                logger.error("[TencentApi/_filter_records] {}/{} record status is:{} (1 recording/2 transcoding)"
                             .format(self.community, mid, record.get('state')))
                continue
            media_start_time = record.get('media_start_time')
            if abs(media_start_time // 1000 - start_timestamp) > 1800:
                logger.error("[TencentApi/_filter_records] {}/{} record start time({}) gt the start time({}) in set"
                             .format(self.community, mid, media_start_time, start_timestamp))
                continue
            sorted_data = sorted(record.get('record_files'), key=lambda x: x['record_size'], reverse=True)
            record_file = sorted_data[0]
            if record_file.get('record_size') < self.bili_video_min_size:
                logger.error("[TencentApi/_filter_records] {}/{} find record size lt 10M".format(self.community, mid))
                continue
            if not match_record:
                match_record['record_file_id'] = record_file.get('record_file_id')
                match_record['record_size'] = record_file.get('record_size')
                match_record['userid'] = record.get('host_user_id')
            elif record_file.get('record_size') > match_record.get('record_size'):
                match_record['record_file_id'] = record_file.get('record_file_id')
                match_record['record_size'] = record_file.get('record_size')
                match_record['userid'] = record.get('host_user_id')
        if not match_record:
            logger.error('[TencentApi/_filter_records] {}/{}: Find no recordings about Tencent meeting'.
                         format(self.community, mid))
            return
        return match_record

    def _get_video_download(self, record_file_id, user_id):
        """get video download url"""
        uri = self.video_download_path.format(record_file_id, user_id)
        signature, headers = self._get_signature('GET', uri, "")
        r = requests.get(self._get_url(uri), headers=headers, timeout=self.time_out)
        if r.status_code != 200:
            logger.error('[TencentApi/_filter_records] {}/{}: get video download failed:{}'.
                         format(self.community, record_file_id, r.content.decode("utf-8")))
            return
        return r.json().get("download_address")

    def _download_video(self, action, available_record):
        """download the video"""
        mid = action.mid
        download_url = self._get_video_download(available_record.get('record_file_id'), available_record.get('userid'))
        if not download_url:
            logger.error("[TencentApi/_download_video] {}/{}: get empty download url".format(self.community, mid))
            return
        target_filename = get_video_path(mid, self.community)
        download_big_file(download_url, target_filename)
        return target_filename

    def get_video(self, action):
        """get video"""
        if not isinstance(action, TencentGetVideo):
            raise RuntimeError("[TencentApi] action must be the subclass of TencentGetVideo")
        recordings = self._get_records()
        if not recordings:
            logger.error("[TencentApi/get_video] {}/{}:find no recordings".format(self.community, action.mid))
            return
        available_record = self._filter_records(action, recordings)
        if not available_record:
            logger.info('[TencentApi/get_video] {}/{}:filter no available recording'.format(self.community, action.mid))
            return
        return self._download_video(action, available_record)

    def force_end_meeting(self, action):
        """force end meeting"""
        if not isinstance(action, TencentForceEndAction):
            raise RuntimeError("[TencentApi] action must be the subclass of TencentForceEndAction")
        payload = json.dumps({
            "operator_id": self.host_id,
            "operator_id_type": 1,
            "instanceid": 1,
            "reason_code": 3,
            "reason_detail": "结束会议",
            "retrieve_code": 1,
            "force_dismiss_meeting": 1
        })
        m_mid = action.m_mid
        uri = self.force_end_path.format(m_mid)
        url = self._get_url(uri)
        signature, headers = self._get_signature('POST', uri, payload)
        r = requests.post(url, headers=headers, data=payload,
                          timeout=self.time_out)
        if r.status_code != 200:
            logger.error('[TencentApi] Fail to force end meeting {}, and return data:{}'.format(m_mid,
                                                                                                r.json()))
            logger.error(r.content.decode("utf-8"))
            return r.status_code
        logger.info('[TencentApi] force end meeting {}'.format(m_mid))
        return r.status_code
