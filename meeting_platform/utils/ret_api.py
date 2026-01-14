#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import logging
import traceback
from functools import wraps
from django.http import JsonResponse
from django.utils.encoding import force_str
from rest_framework import status
from rest_framework.exceptions import ErrorDetail, APIException, ValidationError, AuthenticationFailed
from django.utils.translation import gettext_lazy as _

from meeting_platform.utils.ret_code import RetCode, set_current_request, clear_request_language

logger = logging.getLogger('log')


class MyValidationError(APIException):
    """define the 400 error"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail=None, code=None, *args):
        self.detail_code = detail
        if isinstance(detail, int):
            detail = RetCode.get_name_by_code(detail)
            if len(args) > 0:
                detail = detail % args
        elif detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        text = force_str(detail)
        self.detail = ErrorDetail(text, code)


class MyNoPermission(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Prohibited Operations.')
    default_code = 'forbidden'

    def __init__(self, detail=None, code=None):
        self.detail_code = detail
        if isinstance(detail, int):
            detail = RetCode.get_name_by_code(detail)
        elif detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        text = force_str(detail)
        self.detail = ErrorDetail(text, code)


class MyInnerError(APIException):
    """define the 500 error"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _('inner error.')
    default_code = 'invalid'

    def __init__(self, detail=None, code=None):
        self.detail_code = detail
        if isinstance(detail, int):
            detail = RetCode.get_name_by_code(detail)
        elif detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        text = force_str(detail)
        self.detail = ErrorDetail(text, code)


class MyInnerResult(APIException):
    status_code = status.HTTP_200_OK
    default_detail = _('success.')
    default_code = 'success'

    def __init__(self, code=None, msg=None):
        if code:
            self.code = code
        else:
            self.code = 200
        if isinstance(msg, int):
            self.msg = RetCode.get_name_by_code(msg)
            self.en_msg = RetCode.get_name_by_code(msg, True)
        else:
            self.msg = None
            self.en_msg = None

    def to_ret_json(self):
        return ret_json(code=self.code, msg=self.msg, en_msg=self.en_msg)


def ret_json(code=200, msg="success", data=None, en_msg=None, **kwargs):
    """return the json data"""
    ret_dict = {'code': code, 'msg': msg, "data": data}
    if en_msg:
        ret_dict["en_msg"] = en_msg
    ret_dict.update(kwargs)
    return JsonResponse(ret_dict)


def capture_my_validation_exception(fn):
    """capture my define exception"""
    def set_language(args):
        """set language"""
        request = None
        if args:
            # Django视图函数通常第一个参数是request
            # 或者在类方法中第二个参数是request（self是第一个）
            for arg in args:
                if hasattr(arg, 'META') and hasattr(arg, 'method'):
                    request = arg
                    break
            # 如果第一个参数不是request，检查第二个参数
            if not request and len(args) > 1:
                second_arg = args[1]
                if hasattr(second_arg, 'META') and hasattr(second_arg, 'method'):
                    request = second_arg
        # 设置语言上下文
        if request:
            language = request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')
            set_current_request(language)


    @wraps(fn)
    def inner(*args, **kwargs):
        """the inner function"""
        try:
            set_language(args)
            return fn(*args, **kwargs)
        except (MyValidationError, ValidationError, AuthenticationFailed) as e:
            logger.error("capture_my_validation_exception:{} e:{} {}".format(fn.__name__, e,
                                                                             traceback.format_exc()))
            raise e
        except MyNoPermission as e:
            logger.error("capture_my_validation_exception MyNoPermission:{} e:{} {}".format(fn.__name__, e,
                                                                                            traceback.format_exc()))
            raise MyNoPermission(RetCode.STATUS_MEETING_NO_PERMISSION)
        except (ValueError, TypeError) as e:
            logger.error("capture_my_validation_exception ValueError:{} e:{} {}".format(fn.__name__, e,
                                                                                        traceback.format_exc()))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        except MyInnerResult as e:
            logger.error("capture_my_validation_exception MyInnerResult:{} e:{} {}".format(fn.__name__, e,
                                                                                           traceback.format_exc()))
            return e.to_ret_json()
        except Exception as e:
            logger.error("exception:{}, traceback:{}".format(e, traceback.format_exc()))
            raise MyInnerError(RetCode.INTERNAL_ERROR)
        finally:
            clear_request_language()
    return inner
