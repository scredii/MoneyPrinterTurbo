import streamlit as st

st.set_page_config(page_title="MoneyPrinterTurbo", page_icon="🤖", layout="wide",
                   initial_sidebar_state="auto")
import sys
import os
from uuid import uuid4

from loguru import logger
from app.models.schema import VideoParams, VideoAspect, VoiceNames, VideoConcatMode
from app.services import task as tm, llm

hide_streamlit_style = """
<style>#root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
st.title("MoneyPrinterTurbo")
st.write(
    "⚠️ 先在 **config.toml** 中设置 `pexels_api_keys` 和 `llm_provider` 参数，根据不同的 llm_provider，配置对应的 **API KEY**"
)

root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
font_dir = os.path.join(root_dir, "resource", "fonts")
song_dir = os.path.join(root_dir, "resource", "songs")

# st.session_state

if 'video_subject' not in st.session_state:
    st.session_state['video_subject'] = ''
if 'video_script' not in st.session_state:
    st.session_state['video_script'] = ''
if 'video_terms' not in st.session_state:
    st.session_state['video_terms'] = ''


def get_all_fonts():
    fonts = []
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith(".ttf") or file.endswith(".ttc"):
                fonts.append(file)
    return fonts


def get_all_songs():
    songs = []
    for root, dirs, files in os.walk(song_dir):
        for file in files:
            if file.endswith(".mp3"):
                songs.append(file)
    return songs


def init_log():
    logger.remove()
    _lvl = "DEBUG"

    def format_record(record):
        # 获取日志记录中的文件全路径
        file_path = record["file"].path
        # 将绝对路径转换为相对于项目根目录的路径
        relative_path = os.path.relpath(file_path, root_dir)
        # 更新记录中的文件路径
        record["file"].path = f"./{relative_path}"
        # 返回修改后的格式字符串
        # 您可以根据需要调整这里的格式
        record['message'] = record['message'].replace(root_dir, ".")

        _format = '<green>{time:%Y-%m-%d %H:%M:%S}</> | ' + \
                  '<level>{level}</> | ' + \
                  '"{file.path}:{line}":<blue> {function}</> ' + \
                  '- <level>{message}</>' + "\n"
        return _format

    logger.add(
        sys.stdout,
        level=_lvl,
        format=format_record,
        colorize=True,
    )


init_log()

panel = st.columns(3)
left_panel = panel[0]
middle_panel = panel[1]
right_panel = panel[2]

# define cfg as VideoParams class
cfg = VideoParams()

with left_panel:
    with st.container(border=True):
        st.write("**Copywriting**")
        cfg.video_subject = st.text_input("Video Topic (given a keyword, :red [AI auto-generated] video copy)",
                                          value=st.session_state['video_subject']).strip()

        video_languages = [
            ("自动判断（Auto detect）", ""),
        ]
        for lang in ["zh-CN", "zh-TW", "en-US"]:
            video_languages.append((lang, lang))

        selected_index = st.selectbox("Language for generating video scripts (:blue [normally AI will automatically output based on the theme language you enter])）",
                                      index=0,
                                      options=range(len(video_languages)),  # 使用索引作为内部选项值
                                      format_func=lambda x: video_languages[x][0]  # 显示给用户的是标签
                                      )
        cfg.video_language = video_languages[selected_index][1]

        if cfg.video_language:
            st.write(f"Set the AI output copy language to: **:red[{cfg.video_language}]**")

        if st.button("Click to use AI to generate [Video Copy] and [Video Keywords] based on **Topic**.", key="auto_generate_script"):
            with st.spinner("AI正在生成视频文案和关键词..."):
                script = llm.generate_script(video_subject=cfg.video_subject, language=cfg.video_language)
                terms = llm.generate_terms(cfg.video_subject, script)
                st.toast('AI生成成功')
                st.session_state['video_script'] = script
                st.session_state['video_terms'] = ", ".join(terms)

        cfg.video_script = st.text_area(
            "Video copy (:blue [① may not be filled in, use AI to generate ② reasonable use of punctuation breaks to help generate subtitles])",
            value=st.session_state['video_script'],
            height=230
        )
        if st.button("Click to use AI to generate [video keywords] based on **Copy**", key="auto_generate_terms"):
            if not cfg.video_script:
                st.error("请先填写视频文案")
                st.stop()

            with st.spinner("AI is generating video keywords..."):
                terms = llm.generate_terms(cfg.video_subject, cfg.video_script)
                st.toast('AI生成成功')
                st.session_state['video_terms'] = ", ".join(terms)

        cfg.video_terms = st.text_area(
            "Video keywords (:blue [① may not fill in, use AI to generate ② with ** English comma ** separated, only support English])）",
            value=st.session_state['video_terms'],
            height=50)

with middle_panel:
    with st.container(border=True):
        st.write("**Video Settings**")
        video_concat_modes = [
            ("sequential splicing", "sequential"),
            ("Random splicing (recommended)", "random"),
        ]
        selected_index = st.selectbox("Video splicing mode",
                                      index=1,
                                      options=range(len(video_concat_modes)),  # 使用索引作为内部选项值
                                      format_func=lambda x: video_concat_modes[x][0]  # 显示给用户的是标签
                                      )
        cfg.video_concat_mode = VideoConcatMode(video_concat_modes[selected_index][1])

        video_aspect_ratios = [
            ("Vertical 9:16 (Shake video)）", VideoAspect.portrait.value),
            ("Landscape 16:9 (Watermelon Video)", VideoAspect.landscape.value),
            # ("方形 1:1", VideoAspect.square.value)
        ]
        selected_index = st.selectbox("Video Ratio",
                                      options=range(len(video_aspect_ratios)),  # 使用索引作为内部选项值
                                      format_func=lambda x: video_aspect_ratios[x][0]  # 显示给用户的是标签
                                      )
        cfg.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])

        cfg.video_clip_duration = st.selectbox("Maximum duration of video clips (seconds)", options=[2, 3, 4, 5, 6], index=1)
        cfg.video_count = st.selectbox("Number of simultaneous videos generated", options=[1, 2, 3, 4, 5], index=0)
    with st.container(border=True):
        st.write("**Audio Settings**")
        # 创建一个映射字典，将原始值映射到友好名称
        friendly_names = {
            voice: voice.
            replace("female", "女性").
            replace("male", "男性").
            replace("zh-CN", "中文").
            replace("zh-HK", "香港").
            replace("zh-TW", "台湾").
            replace("en-US", "英文").
            replace("Neural", "") for
            voice in VoiceNames}
        selected_friendly_name = st.selectbox("Reading voice", options=list(friendly_names.values()))
        voice_name = list(friendly_names.keys())[list(friendly_names.values()).index(selected_friendly_name)]
        cfg.voice_name = voice_name

        bgm_options = [
            ("background music (BGM) No BGM", ""),
            ("Random background music Random BGM", "random"),
            ("Customized background music Custom BGM", "custom"),
        ]
        selected_index = st.selectbox("background music (BGM)",
                                      index=1,
                                      options=range(len(bgm_options)),  # 使用索引作为内部选项值
                                      format_func=lambda x: bgm_options[x][0]  # 显示给用户的是标签
                                      )
        # 获取选择的背景音乐类型
        bgm_type = bgm_options[selected_index][1]

        # 根据选择显示或隐藏组件
        if bgm_type == "custom":
            custom_bgm_file = st.text_input("Please enter the file path of the customized background music：")
            if custom_bgm_file and os.path.exists(custom_bgm_file):
                cfg.bgm_file = custom_bgm_file
                # st.write(f":red[已选择自定义背景音乐]：**{custom_bgm_file}**")
        cfg.bgm_volume = st.selectbox("Background music volume (0.2 means 20%, background sound should not be too high)）",
                                      options=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], index=2)

with right_panel:
    with st.container(border=True):
        st.write("**Subtitle settings**")
        cfg.subtitle_enabled = st.checkbox("Generate subtitles (if unchecked, none of the following settings will take effect)", value=True)
        font_names = get_all_fonts()
        cfg.font_name = st.selectbox("calligraphic style", font_names)

        subtitle_positions = [
            ("顶部（top）", "top"),
            ("居中（center）", "center"),
            ("底部（bottom，推荐）", "bottom"),
        ]
        selected_index = st.selectbox("Subtitle position",
                                      index=2,
                                      options=range(len(subtitle_positions)),  # 使用索引作为内部选项值
                                      format_func=lambda x: subtitle_positions[x][0]  # 显示给用户的是标签
                                      )
        cfg.subtitle_position = subtitle_positions[selected_index][1]

        font_cols = st.columns([0.3, 0.7])
        with font_cols[0]:
            cfg.text_fore_color = st.color_picker("字幕颜色", "#FFFFFF")
        with font_cols[1]:
            cfg.font_size = st.slider("字幕大小", 30, 100, 60)

        stroke_cols = st.columns([0.3, 0.7])
        with stroke_cols[0]:
            cfg.stroke_color = st.color_picker("描边颜色", "#000000")
        with stroke_cols[1]:
            cfg.stroke_width = st.slider("描边粗细", 0.0, 10.0, 1.5)

start_button = st.button("开始生成视频", use_container_width=True, type="primary")
if start_button:
    task_id = str(uuid4())
    if not cfg.video_subject and not cfg.video_script:
        st.error("视频主题 或 视频文案，不能同时为空")
        st.stop()

    st.write(cfg)

    log_container = st.empty()

    log_records = []


    def log_received(msg):
        with log_container:
            log_records.append(msg)
            st.code("\n".join(log_records))


    logger.add(log_received)

    logger.info("开始生成视频")

    tm.start(task_id=task_id, params=cfg)
