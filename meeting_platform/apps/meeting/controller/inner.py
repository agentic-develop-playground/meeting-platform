#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from copy import deepcopy

from django.db.models import Q
from django.forms import model_to_dict

from rest_framework.authentication import BasicAuthentication
from rest_framework.filters import SearchFilter
from rest_framework.generics import CreateAPIView, DestroyAPIView, GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from meeting.application.meeting import MeetingApp
from meeting.application.obs_records_app import OBSRecordsApp
from meeting.controller.serializers.meeting_serializers import MeetingSerializer, SingleMeetingSerializer, \
    TranslateVideoTextSerializer, CycleSubMeetingSerializer, MeetingGroupNameSerializer

from meeting.infrastructure.dao.meeting_dao import MeetingDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import MeetingAdapterImpl

from meeting_platform.utils.customized.my_pagination import MyPagination
from meeting_platform.utils.ret_code import RetCode
from meeting_platform.utils.customized.my_serializers import MySerializerParse, EmptySerializers
from meeting_platform.utils.ret_api import ret_json, capture_my_validation_exception, MyValidationError
from meeting_platform.utils.customized.my_view import MyRetrieveModelMixin, MyUpdateAPIView, MyListModelMixin
from meeting_platform.utils.operation_log import OperationLogModule, OperationLogDesc, OperationLogType, \
    logger_wrapper, set_log_thread_local, log_key


class MeetingView(MySerializerParse, MyListModelMixin, ListAPIView, CreateAPIView):
    """create or list meeting"""
    serializer_class = MeetingSerializer
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = MeetingApp.meeting_dao.get_queryset()
    filter_backends = [SearchFilter]
    search_fields = ['community', "mid", "id", "sponsor"]
    pagination_class = MyPagination
    app_class = MeetingApp()
    order_by = ["date", "create_time", "update_time"]
    order_type = ["asc", "desc"]

    @capture_my_validation_exception
    @logger_wrapper(OperationLogModule.OP_MODULE_MEETING, OperationLogType.OP_TYPE_CREATE,
                    OperationLogDesc.OP_DESC_MEETING_CREATE_CODE)
    def create(self, request, *args, **kwargs):
        """create meeting api"""
        set_log_thread_local(request, log_key, [request.data.get('community'),
                                                request.data.get("sponsor"),
                                                request.data.get('topic')])
        meeting = self.get_my_serializer_data(request)
        data = self.app_class.create(meeting)
        return ret_json(data=data)

    def get_queryset(self):
        """get the queryset"""
        finally_queryset = deepcopy(self.queryset)
        date = self.request.query_params.get("date")
        if date is not None:
            date = self.serializer_class.check_date(date)
            self.queryset = self.queryset.filter(Q(date=date) | Q(cycle_sub_meeting__date=date))
        month = self.request.query_params.get("month")
        if month is not None:
            first_date, last_date = self.serializer_class.check_month(month)
            self.queryset = self.queryset.filter(Q(date__gte=first_date, date__lte=last_date) |
                                                 Q(cycle_sub_meeting__date__gte=first_date,
                                                   cycle_sub_meeting__date__lte=last_date))
        is_delete = self.request.query_params.get("is_delete")
        if is_delete is not None:
            self.queryset = self.queryset.filter(is_delete=is_delete)
        sponsor = self.request.query_params.get("sponsor")
        if sponsor is not None:
            self.queryset = self.queryset.filter(sponsor=sponsor)
        community = self.request.query_params.get("community")
        if community is not None:
            self.queryset = self.queryset.filter(community=community)
        is_private = self.request.query_params.get("is_private")
        if is_private is not None:
            self.queryset = self.queryset.filter(is_private=is_private)
        meeting_ids_str = self.request.query_params.get("meeting_ids")
        if meeting_ids_str is not None:
            meeting_ids = meeting_ids_str.split(",")
            self.queryset = self.queryset.filter(id__in=meeting_ids)
        topic = self.request.query_params.get("topic")
        if topic is not None:
            self.queryset = self.queryset.filter(topic__icontains=topic)
        group_name = self.request.query_params.get("group_name")
        if group_name is not None:
            self.queryset = self.queryset.filter(group_name__icontains=group_name)
        time_range = self.request.query_params.get("time_range")
        if time_range is not None:
            # 判断时间？weekly, recently, daily,
            self.queryset = self.app_class.get_time_range_meeting(self.queryset, time_range)
        order_by = self.request.query_params.get("order_by")
        if order_by and order_by not in self.order_by:
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        if not order_by:
            order_by = "date"
        order_type = self.request.query_params.get("order_type")
        if order_type and order_type not in self.order_type:
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        if not order_type:
            order_type = "desc"
        if order_type == "desc":
            order_by = "-{}".format(order_by)
        # get the meeting id
        distinct_ids = self.queryset.values_list("id", flat=True).distinct()
        return finally_queryset.filter(id__in=list(distinct_ids)).order_by(order_by, 'start')


