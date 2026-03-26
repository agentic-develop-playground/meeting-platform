#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import datetime
import json
import secrets
import requests
import logging

from django.conf import settings

from meeting.infrastructure.adapter.obs_adapter_impl import ObsAdapterImp
from meeting_platform.utils.common import get_video_path
from meeting_platform.utils.file_stream import download_big_file
from meeting.domain.repository.meeting_adapter import MeetingAdapter
from meeting.infrastructure.adapter.meeting_adapter_impl.actions.zoom_action import ZoomCreateAction, \
    ZoomUpdateAction, ZoomDeleteAction, ZoomGetParticipantsAction, ZoomGetVideo, ZoomForceEndAction, \
    ZoomGetMeetingStatusAction

logger = logging.getLogger("log")


class ZoomApi(MeetingAdapter):
    meeting_type = "zoom"  # it is platform

    create_path = "/v2/users/{}/meetings"
    update_path = "/v2/meetings/{}"
    delete_path = "/v2/meetings/{}"
    participants_path = "/v2/past_meetings/{}/participants?page_size=300"
    records_path = "/v2/users/{}/recordings"
    force_end_path = "/v2/meetings/{}/status"

    my_obs_adapter_impl = ObsAdapterImp

    def __init__(self, community, platform, host_id):
        platform_info = settings.COMMUNITY_HOST[community][platform]
        cur_platforms = [i for i in platform_info if i["HOST"] == host_id]
        if len(cur_platforms) == 1:
            cur_platform_info = cur_platforms[0]
        else:
            raise RuntimeError("[ZoomApi] init ZoomApi failed, and get config({}) failed.".format(len(cur_platforms)))
        self.account = cur_platform_info["ACCOUNT"]
        self.obs_token = settings.COMMUNITY_ZOOM_OBS[community]
        self.community = community
        self.platform = platform
        self.host_id = host_id
        self.api_prefix = settings.API_PREFIX["ZOOM_API_PREFIX"]
        self.time_out = settings.REQUEST_TIMEOUT
        self.bili_upload_date = settings.BILI_UPLOAD_DATE
        self.bili_video_min_size = settings.BILI_VIDEO_MIN_SIZE

    def _get_url(self, uri):
        """get url"""
        return self.api_prefix + uri

    def _get_oauth_token(self):
        """get oauth token"""
        obs_client = self.my_obs_adapter_impl(self.obs_token["AK"], self.obs_token["SK"], self.obs_token["ENDPOINT"])
        res = obs_client.get_object_metadata(self.obs_token["BUCKET"], self.obs_token["OBJECT"])
        token = ''
        if res.get('status') != 200:
            logger.error('[ZoomApi/_get_oauth_token] {}:Fail to get zoom token'.format(self.community))
            return token
        for k, v in res.get('header'):
            if k == 'access_token':
                token = v
                break
        logger.info('[ZoomApi/_get_oauth_token] {}:Get zoom token successfully'.format(self.community))
        return token

    def create(self, action):
        """create meeting"""
        if not isinstance(action, ZoomCreateAction):
            raise RuntimeError("[ZoomApi] action must be the subclass of ZoomCreateAction")
        start_time = (datetime.datetime.strptime(action.date + action.start, '%Y-%m-%d%H:%M') -
                      datetime.timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time = (datetime.datetime.strptime(action.date + action.end, '%Y-%m-%d%H:%M') -
                    datetime.timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M:%SZ')
        duration = int((datetime.datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ') -
                        datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')).seconds / 60)
        token = self._get_oauth_token()
        headers = {
            "content-type": "application/json",
            "authorization": "Bearer {}".format(token)
        }
        if action.is_record:
            auto_recording = "cloud"
        else:
            auto_recording = "none"
        payload = {
            'start_time': start_time,
            'duration': duration,
            'topic': action.topic,
            'password': secrets.token_hex(3),
            'settings': {
                'waiting_room': False,
                'auto_recording': auto_recording,
                'join_before_host': True,
                'jbh_time': 5
            }
        }
        uri = self.create_path.format(self.host_id)
        response = requests.post(self._get_url(uri), data=json.dumps(payload), headers=headers,
                                 timeout=self.time_out)
        resp_dict = {}
        if response.status_code != 201:
            return response.status_code, resp_dict
        resp_dict['mid'] = response.json()['id']
        resp_dict['start_url'] = response.json()['start_url']
        resp_dict['join_url'] = response.json()['join_url']
        resp_dict['host_id'] = response.json()['host_id']
        return response.status_code, resp_dict

    def update(self, action):
        """update meeting"""
        if not isinstance(action, ZoomUpdateAction):
            raise RuntimeError("[ZoomApi] action must be the subclass of ZoomUpdateAction")
        start = action.start
        end = action.end
        date = action.date
        if int(start.split(':')[0]) >= 8:
            start_time = date + 'T' + ':'.join([str(int(start.split(':')[0]) - 8), start.split(':')[1], '00Z'])
        else:
            d1 = datetime.datetime.strptime(date, '%Y-%m-%d') - datetime.timedelta(days=1)
            d2 = datetime.datetime.strftime(d1, '%Y-%m-%d %H%M%S')[:10]
            start_time = d2 + 'T' + ':'.join([str(int(start.split(':')[0]) + 16), start.split(':')[1], '00Z'])
        duration = (int(end.split(':')[0]) - int(start.split(':')[0])) * 60 + \
                   (int(end.split(':')[1]) - int(start.split(':')[1]))
        if action.is_record:
            auto_recording = "cloud"
        else:
            auto_recording = "none"
        new_data = {
            'start_time': start_time,
            'duration': duration,
            'topic': action.topic,
            'settings': {
                'waiting_room': False,
                'auto_recording': auto_recording,
            }
        }
        token = self._get_oauth_token()
        headers = {
            "content-type": "application/json",
            "authorization": "Bearer {}".format(token)
        }
        uri = self.update_path.format(action.mid)
        response = requests.patch(self._get_url(uri), data=json.dumps(new_data),
                                  headers=headers, timeout=self.time_out)
        return response.status_code

    def delete(self, action):
        """delete meeting"""
        if not isinstance(action, ZoomDeleteAction):
            raise RuntimeError("[ZoomApi] action must be the subclass of ZoomDeleteAction")
        uri = self.delete_path.format(action.mid)
        token = self._get_oauth_token()
        headers = {
            "authorization": "Bearer {}".format(token)
        }
        response = requests.request("DELETE", self._get_url(uri),
                                    headers=headers, timeout=self.time_out)
        return response.status_code

    def get_participants(self, action):
        """get participants from meeting"""
        if not isinstance(action, ZoomGetParticipantsAction):
            raise RuntimeError("[ZoomApi] action must be the subclass of ZoomGetParticipantsAction")
        uri = self.participants_path.format(action.mid)
        token = self._get_oauth_token()
        headers = {
            "authorization": "Bearer {}".format(token)}
        r = requests.get(self._get_url(uri), headers=headers, timeout=self.time_out)
        if r.status_code == 200:
            ret_json = r.json()
            total_records = ret_json['total_records']
            participants = ret_json['participants']
            resp = {'total_records': total_records, 'participants': [{'name': x['name']} for x in participants]}
            return r.status_code, resp
        elif r.status_code == 404:
            return 200, r.json()
        else:
            return r.status_code, r.json()

    def get_records(self, action):
        """get all records"""
        mid = action.mid
        uri = self.records_path.format(self.host_id)
        headers = {
            'authorization': 'Bearer {}'.format(self._get_oauth_token())
        }
        params = {
            'from': (datetime.datetime.now() - datetime.timedelta(days=self.bili_upload_date)).strftime("%Y-%m-%d"),
            'page_size': 50
        }
        response = requests.get(self._get_url(uri), headers=headers, params=params, timeout=self.time_out)
        if response.status_code != 200:
            logger.error('[ZoomApi/get_records] {}/{} get recordings failed: {} {}'.
                         format(self.community, self.platform, response.status_code, response.content.decode("utf-8")))
            return
        ret_json = response.json()
        if "meetings" not in ret_json:
            logger.error('[ZoomApi/get_records] {}/{} get recordings format failed: {} {}'.
                         format(self.community, self.platform, response.status_code, ret_json.get("message")))
            return
        records = list(filter(lambda x: x if x['id'] == int(mid) else None, ret_json['meetings']))
        if not records:
            logger.info('[ZoomApi/get_records] {}/{} meeting {} have no recordings yet'.
                        format(self.community, self.platform, mid))
            return
        sorted_data = sorted(records, key=lambda x: x['total_size'], reverse=True)
        return sorted_data[0]

    def get_records_by_duration_day(self, duration_day):
        uri = self.records_path.format(self.host_id)
        headers = {
            'authorization': 'Bearer {}'.format(self._get_oauth_token())
        }
        params = {
            'from': (datetime.datetime.now() - datetime.timedelta(days=duration_day)).strftime("%Y-%m-%d"),
            'page_size': 50
        }
        response = requests.get(self._get_url(uri), headers=headers, params=params, timeout=self.time_out)
        if response.status_code != 200:
            logger.error('[ZoomApi/get_records] {}/{} get recordings failed: {} {}'.
                         format(self.community, self.platform, response.status_code, response.content.decode("utf-8")))
            return
        ret_json = response.json()
        if "meetings" not in ret_json:
            logger.error('[ZoomApi/get_records] {}/{} get recordings format failed: {} {}'.
                         format(self.community, self.platform, response.status_code, ret_json.get("message")))
            return
        return ret_json['meetings']

    def _get_download_url(self, action, recordings):
        """get download url"""
        logger.info("start to filter download url....")
        if action:
            mid = action.mid
        else:
            mid = ""
        recordings_list = list(
            filter(lambda x: x if x['file_extension'] == 'MP4' else None, recordings['recording_files']))
        if len(recordings_list) == 0:
            logger.info('[ZoomApi/_get_download_url] {}/{}: file_extension not is mp4 and result is empty'.
                        format(self.community, mid))
            return
        sorted_data = sorted(recordings_list, key=lambda x: x['file_size'], reverse=True)
        total_size = sorted_data[0]['file_size']
        logger.info('[ZoomApi/_get_download_url] {}/{}: the full size of the recording file is {}'.
                    format(self.community, mid, total_size))
        if total_size < self.bili_video_min_size:
            logger.info('[ZoomApi/_get_download_url] {}/{} the size of file is lt 1M'.
                        format(self.community, mid))
            return
        return sorted_data[0]['download_url']

    def _download_video(self, action, download_url):
        """download video"""
        logger.info("start to download url....")
        mid = action.mid
        video_path = get_video_path(str(mid), self.community)
        r = requests.get(url=download_url, allow_redirects=False, timeout=self.time_out)
        url = r.headers['location']
        filename = download_big_file(url, video_path)
        return filename

    def get_video(self, action):
        """get video"""
        if not isinstance(action, ZoomGetVideo):
            raise RuntimeError("[ZoomApi/get_video] action must be the subclass of ZoomGetVideo")
        records = self.get_records(action)
        if not records:
            logger.error("[ZoomApi/get_video] {}/{}: get empty records.".format(self.community, action.mid))
            return
        download_url = self._get_download_url(action, records)
        if not download_url:
            logger.error("[ZoomApi/get_video] {}/{}: get empty download_url.".format(self.community, action.mid))
            return
        return self._download_video(action, download_url)

    def get_video_by_day(self, day):
        records = self.get_records_by_duration_day(day)
        if not records:
            logger.error("[ZoomApi/get_video_by_day] {}/{}: get empty records.".format(self.community, self.host_id))
            return list()
        return records

    def get_video_url_by_records(self, records):
        path_dict = dict()
        for record in records:
            logger.info("start to get the url for {}".format(record))
            download_url = self._get_download_url(None, record)
            if not download_url:
                logger.error("[ZoomApi/get_video] {}: get empty download_url.".format(self.community))
                continue
            action = ZoomGetVideo(mid=record["id"])
            filename = self._download_video(action, download_url)
            path_dict[filename] = record
        return path_dict

    def force_end_meeting(self, action):
        """force end meeting"""
        if not isinstance(action, ZoomForceEndAction):
            raise RuntimeError("[ZoomApi] action must be the subclass of ZoomForceEndAction")
        uri = self.force_end_path.format(action.mid)
        token = self._get_oauth_token()
        headers = {
            "authorization": "Bearer {}".format(token)
        }
        data = {
            "action": "end"
        }
        response = requests.request("PUT", self._get_url(uri), data=data,
                                    headers=headers, timeout=self.time_out)
        if response.status_code != 200:
            logger.error('[ZoomApi] Fail to force end meeting {}, and return data:{}'.format(action.mid,
                                                                                             response.json()))
        return response.status_code

    def get_meeting_status(self, action):
        """查询Zoom会议状态"""
        if not isinstance(action, ZoomGetMeetingStatusAction):
            raise RuntimeError("[ZoomApi] action must be the subclass of ZoomGetMeetingStatusAction")
        detail_meeting_path = "/v2/meetings/{}"
        uri = detail_meeting_path.format(action.mid)
        headers = {"authorization": "Bearer {}".format(self._get_oauth_token())}
        r = requests.get(self._get_url(uri), headers=headers, timeout=self.time_out)
        if r.status_code == 200:
            # status: waiting/started/ended
            return r.json().get('status') == 'started'
        logger.error('[ZoomApi] Fail to get meeting status for {}, status_code: {}, content: {}'
                     .format(action.mid, r.status_code, r.content.decode("utf-8")))
        return False

