import time
import os
import typing
import math
import pysubs2
from volcenginesdkarkruntime import Ark
from parrot_v2.util import logger

# doubao pro
model = "ep-20250215214655-hwwv7"
# deepseek v3
model = "ep-20250217140128-vrzc7"

client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
    timeout=120,
    max_retries=2,
)

_Step = 10


def split_list(input_list, chunk_count):
    if len(input_list) < chunk_count:
        return '', 'unable to split because input is too short'
    chunk_size = math.ceil(len(input_list) / chunk_count)
    return [input_list[i*chunk_size:(i+1)*chunk_size] for i in range(chunk_count)], ''


def translate(
    content_list: typing.List[str]
) -> typing.Tuple[typing.List[str], str]:
    content_str = ',,'.join(content_list)
    # content_str = json.dumps(content_list)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "将该字幕列表翻译成中文，保持“,,”分割的格式和元素数量不变"
            },
            {"role": "user", "content": content_str},
        ],
    )
    result_string = completion.choices[0].message.content
    result_string = result_string.replace('，', ',')
    result_list = result_string.split(',,')
    if len(result_list) != len(content_list):
        # 按照长度等分
        result_string = result_string.replace(',,', ',')
        logger.warning(f'content_list={content_str}||' +
                       f'result_list={result_string}||invalid result so try to split from the middle')
        return split_list(result_string, len(content_list))
    return result_list, ''


def translate2(
    content: str
) -> str:
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "将该字幕内容翻译成中文，保持格式不变"},
            {"role": "user", "content": content},
        ],
    )
    return completion.choices[0].message.content


def trans_vtt(vtt_file, output_file) -> str:
    subs = pysubs2.load(vtt_file)
    # subs = subs[:80]
    new_subs = pysubs2.SSAFile()
    origin_content_list = [s.text for s in subs]
    i = 0
    result_list = []
    while _Step*i < len(origin_content_list):
        begin = _Step*i
        end = _Step*(i+1)
        sub_content_list = origin_content_list[begin:end]
        begin_time = time.time()

        sub_result, err_string = translate(sub_content_list)
        cost = round(time.time() - begin_time, 2)
        if len(err_string) != 0:
            logger.error(f'err_string={err_string}||translate error')
            break
        if len(sub_result) != len(sub_content_list):
            for i in enumerate(sub_content_list):
                origin_txt = sub_content_list[i]
                result_txt = ''
                if i < len(sub_result):
                    result_txt = sub_result[i]
                logger.error(f'index {i}: {origin_txt}||{result_txt}')
            break
        result_list += sub_result
        logger.info('finished %.2f%%, (%d, %fs)',
                    100*len(result_list)/float(len(subs)),
                    len(sub_result),
                    cost)
        i += 1

    if len(result_list) != len(subs):
        return 'trans_vtt error'
    for i, s in enumerate(subs):
        s.text = result_list[i]
        new_subs.append(s)
    # import ipdb
    # ipdb.set_trace()
    new_subs.save(output_file, format_='vtt')
    return ''


def trans_vtt2(vtt_file, output_file) -> str:
    subs = pysubs2.load(vtt_file)
    # subs = subs[:80]
    new_subs = pysubs2.SSAFile()
    i = 0
    result_list = []
    while _Step*i < len(subs):
        begin = _Step*i
        end = _Step*(i+1)
        sub_content_list = subs[begin:end]
        sub_file = pysubs2.SSAFile()
        for s in sub_content_list:
            sub_file.append(s.copy())
        sub_content = sub_file.to_string('vtt')
        begin_time = time.time()
        sub_result = translate2(sub_content)
        cost = round(time.time() - begin_time, 2)
        sub_result_file = pysubs2.SSAFile.from_string(sub_result, 'vtt')
        if len(sub_result_file) != len(sub_file):
            for i in range(len(sub_file)):
                origin_txt = sub_file[i].text
                result_txt = ''
                if i < len(sub_result_file):
                    result_txt = sub_result_file[i].text
                logger.error(f'index {i}: {origin_txt}||{result_txt}')
            break

        result_list += sub_result_file.events
        logger.info('finished %.2f%%, (%d, %fs)',
                    100*len(result_list)/float(len(subs)),
                    len(sub_file),
                    cost)
        i += 1

    if len(result_list) != len(subs):
        return 'trans_vtt error'
    for s in result_list:
        new_subs.append(s)
    new_subs.save(output_file, format_='vtt')
    return ''


def merge_vtt(vtt_file, output_file):
    subs = pysubs2.load(vtt_file)
    new_subs = pysubs2.SSAFile()
    chunk_list, err_string = split_list(subs, len(subs)//2)
    if len(err_string) != 0:
        raise Exception(err_string)
    for sub_events in chunk_list:
        first_e = sub_events[0]
        last_e = sub_events[-1]
        sub_text_list = [e.text for e in sub_events]
        text = ' '.join(sub_text_list)
        e = pysubs2.SSAEvent(start=first_e.start, end=last_e.end, text=text)
        new_subs.append(e)
    new_subs.save(output_file, format_='vtt')


if __name__ == '__main__':
    # content = [
    #     "In May 1914, a Bosnian student, Gavrilo Princip,",
    #     "came here with a Browning pistol",
    #     "for some target practice."]
    # print(translate(content))
    vtt_e = 'tmp/BH Annual Shareholders Meeting 2024-e.vtt'
    long_vtt_e = 'tmp/BH Annual Shareholders Meeting 2024-long-e.vtt'
    vtt_c = 'tmp/BH Annual Shareholders Meeting 2024-c.vtt'
    long_vtt_c = 'tmp/BH Annual Shareholders Meeting 2024-long-c.vtt'
    # merge_vtt(vtt_e, long_vtt_e)
    trans_vtt(long_vtt_e, long_vtt_c)
