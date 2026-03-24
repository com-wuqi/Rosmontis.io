import os

from nonebot.log import logger

_cwd_dir = os.path.abspath(os.path.dirname(__file__))
_md_dir = os.path.join(_cwd_dir, "md_prompts")
_tool_system_prompts_list = []
_flie_list = [
    os.path.join(_md_dir, f) for f in os.listdir(_md_dir)
    if os.path.isfile(os.path.join(_md_dir, f))
       and f.endswith(".md")
]
for _md_file in _flie_list:
    with open(_md_file, encoding="utf-8") as f:
        logger.debug(_md_file)
        _tool_system_prompts_list.append(
            {"role": "system", "content": f.read()}
        )

tool_system_prompts_list = _tool_system_prompts_list
