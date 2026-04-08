#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

import threading

_thread_locals = threading.local()


def get_current_request():
    if hasattr(_thread_locals, 'http_accept_language'):
        return getattr(_thread_locals, 'http_accept_language', None)
    return None

def set_current_request(http_accept_language):
    _thread_locals.http_accept_language = http_accept_language

def clear_request_language():
    _thread_locals.http_accept_language = None

class RetCodeBase:
    EN_OPERATION = dict()
    CN_OPERATION = dict()

    @classmethod
    def _is_language_en(cls):
        request_language = get_current_request()
        print(f'request_language: {request_language}')
        if request_language == 'en':
            return True
        else:
            return False

    @classmethod
    def get_name_by_code(cls, code):
        if cls._is_language_en():
            return cls.EN_OPERATION.get(code)
        else:
            return cls.CN_OPERATION.get(code)

    @classmethod
    def get_code_by_name(cls, name):
        if cls._is_language_en():
            temp = {value: key for key, value in cls.EN_OPERATION.items()}
            return temp.get(name, str())
        else:
            temp = {value: key for key, value in cls.CN_OPERATION.items()}
            return temp.get(name, str())


class RetCode(RetCodeBase):
    # common
    STATUS_SUCCESS = 0
    STATUS_PARAMETER_ERROR = -1
    STATUS_PARTIAL_SUCCESS = -2
    INTERNAL_ERROR = -3
    SYSTEM_BUSY = -4
    NAME_NOT_STANDARD = -5
    RESULT_IS_EMPTY = -6
    STATUS_PARAMETER_CORRESPONDING_ERROR = -7
    STATUS_FAILED = -8
    INFORMATION_CHANGE_ERROR = -9
    STATUS_START_LT_END = -10
    STATUS_START_GT_NOW = -11
    STATUS_START_LT_LIMIT = -12
    STATUS_START_VALID_URL = -13
    STATUS_START_VALID_XSS = -14
    STATUS_START_VALID_CRLF = -15
    STATUS_AUTH_FAILED = -16
    STATUS_INVALID_CONTENT_FAILED = -17

    STATUS_FACILITY_BIT_MASK = 16
    STATUS_FACILITY_MEETING = 1 << STATUS_FACILITY_BIT_MASK

    # sub module: meeting
    STATUS_MEETING_INVALID_EMAIL = STATUS_FACILITY_MEETING + 0
    STATUS_MEETING_DATE_CONFLICT = STATUS_FACILITY_MEETING + 1
    STATUS_MEETING_CANNOT_BE_OPERATE = STATUS_FACILITY_MEETING + 2
    STATUS_MEETING_NO_PERMISSION = STATUS_FACILITY_MEETING + 3
    STATUS_MEETING_NOT_EXIST = STATUS_FACILITY_MEETING + 4
    STATUS_MEETING_FAILED_UPDATE = STATUS_FACILITY_MEETING + 5
    STATUS_MEETING_CANNOT_BE_OPERATE_BY_EXPIRED = STATUS_FACILITY_MEETING + 6
    STATUS_MEETING_CREATE_COUNT_LIMIT = STATUS_FACILITY_MEETING + 7
    STATUS_MEETING_MODIFY_COUNT_LIMIT = STATUS_FACILITY_MEETING + 8
    STATUS_MEETING_PUT_RUNNING = STATUS_FACILITY_MEETING + 9
    STATUS_MEETING_REPEAT_FAILED = STATUS_FACILITY_MEETING + 10
    STATUS_MEETING_CANNOT_DELETE_FAILED = STATUS_FACILITY_MEETING + 11
    STATUS_MEETING_IN_HALF_YEAR_FAILED = STATUS_FACILITY_MEETING + 12
    STATUS_MEETING_DATE_NOT_IN_RANGE_FAILED = STATUS_FACILITY_MEETING + 13
    STATUS_MEETING_PUT_INVALID_DATE = STATUS_FACILITY_MEETING + 14
    STATUS_MEETING_PRIVATE_SUPPORT_TYPE = STATUS_FACILITY_MEETING + 15
    STATUS_MEETING_PRIVATE_SUPPORT_CYCLE = STATUS_FACILITY_MEETING + 16
    STATUS_MEETING_PRIVATE_SUPPORT_EMAIL_LIST = STATUS_FACILITY_MEETING + 17

    EN_OPERATION = {
        # common
        STATUS_SUCCESS: "Operation successful.",
        STATUS_PARTIAL_SUCCESS: "Partially successful, data may be incomplete, please check the cluster for exceptions.",
        STATUS_PARAMETER_ERROR: "Parameter invalid.",
        STATUS_FAILED: "Failed.",
        INTERNAL_ERROR: 'System error. Try again later.',
        SYSTEM_BUSY: 'The system is busy.',
        NAME_NOT_STANDARD: 'name not standard.',
        RESULT_IS_EMPTY: 'The result is empty.',
        STATUS_PARAMETER_CORRESPONDING_ERROR: 'Parameter corresponding invalid.',

        # meetings
        INFORMATION_CHANGE_ERROR: "Meeting status has changed. Refresh and try again.",
        STATUS_MEETING_INVALID_EMAIL: "Enter a valid email address.",
        STATUS_START_LT_END: "The start time must be earlier than the end time.",
        STATUS_START_GT_NOW: "The start time must be later than the current time.",
        STATUS_START_LT_LIMIT: "Book meetings only within 60 days.",
        STATUS_START_VALID_URL: "URLs and XSS tags are not allowed.",
        STATUS_START_VALID_XSS: "XSS tags are not allowed.",
        STATUS_START_VALID_CRLF: "\r, \n, or \r\n is not allowed.",
        STATUS_AUTH_FAILED: "Operation failed. Your account has been logged out.",
        STATUS_INVALID_CONTENT_FAILED: "Invalid input. Please try again.",
        STATUS_MEETING_DATE_CONFLICT: "Meeting time conflict. Reserve 30 minutes between meetings.",
        STATUS_MEETING_CANNOT_BE_OPERATE: "You cannot edit or delete meetings 30 minutes before start.",
        STATUS_MEETING_NO_PERMISSION: "Failed to operate a meeting due to insufficient permissions",
        STATUS_MEETING_CANNOT_BE_OPERATE_BY_EXPIRED: "Operation failed. The meeting has expired.",
        STATUS_MEETING_CREATE_COUNT_LIMIT: "Too many meetings created today. Try again tomorrow.",
        STATUS_MEETING_MODIFY_COUNT_LIMIT: "Meeting edit limit reached.",
        STATUS_MEETING_PUT_RUNNING: "Operation failed. The meeting is in progress.",
        STATUS_MEETING_REPEAT_FAILED: "The meeting already exists.",
        STATUS_MEETING_CANNOT_DELETE_FAILED: "There is only one sub-meeting left in the recurring meeting,"
                                             "Please delete the entire recurring meeting.",
        STATUS_MEETING_IN_HALF_YEAR_FAILED: "Operation failed. Book recurring meetings only within 6 months.",
        STATUS_MEETING_DATE_NOT_IN_RANGE_FAILED: "No matching time found in the recurrence period.",
        STATUS_MEETING_PUT_INVALID_DATE: "The new time conflicts with an adjacent sub-meeting.",
        STATUS_MEETING_NOT_EXIST: "Meeting does not exist",
        STATUS_MEETING_PRIVATE_SUPPORT_TYPE: "Private meetings only support WeLink meetings.",
        STATUS_MEETING_PRIVATE_SUPPORT_CYCLE: "Private meetings only support non-periodic meetings.",
        STATUS_MEETING_PRIVATE_SUPPORT_EMAIL_LIST: "Do not enter SIG mailing list addresses to prevent unauthorized access to the meeting.",
    }

    CN_OPERATION = {
        # common
        STATUS_SUCCESS: "操作成功。",
        STATUS_PARTIAL_SUCCESS: "部分成功，请求数据可能不完整，请检查。",
        STATUS_PARAMETER_ERROR: "参数无效。",
        STATUS_FAILED: "操作失败。",
        INTERNAL_ERROR: '系统出现错误，请稍后重试。',
        SYSTEM_BUSY: '系统繁忙，请稍后重试。',
        NAME_NOT_STANDARD: '非法名字。',
        RESULT_IS_EMPTY: '结果为空。',
        STATUS_PARAMETER_CORRESPONDING_ERROR: '参数响应无效。',
        INFORMATION_CHANGE_ERROR: "系统数据延迟，会议状态已变化，请刷新后重试。",

        # meetings
        STATUS_MEETING_INVALID_EMAIL: "请输入正确的邮箱地址。",
        STATUS_START_LT_END: "会议开始时间应小于结束时间。",
        STATUS_START_GT_NOW: "会议开始时间应大于当前时间。",
        STATUS_START_LT_LIMIT: "仅支持预定60天之内的会议。",
        STATUS_START_VALID_URL: "请勿输入URL链接，XSS标签等内容。",
        STATUS_START_VALID_XSS: "请勿输入XSS标签等内容。",
        STATUS_START_VALID_CRLF: "请勿输入\r\n等内容。",
        STATUS_AUTH_FAILED: "操作失败，您的账号已退登。",
        STATUS_INVALID_CONTENT_FAILED: "检查到您输入的内容不合规，请重新输入。",
        STATUS_MEETING_DATE_CONFLICT: "所选时间段内已有会议冲突，建议您调整会议时间，请勿在其他会议开始或结束半小时内预定会议。",
        STATUS_MEETING_CANNOT_BE_OPERATE: "距离会议开始时间小于半个小时，无法修改或删除。",
        STATUS_MEETING_NO_PERMISSION: "权限不足导致操作会议失败。",
        STATUS_MEETING_CANNOT_BE_OPERATE_BY_EXPIRED: "会议已经过期，操作失败。",
        STATUS_MEETING_CREATE_COUNT_LIMIT: "今日创建会议次数已达上限，请明日再重试。",
        STATUS_MEETING_MODIFY_COUNT_LIMIT: "会议修改次数已达上限。",
        STATUS_MEETING_PUT_RUNNING: "会议正在进行中，无法操作。",
        STATUS_MEETING_REPEAT_FAILED: "您创建的会议已经存在，请勿重复创建。",
        STATUS_MEETING_CANNOT_DELETE_FAILED: "周期性会议目前只剩一场子会议，请删除整个周期性会议。",
        STATUS_MEETING_IN_HALF_YEAR_FAILED: "操作失败，周期性会议仅支持半年内会议。",
        STATUS_MEETING_DATE_NOT_IN_RANGE_FAILED: "重复规则里没有符合条件的时间。",
        STATUS_MEETING_PUT_INVALID_DATE: "修改的时间与相邻子会议时间冲突，请重新修改。",
        STATUS_MEETING_NOT_EXIST: "会议不存在。",
        STATUS_MEETING_PRIVATE_SUPPORT_TYPE: "非公开会议只支持WeLink会议。",
        STATUS_MEETING_PRIVATE_SUPPORT_CYCLE: "非公开会议只支持非周期性会议。",
        STATUS_MEETING_PRIVATE_SUPPORT_EMAIL_LIST: "请勿输入SIG组邮件列表地址，避免无关人员获得会议链接。",

    }
