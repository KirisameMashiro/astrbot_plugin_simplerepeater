import random
import asyncio

import astrbot.api.message_components as Comp
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain


@register("simplerepeater", "KirisameMashiro", "一个简单的复读插件", "1.5")
class RepeatPlugin(Star):
    # 消息类型
    MESSAGE_TYPE = {
        "Forward": "[聊天记录]",
        "Record": "[语音消息]",
        "Video": "[视频]",
    }

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
                if comp_type in RepeatPlugin.MESSAGE_TYPE:
                    reply_chain.append(Comp.Plain(RepeatPlugin.MESSAGE_TYPE[comp_type]))
                elif comp_type == "Image":
                    reply_chain.append(Comp.Plain("[图片]"))
                else:
                    reply_chain.append(comp)
            chain = reply_chain
        else:
            chain = self.get_filtered_chain(message, RepeatPlugin.MESSAGE_TYPE)

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
        await event.send(MessageChain([Comp.Plain("Success.")]))

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def display(self, event: AstrMessageEvent):
        """展示回复特定群友时的原消息"""
        message = event.message_obj
        group_id = message.session_id
        chain = list(message.message)
        username = Comp.Plain("")
        origin_chain = []
        display_chain = [(Comp.Plain("原消息："))]

        if (
            self.repeat_group_whitelist and group_id not in self.repeat_group_whitelist
        ):  # 群白名单过滤
            # print(f"群{group_id}不在白名单中")
            return
        for word in self.repeat_words_blacklist:  # 屏蔽词过滤
            if word in event.message_str:
                return

        first_type = str(chain[0].type).split(".")[-1]  # 获取第一段判断是否为回复消息
        if first_type == "Reply":
            comp = chain[0]
            # print(f"comp:{comp}")
            # print(f"repeat_users:{self.repeat_users}")
            sender_id = str(comp.sender_id)  # 获取原消息发送人id
            if sender_id in self.repeat_users:  # 判断原消息发送人是否在白名单中
                for word in self.repeat_words_blacklist:  # 屏蔽词过滤
                    if word in comp.message_str:
                        await asyncio.sleep(1.5)
                        await event.send(
                            MessageChain([Comp.Plain(f"原消息包含屏蔽词:{word}")])
                        )
                        return
                username = Comp.Plain(f"（{self.repeat_users[sender_id]}）")
                origin_chain = comp.chain  # 获取原消息链（暂未做如json的消息处理）
                # print(f"origin_chain:{origin_chain}")
                new_chain = []
                for component in origin_chain:
                    component_type = str(component.type).split(".")[-1]
                    if component_type in RepeatPlugin.MESSAGE_TYPE:
                        new_chain.append(
                            Comp.Plain(RepeatPlugin.MESSAGE_TYPE[component_type])
                        )
                    elif component_type == "Image":
                        new_chain.append(Comp.Plain("[图片]"))
                    else:
                        new_chain.append(component)
                display_chain.extend(new_chain)
                display_chain.append(username)
                await event.send(MessageChain(display_chain))
        else:
            return

    def get_filtered_chain(self, message, MESSAGE_TYPE):
        """获取过滤后的消息链"""
        # print(f"func_message:{message}")
        before_chain = list(message.message)
        # print(f"func_before_chain:{before_chain}")
        after_chain = []
        for index, comp in enumerate(before_chain):
            comp_type = str(comp.type).split(".")[-1]
            if comp_type in MESSAGE_TYPE:
                after_chain.append(Comp.Plain(MESSAGE_TYPE[comp_type]))
            elif (
                comp_type == "Image"
                and message.raw_message["message"][index]["data"]["sub_type"]
                == 0  # 通过索引对应检测避免访问不存在的字段
            ):  # 不过滤动画表情
                after_chain.append(Comp.Plain("[图片]"))
            else:
                after_chain.append(comp)
        return after_chain
