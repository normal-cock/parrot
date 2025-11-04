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


def translate(content_list: typing.List[str]) -> typing.Tuple[typing.List[str], str]:
    content_str = ",,".join(content_list)
    # content_str = json.dumps(content_list)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "将该字幕列表翻译成中文，保持“,,”分割的格式和元素数量不变",
            },
            {"role": "user", "content": content_str},
        ],
    )
    result_string = completion.choices[0].message.content
    result_string = result_string.replace("，", ",")
    result_list = result_string.split(",,")
    if len(result_list) != len(content_list):
        # 按照长度等分
        result_string = result_string.replace(",,", ",")
        logger.warning(
            f"content_list={content_str}||"
            + f"result_list={result_string}||invalid result so try to split from the middle"
        )
        return split_list(result_string, len(content_list))
    return result_list, ""


def trans_vtt(vtt_file, output_file) -> str:
    subs = pysubs2.load(vtt_file)
    # subs = subs[:80]
    new_subs = pysubs2.SSAFile()
    origin_content_list = [s.text for s in subs]
    i = 0
    result_list = []
    while _Step * i < len(origin_content_list):
        begin = _Step * i
        end = _Step * (i + 1)
        sub_content_list = origin_content_list[begin:end]
        begin_time = time.time()

        sub_result, err_string = translate(sub_content_list)
        cost = round(time.time() - begin_time, 2)
        if len(err_string) != 0:
            logger.error(f"err_string={err_string}||translate error")
            break
        if len(sub_result) != len(sub_content_list):
            for i in enumerate(sub_content_list):
                origin_txt = sub_content_list[i]
                result_txt = ""
                if i < len(sub_result):
                    result_txt = sub_result[i]
                logger.error(f"index {i}: {origin_txt}||{result_txt}")
            break
        result_list += sub_result
        logger.info(
            "finished %.2f%%, (%d, %fs)",
            100 * len(result_list) / float(len(subs)),
            len(sub_result),
            cost,
        )
        i += 1

    if len(result_list) != len(subs):
        return "trans_vtt error"
    for i, s in enumerate(subs):
        s.text = result_list[i]
        new_subs.append(s)
    # import ipdb
    # ipdb.set_trace()
    new_subs.save(output_file, format_="vtt")
    return ""


def split_list(input_list, chunk_count):
    if len(input_list) < chunk_count:
        return "", "unable to split because input is too short"
    chunk_size = math.ceil(len(input_list) / chunk_count)
    return [
        input_list[i * chunk_size : (i + 1) * chunk_size] for i in range(chunk_count)
    ], ""


def split_eventlist_into_chuck(event_list):
    """
    贪心策略。停止的条件是满足如下任意条件
    * 时间长度大于 n s
    * 单词数量大于 3n 个
    * 单词数量大于2n且以点号结尾
    * 当前的end距离下次event的start超过5s
    """
    n = 6

    chuck_list = []
    crt_chuck = []
    crt_chuck_start_e = None
    crt_chuck_token_len = 0
    last_e_end = 0
    for e in event_list:
        # import ipdb

        # ipdb.set_trace()
        if (e.start - last_e_end > 5000) and (len(crt_chuck) > 0):
            chuck_list.append(crt_chuck)
            crt_chuck = []
            crt_chuck_start_e = e
            crt_chuck_token_len = 0

        crt_chuck.append(e)
        crt_chuck_token_len += len(e.text.split())
        if crt_chuck_start_e is None:
            crt_chuck_start_e = e

        if (
            e.end - crt_chuck_start_e.start > n * 1000
            or crt_chuck_token_len > 3 * n
            or (crt_chuck_token_len >= 1.5 * n and e.text.strip().endswith("."))
        ):
            chuck_list.append(crt_chuck)
            crt_chuck = []
            crt_chuck_start_e = None
            crt_chuck_token_len = 0
        last_e_end = e.end
    else:
        if len(crt_chuck) > 0:
            chuck_list.append(crt_chuck)

    return chuck_list, ""


def merge_vtt(vtt_file, output_file):
    subs = pysubs2.load(vtt_file)
    new_subs = pysubs2.SSAFile()
    chunk_list, err_string = split_eventlist_into_chuck(subs)
    if len(err_string) != 0:
        raise Exception(err_string)
    for sub_events in chunk_list:
        first_e = sub_events[0]
        last_e = sub_events[-1]
        sub_text_list = [e.text for e in sub_events]
        text = " ".join(sub_text_list)
        e = pysubs2.SSAEvent(start=first_e.start, end=last_e.end, text=text)
        new_subs.append(e)
    new_subs.save(output_file, format_="vtt")


if __name__ == "__main__":
    # content = [
    #     "In May 1914, a Bosnian student, Gavrilo Princip,",
    #     "came here with a Browning pistol",
    #     "for some target practice."]
    # print(translate(content))
    name = "Interview About Tim Cook by Dua Lipa-2023"
    vtt_e = "tmp/Interview About Tim Cook by Dua Lipa-2023.vtt"
    long_vtt_e = f"tmp/{name}-e.vtt"
    long_vtt_c = f"tmp/{name}-c.vtt"
    merge_vtt(vtt_e, long_vtt_e)
    trans_vtt(long_vtt_e, long_vtt_c)
