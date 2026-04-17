#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.


from django.urls import path

from meeting.controller.inner import MeetingView, SingleMeetingView, MeetingParticipantsView, \
    MeetingPlatformView, MeetingDateView, MeetingTextCallBack, SingleSubMeetingView, NotifyMeetingView, \
    MeetingGroupView, ForceEndMeetingView, MeetingListView, MeetingSponsorView

urlpatterns = [
    path('meeting/', MeetingView.as_view()),                                    # 预定会议/会议列表
    path('meeting/list/', MeetingListView.as_view()),                           # 合并会议列表（新增）
    path('meeting/<int:id>/', SingleMeetingView.as_view()),                     # 修改/删除/查询会议/周期性会议
    path('meeting/notify/<int:id>/', NotifyMeetingView.as_view()),              # 根据会议id通知对应的会议
    path('meeting/sub/<str:sub_id>/', SingleSubMeetingView.as_view()),          # 修改/删除周期性会议的子会议
    path('meeting/group_name/', MeetingGroupView.as_view()),                    # 获取所有会议的组名称
    path('meeting/sponsor/', MeetingSponsorView.as_view()),                     # 获取会议发起者列表
    path('meeting/date/', MeetingDateView.as_view()),                           # 获取会议时间（官网）
    path('meeting/participants/<int:id>/', MeetingParticipantsView.as_view()),  # 查询会议参与人
    path('meeting/platform/', MeetingPlatformView.as_view()),                   # 获取会议类型

    path('meeting/meeting_text/callback/', MeetingTextCallBack.as_view()),       # 文字翻译的回调地址

    # 超时会议相关API
    path('meeting/force_end/', ForceEndMeetingView.as_view()),           # 强制结束会议（统一接口）
]
