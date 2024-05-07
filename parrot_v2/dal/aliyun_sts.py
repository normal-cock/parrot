# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
import os
import time
from datetime import datetime
import re

from typing import List

from alibabacloud_sts20150401.client import Client as Sts20150401Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_sts20150401 import models as sts_20150401_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient


class STSTokenSington:
    '''
        https://ram.console.aliyun.com/overview
        相当于利用openapi, 来让RAM用户parrot来扮演parrot-role角色。
        之后增加授权时, 都给parrot-role增加授权即可, RAM用户parrot只需要STS权限来进行角色扮演
    '''

    def __init__(self):
        self.role_arn = 'acs:ram::1678312063870977:role/parrot-role'
        self.role_session_name = 'parrot-server'
        self.client = STSTokenSington.create_client()
        self._token_info = None
        self._expire_timestamp = 0

    def get_expire_sec(self) -> float:
        return self._expire_timestamp

    def get_token_info(self):
        '''
            return token_info, err_string
                token_info: {'ACCESS_KEY_ID':, 'ACCESS_KEY_SECRET', 'SESSION_TOKEN'}
        '''
        if time.time() < self._expire_timestamp:
            return self._token_info, ''

        assume_role_request = sts_20150401_models.AssumeRoleRequest(
            role_arn=self.role_arn,
            role_session_name=self.role_session_name
        )
        runtime = util_models.RuntimeOptions()
        try:
            # 复制代码运行请自行打印 API 的返回值
            resp = self.client.assume_role_with_options(
                assume_role_request, runtime)
        except Exception as error:
            # 此处仅做打印展示，请谨慎对待异常处理，在工程项目中切勿直接忽略异常。
            # 错误 message
            print(error.message)
            # 诊断地址
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)
        if resp.status_code != 200:
            return None, f'err_status_code={resp.status_code}||body={str(resp.body)}'
        body_dict = resp.body.to_map()
        self._token_info = {
            'ACCESS_KEY_ID': body_dict['Credentials']['AccessKeyId'],
            'ACCESS_KEY_SECRET': body_dict['Credentials']['AccessKeySecret'],
            'SESSION_TOKEN': body_dict['Credentials']['SecurityToken']
        }
        ios_string = body_dict['Credentials']['Expiration']
        ios_string = re.sub(r"Z$", "+00:00", ios_string)
        self._expire_timestamp = datetime.fromisoformat(
            ios_string).timestamp()
        return self._token_info, ''

    @staticmethod
    def create_client() -> Sts20150401Client:
        """
        使用AK&SK初始化账号Client
        @return: Client
        @throws Exception
        """
        # 工程代码泄露可能会导致 AccessKey 泄露，并威胁账号下所有资源的安全性。以下代码示例仅供参考。
        # 建议使用更安全的 STS 方式，更多鉴权访问方式请参见：https://help.aliyun.com/document_detail/378659.html。
        config = open_api_models.Config(
            # 必填，请确保代码运行环境设置了环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID。,
            access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
            # 必填，请确保代码运行环境设置了环境变量 ALIBABA_CLOUD_ACCESS_KEY_SECRET。,
            access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET']
        )
        # Endpoint 请参考 https://api.aliyun.com/product/Sts
        config.endpoint = f'sts.cn-beijing.aliyuncs.com'
        return Sts20150401Client(config)


aliyun_sts_sington = STSTokenSington()

if __name__ == '__main__':
    print(aliyun_sts_sington.get_token_info())
