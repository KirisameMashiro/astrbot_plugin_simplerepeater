import random
import asyncio

import astrbot.api.message_components as Comp
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain


@register("simplerepeater", "KirisameMashiro", "一个简单的复读插件", "1.3")
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

        self.repeat_users = {}  # 用户白名单处理 改为使用 dict
        for item in self.repeat_user_whitelist:
            try:
                key, value = item.split(",", 1)
                # print(f"key:{key},value:{value}")
                self.repeat_users[key] = value
            except ValueError:
                logger.warning(f"用户白名单格式错误,已跳过:{item}")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)  # 接收群事件
    async def repeat(self, event: AstrMessageEvent):
        """复读特定群友消息"""
        message = event.message_obj
        group_id = message.session_id
        sender_id = message.sender.user_id
        chain = list(message.message)
        username_chain = Comp.Plain("")

        MESSAGE_TYPE = {"Forward": "[聊天记录]", "Record": "[语音消息]", "Video": "[视频]"}

        if (
            self.repeat_group_whitelist and group_id not in self.repeat_group_whitelist
        ):  # 群白名单过滤
            # print(f"群{group_id}不在白名单中")
            return
        if self.repeat_users:  # 用户白名单过滤
            user_name = self.repeat_users.get(sender_id)
            if user_name is None:
                # print(f"用户{sender_id}不在白名单中")
                return
            else:
                username_chain = Comp.Plain(f"（{user_name}）")  # 追加用户名
        for word in self.repeat_words_blacklist:  # 屏蔽词过滤
            if word in event.message_str:
                await asyncio.sleep(1.5)
                await event.send(
                    MessageChain([Comp.Plain(f"触发屏蔽词:{word}"), username_chain])
                )
                return

        # print(f"raw_message:{message.raw_message}")  # 平台下发的原始消息
        # print(f"message:{chain}") #消息链

        first_type = str(chain[0].type).split(".")[
            -1
        ]  # 获取第一段消息类型 用于判断复读逻辑
        if first_type == "Reply":  # 优先判断是否为回复类型 编写回复消息链
            reply_id = chain[0].id
            # print(f"reply_id:{reply_id}")
            reply_chain = [Comp.Reply(id=reply_id)]
            for comp in chain[1:]:
                comp_type = str(comp.type).split(".")[-1]
                if comp_type in MESSAGE_TYPE:
                    reply_chain.append(Comp.Plain(MESSAGE_TYPE[comp_type]))
                elif (comp_type == "Image"):
                    reply_chain.append(Comp.Plain("[图片]"))
                else:
                    reply_chain.append(comp)
            chain = reply_chain
        else:
            new_chain = []
            for comp in chain:
                comp_type = str(comp.type).split(".")[-1]
                if comp_type in MESSAGE_TYPE:
                    new_chain.append(Comp.Plain(MESSAGE_TYPE[comp_type]))
                elif (comp_type == "Image" and message.raw_message["message"][0]["data"]["sub_type"] == 0): # 不过滤动画表情
                    new_chain.append(Comp.Plain("[图片]"))
                else:
                    new_chain.append(comp)
            chain = new_chain

        random_time = random.uniform(2.0, 4.0)
        await asyncio.sleep(random_time)  # 延迟发送

        chain.append(username_chain)
        await event.send(MessageChain(chain))

        if first_type == "Json":  # 特殊信息追加提示(如qq小程序)
            await asyncio.sleep(1)
            await event.send(MessageChain([Comp.Plain("发送人:"), username_chain]))

    @filter.command("repeater_test")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def repeater_test(self, event: AstrMessageEvent):
        """测试复读机状态"""
        await event.send(MessageChain([Comp.Plain("Success")]))