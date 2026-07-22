import nonebot
from nonebot.adapters.feishu import Adapter as FEISHUAdapter
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)
driver.register_adapter(FEISHUAdapter)


nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    try:
        nonebot.run()
    except KeyboardInterrupt:
        pass
    except BaseExceptionGroup:
        pass
