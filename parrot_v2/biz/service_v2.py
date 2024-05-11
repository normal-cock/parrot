import time
import uuid
from sqlalchemy import desc
from parrot_v2 import Session, DEBUG, PW
from parrot_v2.model import Item
from parrot_v2.dal.aliyun_oss import oss_sington


def get_media_url(item_id):
    '''
        return {
            'item_id':
            'subtitle_url':, 
            'audio_url':, 
            'video_url':, 
            'expiration_time':timestamp
        }, err_string
    '''
    session = Session()
    item = session.query(Item).filter(
        Item.item_id == item_id).one_or_none()
    if item == None:
        return {}, f'{item_id} not found'
    adjustment = item.subtitle_adjustment
    subtitle_url = oss_sington.get_object_url(f'{item_id}.vtt')
    audio_url = oss_sington.get_object_url(f'{item_id}.mp3')
    video_url = oss_sington.get_object_url(f'{item_id}.mp4')

    session.close()
    return {
        'item_id': item_id,
        'subtitle_url': subtitle_url,
        'audio_url': audio_url,
        'video_url': video_url,
        'adjustment': adjustment,
        'expiration_time': time.time() + oss_sington.get_expire_sec(),
    }, ''


def get_item_total() -> int:
    session = Session()
    total_count = session.query(Item).count()
    session.close()
    return total_count


def get_item_list(offset, per_page):
    '''
        return item_list
    '''
    session = Session()
    item_list = session.query(Item).order_by(desc(Item.created_time)).offset(
        offset).limit(per_page).all()
    result_list = []
    for item in item_list:
        result_list.append({
            'create_time': item.created_time.strftime('%Y-%m-%d'),
            'item_name': item.item_name,
            'url': f'{PW}/{item.item_id}',
        })
    session.close()
    return result_list


def add_item(item_name, item_id, adjustment: float, item_type: int):
    session = Session()
    item = Item.new_item(
        item_name=item_name,
        item_id=item_id,
        item_type=item_type,
        adjustment=adjustment,
    )
    session.add(item)
    session.commit()
    session.close()
    return True
