import time
from parrot_v2.dal.aliyun_oss import oss_sington


def get_media_url():
    '''
        return {
            'item_name':
            'subtitle_url':, 
            'audio_url':, 
            'video_url':, 
            'expiration_time':timestamp
        }
    '''
    item_name = 'apu_hertz_weekly_20240412'
    subtitle_url = oss_sington.get_object_url(f'{item_name}.vtt')
    audio_url = oss_sington.get_object_url(f'{item_name}.mp3')
    video_url = oss_sington.get_object_url(f'{item_name}.mp4')
    return {
        'item_name': item_name,
        'subtitle_url': subtitle_url,
        'audio_url': audio_url,
        'video_url': video_url,
        'expiration_time': time.time() + oss_sington.get_expire_sec(),
    }
