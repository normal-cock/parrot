import datetime
import uuid
import enum
from sqlalchemy import Column, Float, Enum, Integer, String, DateTime, ForeignKey
from parrot_v2.model import Base

# * [P1]建模
# * [P2]字幕修正时间的存储
# * [P1]播放列表


class ItemType(enum.Enum):
    '''1:MP3 only 2:MP4+MP3'''
    MP3 = 1
    MP4 = 2


class Item(Base):
    __tablename__ = 'player_item'
    id = Column(Integer, primary_key=True)

    # auto generated unique key for item, and used for oss key
    item_id = Column(String(256), unique=True, nullable=False)
    item_name = Column(String(256), nullable=False)
    item_type = Column(Enum(ItemType), default=ItemType.MP3)

    subtitle_adjustment = Column(Float, default=0)

    created_time = Column(DateTime, default=datetime.datetime.now)
    changed_time = Column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    @classmethod
    def new_item(cls, item_name: str, item_id: str, adjustment: float, item_type: int):
        if len(item_id) == 0:
            item_id = str(uuid.uuid4())
        item = Item(
            item_id=item_id,
            item_name=item_name,
            item_type=ItemType(item_type),
            subtitle_adjustment=adjustment,
        )
        return item
