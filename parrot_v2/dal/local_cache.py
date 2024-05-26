import datetime
import diskcache as dc
import json
from typing import List


class CustmLocalCache(object):
    def __init__(self, dir) -> None:
        self._duration = 2*24*60*60
        self._cache = dc.Cache(dir)
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
