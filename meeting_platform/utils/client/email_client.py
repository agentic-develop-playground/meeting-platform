#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

import smtplib
import traceback
from logging import getLogger


logger = getLogger("log")


class EmailClient(object):
    """EmailClient"""

    def __init__(self, host, port, user, pwd):
        """init smtp client"""
        self.server = smtplib.SMTP(host, port)
        self.server.ehlo()
        self.server.starttls()
        self.server.login(user, pwd)

    def send_message(self, from_str, receive_str, msg, is_close=True):
        """send the message by email client"""
        try:
            return self.server.sendmail(from_str, receive_str, msg.as_string())
        except smtplib.SMTPException as e:
            logger.error("[EmailClient] e:{},traceback:{}".format(e, traceback.format_exc()))
        finally:
            if is_close:
                self.server.quit()
        return None
