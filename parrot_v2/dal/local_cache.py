import datetime
import diskcache as dc
import json
from typing import List
from parrot_v2.util import logger


class CustmLocalCache(object):
    def __init__(self, dir) -> None:
        self._duration = 2*24*60*60
        self._cache = dc.Cache(dir)
        self._lock = dc.Lock(self._cache, 'heartbeat-lock')
        # pass

    def _gen_rplan_key(self) -> str:
        return f'rplan_cache:{datetime.date.today()}'

    def _gen_rplan_last_index_key(self) -> str:
        return f'last_reviewed_index:{datetime.date.today()}'

    def get_rplan_today(self) -> List[List[int]]:
        '''return [[], []]'''
        return json.loads(self._cache.get(self._gen_rplan_key(), '[]'))

    def set_rplan_today(self, rplan: List[List[int]]):
        '''
            rplan: [[], []]
        '''
        self._cache.set(self._gen_rplan_key(), json.dumps(
            rplan), expire=self._duration)

    def get_rplan_last_index_today(self) -> int:
        '''
            这里的index是未review的rplan里面的第一个chuck的上次review了的index
                如果该chunk都未review过，则为-1
        '''
        return int(self._cache.get(self._gen_rplan_last_index_key(), '-1'))

    def set_rplan_last_index_today(self, reviewed_index: int):
        self._cache.set(
            self._gen_rplan_last_index_key(),
            str(reviewed_index), expire=self._duration
        )

    def reset_rplan_last_index_today(self):
        '''reset to -1'''
        self._cache.set(
            self._gen_rplan_last_index_key(),
            '-1', expire=self._duration
        )

    def _gen_erplan_key(self) -> str:
        return f'erplan_cache:{datetime.date.today()}'

    def _gen_erplan_last_index_key(self) -> str:
        return f'last_erplan_index:{datetime.date.today()}'

    def get_erplan_today(self) -> List[int]:
        '''return [meaning_id, meaning_id, ]'''
        return json.loads(self._cache.get(self._gen_erplan_key(), '[]'))

    def set_erplan_today(self, erplan: List[int]):
        '''
            erplan: [meaning_id, meaning_id, ]
        '''
        self._cache.set(self._gen_erplan_key(), json.dumps(
            erplan), expire=self._duration)

    def get_erplan_last_index_today(self) -> int:
        '''
            这里的index是以review的erplan的index，-1代表还未开始
        '''
        return int(self._cache.get(self._gen_erplan_last_index_key(), '-1'))

    def set_erplan_last_index_today(self, reviewed_index: int) -> bool:
        with self._lock:
            index_key = self._gen_erplan_last_index_key()
            old_er_index_str = self._cache.get(index_key)
            if old_er_index_str == None:
                if reviewed_index == 0:
                    self._cache.set(
                        index_key,
                        str(reviewed_index), expire=self._duration
                    )
                    return True
                else:
                    return False
            else:
                old_er_index = int(old_er_index_str)
                if old_er_index + 1 == reviewed_index:
                    self._cache.set(
                        index_key,
                        str(reviewed_index), expire=self._duration
                    )
                    return True
            return False

    def update_item_heartbeat(self, item_id, hb_dict):
        '''
            hb_data {
                "version":0, // auto increase
                "cue_index":22, // 
                "adjust_st": 0.1, // float
                "adjust_et": 0.1, // float
            }
            return bool, hb_dict
                bool, if update successfully
                hb_dict, final data in the db
        '''
        key = f'hb:{item_id}'
        hb_data = json.dumps(hb_dict)
        with self._lock:
            old_hb = self._cache.get(key)
            if old_hb == None:
                self._cache.set(key, hb_data, tag='hb')
                return True, hb_dict
            old_hb_dict = json.loads(old_hb)
            if hb_dict['version'] == (old_hb_dict['version'] + 1):
                self._cache.set(key, hb_data, tag='hb')
                return True, hb_dict
            else:
                return False, old_hb_dict
