import oss2
import base64
from oss2.credentials import StaticCredentialsProvider
from parrot_v2.dal.aliyun_sts import aliyun_sts_sington


class OSSSington:
    def __init__(self) -> None:
        self._bucket_name = 'dae-parrot'
        # expiration of signed url is also affected by token expiration which
        # is 3600s by default, you can change that in
        # https://ram.console.aliyun.com/roles/detail?roleName=parrot-role
        self._expires = 3600

    def check_existence(self, obj_name) -> bool:
        return self._get_bucket().object_exists(obj_name)

    def get_expire_sec(self) -> float:
        token_expiration = aliyun_sts_sington.get_expire_sec()
        return min(self._expires, token_expiration)

    def get_object_url(self, obj_name):
        # 生成下载文件的签名URL，有效时间为3600秒。
        # 设置slash_safe为True，OSS不会对Object完整路径中的正斜线（/）进行转义，此时生成的签名URL可以直接使用。
        url = self._get_bucket().sign_url('GET', obj_name, self._expires, slash_safe=True)
        return url
        # print('签名URL的地址为：', url)

    def list_file(self):
        # 列举Bucket下的所有文件。
        for obj in oss2.ObjectIteratorV2(self._get_bucket()):
            print(obj.key)

    def extract_audio(self, video_key: str):
        '''
            注意是收费的, 1小时1.5元左右
        '''
        # 对文件example.avi进行音频提取并将提取的音频进行转码。
        name = '.'.join(video_key.split('.')[:-1])
        audio_key = f'{name}.mp3'
        style = 'video/convert,f_mp3,acodec_mp3,ab_100000,vn_1,sn_1'
        process = "{0}|sys/saveas,o_{1},b_{2}".format(
            style,
            oss2.compat.to_string(base64.urlsafe_b64encode(
                oss2.compat.to_bytes(audio_key))).replace('=', ''),
            oss2.compat.to_string(base64.urlsafe_b64encode(
                oss2.compat.to_bytes(self._bucket_name))).replace('=', '')
        )

        # 调用异步流媒体处理接口。
        result = self._get_bucket().async_process_object(video_key, process)
        return result.status

    def _get_bucket(self):
        '''
            注意, 这里的bucket是会过期的, 所以要么不缓存每次都重新生成bucket, 要么将token的过期时间也缓存下来
            不过也没有网络请求 可以不缓存生成的bucket
        '''
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
        bucket = oss2.Bucket(auth, endpoint, self._bucket_name, region=region)
        return bucket


oss_sington = OSSSington()

if __name__ == '__main__':
    # 通过list来验证权限
    print(oss_sington.list_file())
    # print(oss_sington.get_object_url('audio.vtt'))
    # print(oss_sington.get_object_url('audio.mp3'))
    print(oss_sington.extract_audio('test2.mp4'))
