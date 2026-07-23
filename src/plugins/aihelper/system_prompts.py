import os
from pathlib import Path

from nonebot.log import logger

from . import config

_cwd_dir = os.path.abspath(os.path.dirname(__file__))
_md_dir = Path(_cwd_dir) / "md_prompts"
_tool_system_prompts_list = []
_file_list = [
    _md_dir / f
    for f in sorted(os.listdir(_md_dir))
    if os.path.isfile(
        _md_dir / f
    )
       and f.endswith(".md")
       and (config.is_enable_design_prompts or (not f.startswith("design-")))
]
for _md_file in _file_list:
    with Path(_md_file).open(encoding="utf-8") as f:
        logger.debug(f"found a markdown file: {_md_file}")
        _tool_system_prompts_list.append(
            {"role": "system", "content": f.read()}
        )

tool_system_prompts_list = _tool_system_prompts_list
