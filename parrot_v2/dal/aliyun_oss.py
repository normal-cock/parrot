import oss2
from oss2.credentials import StaticCredentialsProvider
from parrot_v2.dal.aliyun_sts import aliyun_sts_sington


class OSSSington:
    def __init__(self) -> None:
        self._bucket = self._get_bucket()

    def get_object_url(self, obj_name):
        # 生成下载文件的签名URL，有效时间为3600秒。
        # 设置slash_safe为True，OSS不会对Object完整路径中的正斜线（/）进行转义，此时生成的签名URL可以直接使用。
        url = self._bucket.sign_url('GET', obj_name, 3600, slash_safe=True)
        return url
        # print('签名URL的地址为：', url)

    def list_file(self):
        # 列举Bucket下的所有文件。
        for obj in oss2.ObjectIteratorV2(self._bucket):
            print(obj.key)

    def _get_bucket(self):
        token_info, err_string = aliyun_sts_sington.get_token_info()
        if err_string:
            raise Exception(err_string)
        auth = oss2.ProviderAuthV4(StaticCredentialsProvider(
            access_key_id=token_info['ACCESS_KEY_ID'],
            access_key_secret=token_info['ACCESS_KEY_SECRET'],
            security_token=token_info['SESSION_TOKEN'],
        ))

        # 填写Bucket所在地域对应的Endpoint
        endpoint = 'https://oss-cn-beijing.aliyuncs.com'
        # 填写Endpoint对应的Region信息，例如cn-hangzhou。
        region = 'cn-beijing'

        # 填写Bucket名称。
        bucket = oss2.Bucket(auth, endpoint, 'dae-parrot', region=region)
        return bucket


oss_sington = OSSSington()

if __name__ == '__main__':
    # 通过list来验证权限
    oss_sington.list_file()
    print(oss_sington.get_object_url('audio.vtt'))
    print(oss_sington.get_object_url('audio.mp3'))
