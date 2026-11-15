"""固定正负例校准的证据门槛；相似度不是命中概率或事实判断。"""

VERSION = 'contrast-calibration-20261115-v1'
# 依据已登记 calibration 分组，不用 validation 分组搜索参数。
MIN_SCORE = {'text': 0.78, 'visual': 0.035}
MIN_MARGIN = {'text': -0.015, 'visual': 0.0}
BACKGROUNDS = {
    'text': ('这是一段视频或图片素材', 'This is an image or video.'),
    'visual': ('a television color bars test pattern', 'a blank image with no subject'),
}
