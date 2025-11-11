import random
import asyncio

import astrbot.api.message_components as Comp
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain


@register("simplerepeater", "KirisameMashiro", "一个简单的复读插件", "1.0")
class RepeatPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.repeat_group_whitelist = config.get(
            "repeat_group_whitelist", []
        )  # 群白名单导入
        self.repeat_user_whitelist = config.get(
            "repeat_user_whitelist", []
        )  # 用户白名单导入
        self.repeat_words_blacklist = config.get(
            "repeat_words_blacklist", []
        )  # 屏蔽词导入

        self.repeat_users = []  # 用户白名单处理
        for item in self.repeat_user_whitelist:
            key, value = item.split(",")
            self.repeat_users.append((key, value))
            # print(f"key:{key},value:{value}")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)  # 接收群事件
    async def repeat(self, event: AstrMessageEvent):
        """复读特定群友消息"""
        message = event.message_obj
        group_id = message.session_id
        sender_id = message.sender.user_id
        chain = message.message
        username_chain = Comp.Plain("")

        if (
            self.repeat_group_whitelist and group_id not in self.repeat_group_whitelist
        ):  # 群白名单过滤
            # print(f"群{group_id}不在白名单中")
            return
        if self.repeat_users:  # 用户白名单过滤
            user_name = next(
                (value for key, value in self.repeat_users if key == sender_id), None
            )
            if user_name is None:
                # print(f"用户{sender_id}不在白名单中")
                return
            else:
                username_chain = Comp.Plain(f"（{user_name}）")  # 追加用户名
        for word in self.repeat_words_blacklist:  # 屏蔽词过滤
            if word in event.message_str:
                await asyncio.sleep(1.5)
                await event.send(
                    MessageChain([Comp.Plain("触发屏蔽词"), username_chain])
                )
                return

        print(f"raw_message:{message.raw_message}")  # 平台下发的原始消息
        # print(f"message:{chain}") #消息链

        chain_type = str(chain[0].type).split(".")[
            -1
        ]  # 获取第一段消息类型 用于判断复读逻辑
        if chain_type == "Forward":
            chain = [Comp.Plain("[聊天记录]")]
        elif (
            chain_type == "Image"
            and message.raw_message["message"][0]["data"]["sub_type"] == 0
        ):  # 不过滤动画表情
            chain = [Comp.Plain("[图片]")]
        elif chain_type == "Record":
            chain = [Comp.Plain("[语音消息]")]
        elif chain_type == "Video":
            chain = [Comp.Plain("[视频]")]

        random_time = (
            random.random() * 5000
            + random.random() * 2000
            + random.random() * 1000
            + 1000
        )
        await asyncio.sleep(random_time / 1000)  # 延迟发送

        chain.append(username_chain)
        await event.send(MessageChain(chain))

        if chain_type == "Json":  # 特殊信息追加提示(如qq小程序)
            await asyncio.sleep(1.5)
            await event.send(MessageChain([Comp.Plain("发送人:"), username_chain]))