class SingleMeetingView(MySerializerParse, MyRetrieveModelMixin, MyUpdateAPIView, RetrieveAPIView, DestroyAPIView):
    """get or update or delete meeting"""
    lookup_field = "id"
    serializer_class = SingleMeetingSerializer
    queryset = MeetingApp.meeting_dao.get_queryset().filter(is_delete=0)
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAuthenticated,)
    app_class = MeetingApp()

    @capture_my_validation_exception
    @logger_wrapper(OperationLogModule.OP_MODULE_MEETING, OperationLogType.OP_TYPE_MODIFY,
                    OperationLogDesc.OP_DESC_MEETING_UPDATE_CODE)
    def update(self, request, *args, **kwargs):
        """update meeting api"""
        set_log_thread_local(request, log_key, [request.data.get('community'),
                                                request.data.get('topic'), kwargs.get('id')])
        meeting = self.get_my_serializer_data(request)
        data = self.app_class.update(request, kwargs.get('id'), meeting)
        return ret_json(data=data)

    @capture_my_validation_exception
    @logger_wrapper(OperationLogModule.OP_MODULE_MEETING, OperationLogType.OP_TYPE_DELETE,
                    OperationLogDesc.OP_DESC_MEETING_DELETE_CODE)
    def destroy(self, request, *args, **kwargs):
        """delete meeting by mid"""
        set_log_thread_local(request, log_key, ["", "", kwargs.get('id')])
        data = self.app_class.delete(request, kwargs.get('id'))
        return ret_json(data=data)


class SingleSubMeetingView(MySerializerParse, MyRetrieveModelMixin, MyUpdateAPIView, RetrieveAPIView, DestroyAPIView):
    """update or delete a cycle sub meeting"""
    lookup_field = "sub_id"
    serializer_class = CycleSubMeetingSerializer
    queryset = MeetingApp.meeting_cycle_sub_dao.get_all()
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAuthenticated,)
    app_class = MeetingApp()

    def get_queryset(self):
        """get the queryset"""
        return self.queryset.filter(sub_id=self.kwargs.get("sub_id"))

    @capture_my_validation_exception
    @logger_wrapper(OperationLogModule.OP_MODULE_MEETING, OperationLogType.OP_TYPE_MODIFY,
                    OperationLogDesc.OP_DESC_MEETING_UPDATE_SUB_CODE)
    def update(self, request, *args, **kwargs):
        """update meeting api"""
        set_log_thread_local(request, log_key, [request.data.get('mid'), kwargs.get("sub_id")])
        meeting = self.get_my_serializer_data(request)
        meeting["sub_id"] = kwargs.get("sub_id")
        data = self.app_class.update_sub(meeting)
        return ret_json(data=data)

    @capture_my_validation_exception
    @logger_wrapper(OperationLogModule.OP_MODULE_MEETING, OperationLogType.OP_TYPE_DELETE,
                    OperationLogDesc.OP_DESC_MEETING_DELETE_SUB_CODE)
    def destroy(self, request, *args, **kwargs):
        """delete meeting by mid"""
        set_log_thread_local(request, log_key, [kwargs.get('sub_id')])
        data = self.app_class.delete_sub(kwargs.get('sub_id'))
        return ret_json(data=data)


class NotifyMeetingView(RetrieveAPIView, GenericAPIView):
    lookup_field = "id"
    serializer_class = EmptySerializers
    queryset = MeetingApp.meeting_dao.get_queryset().filter(is_delete=0)
    authentication_classes = (BasicAuthentication,)
    app_class = MeetingApp()

    @capture_my_validation_exception
    def retrieve(self, *args, **kwargs):
        data = self.app_class.notify_meeting(kwargs.get('id'))
        return ret_json(data=data)


class MeetingParticipantsView(RetrieveAPIView, GenericAPIView):
    lookup_field = "id"
    serializer_class = EmptySerializers
    queryset = MeetingApp.meeting_dao.get_queryset().filter(is_delete=0)
    authentication_classes = (BasicAuthentication,)
    app_class = MeetingApp()

    def retrieve(self, *args, **kwargs):
        data = self.app_class.get_participants(kwargs.get('id'))
        return ret_json(data=data)


class MeetingPlatformView(MyListModelMixin, GenericAPIView):
    serializer_class = EmptySerializers
    queryset = None
    authentication_classes = (BasicAuthentication,)
    app_class = MeetingApp()

    @capture_my_validation_exception
    def get(self, request):
        community = request.query_params.get("community")
        data = self.app_class.get_meeting_platform(community)
        return ret_json(data=data)


class MeetingDateView(MyListModelMixin, GenericAPIView):
    serializer_class = MeetingSerializer
    queryset = None
    authentication_classes = (BasicAuthentication,)
    app_class = MeetingApp()

    def get(self, request):
        community = request.query_params.get("community")
        group_name = request.query_params.get("group_name")
        date = request.query_params.get("date")
        if date is not None:
            date = self.serializer_class.check_date(date)
        is_record = request.query_params.get("is_record")
        if is_record is not None:
            is_record = True if is_record.lower() == "true" else False
        data = self.app_class.get_meeting_date(community, group_name, date, is_record)
        return ret_json(data=data)


class MeetingGroupView(MyListModelMixin, GenericAPIView):
    serializer_class = MeetingGroupNameSerializer
    queryset = None
    authentication_classes = (BasicAuthentication,)
    app_class = MeetingApp()

    def get(self, request):
        community = request.query_params.get("community")
        data = self.app_class.get_meeting_group_name(community)
        return ret_json(data=data)


class MeetingTextCallBack(MySerializerParse, CreateAPIView):
    serializer_class = TranslateVideoTextSerializer
    queryset = None
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAuthenticated,)
    app_class = OBSRecordsApp()

    @capture_my_validation_exception
    @logger_wrapper(OperationLogModule.OP_MODULE_MEETING, OperationLogType.OP_TYPE_CREATE,
                    OperationLogDesc.OP_DESC_MEETING_TRANSLATE_CALLBACK_CODE)
    def create(self, request, *args, **kwargs):
        """create the translating meeting api"""
        set_log_thread_local(request, log_key, [request.data.get('mid')])
        meeting = self.get_my_serializer_data(request)
        data = self.app_class.update_by_mid(meeting)
        return ret_json(data=data)


class ForceEndMeetingView(GenericAPIView):
    """强制结束会议（内部API）- 统一接口

    请求参数（POST body）：
    - 非周期会议: {"meeting_id": 123}
    - 周期子会议: {"meeting_id": 123, "sub_id": "xxx"}
    """
    serializer_class = EmptySerializers
    queryset = MeetingDao.get_queryset().filter(is_delete=0)

    @capture_my_validation_exception
    def post(self, request, *args, **kwargs):
        meeting_id = request.data.get('meeting_id')
        sub_id = request.data.get('sub_id')

        if not meeting_id:
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

        meeting = self.queryset.filter(id=meeting_id).first()
        if not meeting:
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

        meeting_adapter = MeetingAdapterImpl()
        meeting_dict = model_to_dict(meeting)

        if sub_id:
            # 强制结束周期子会议
            sub_meeting = MeetingCycleSubMeetingDao.get_all().filter(sub_id=sub_id).first()
            if not sub_meeting:
                raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

            meeting_dict["sub_id"] = sub_id
            meeting_adapter.force_end_meeting(meeting_dict)

            # 清除子会议超时状态
            MeetingCycleSubMeetingDao.clear_overtime_status(sub_id)

            return ret_json(data={"message": "Sub meeting force ended successfully"})
        else:
            # 强制结束非周期会议
            meeting_adapter.force_end_meeting(meeting_dict)

            if meeting.is_cycle:
                # 周期会议：清除所有正在进行中的子会议的超时状态
                sub_meetings = MeetingCycleSubMeetingDao.get_by_mid(meeting.mid)
                for sub in sub_meetings:
                    if sub.get('is_ongoing') or sub.get('is_overtime'):
                        MeetingCycleSubMeetingDao.clear_overtime_status(sub.get('sub_id'))
            else:
                # 非周期会议
                MeetingDao.clear_overtime_status(meeting_id)

            return ret_json(data={"message": "Meeting force ended successfully"})
