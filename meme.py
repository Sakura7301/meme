import io
import os
import asyncio
import json
import re
import random
from meme_generator import get_meme
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from common.log import logger
from plugins import *
from config import conf, global_config

@plugins.register(
    name="meme",
    desire_priority=99,
    hidden=True,
    desc="A simple plugin that returns the user's avatar or a gif",
    version="0.4",
    author="Cool、fred",
)
class Meme(Plugin):
    def __init__(self):
        super().__init__()
        try:
            logger.info("[Meme] Initialized")
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
            self.load_config()
            self.disabled_memes = {}  # 格式: {group_id: set(disabled_meme_types)}
            self.globally_disabled_memes = set()  # 全局禁用的表情类型
        except Exception as e:
            logger.error(f"[Meme] Initialization error: {e}")
            raise "[Meme] initialization failed, ignoring"

        self.channel = None
        self.channel_type = conf().get("channel_type", "wx")
        if self.channel_type == "wx":
            try:
                from lib import itchat
                self.channel = itchat
            except Exception as e:
                logger.error(f"itchat not installed: {e}")
        else:
            logger.error(f"Unsupported channel_type: {self.channel_type}")

        self.meme_gen = {}

    def load_config(self):
        """Load meme types from config.json under 'one_PicEwo' and 'two_PicEwo'."""
        config_path = os.path.join(self.path, 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.trigger_to_meme = config.get("one_PicEwo", {})
                self.two_person_meme = config.get("two_PicEwo", {})
            logger.info("[Meme] Configuration loaded successfully.")
        except Exception as e:
            logger.error(f"[Meme] Error loading configuration: {e}")
            self.trigger_to_meme = {}
            self.two_person_meme = {}

    def on_handle_context(self, e_context):
        if e_context["context"].type not in [ContextType.TEXT]:
            return

        content = e_context["context"].content
        
        # 检查特定的命令以显示表情列表
        if content.strip() == "表情列表":
            self.send_meme_list(e_context)
            return

        # 首先处理禁用或启用的命令
        if re.match(r'^(全局)?(禁用|启用)表情\s+.+$', content):
            self.handle_enable_disable_commands(e_context, content)

        # 检查表情是否被禁用
        msg = e_context["context"].kwargs.get("msg")
        group_id = msg.from_user_id if e_context["context"]["isgroup"] else None
        
        clean_content = self.clean_at_users_from_content(content)
        if (clean_content in self.globally_disabled_memes or 
            (group_id in self.disabled_memes and clean_content in self.disabled_memes[group_id])):
            return

        # 提取被@用户
        mentioned_users = self.extract_at_users_from_content(content)
        logger.debug(f"Mentions found: {mentioned_users}")

        # 新增逻辑: 检查是否是 "随机表情" 以及有无 @用户
        if "随机表情" in content:
            meme_type = random.choice(list(self.trigger_to_meme.values()))

            # 如果有 "@用户"
            if mentioned_users:
                for username in mentioned_users:
                    username = username.strip()
                    user_info = self.get_user_info_by_username(msg.from_user_id, username)
                    if user_info:
                        head_img = self.channel.get_head_img(user_info['UserName'], msg.from_user_id)
                    else:
                        logger.error(f"User '{username}' not found.")
                        reply = Reply(type=ReplyType.TEXT, content="无法获取被@用户的头像！")
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        return

                    if isinstance(head_img, bytes):
                        self.generate_and_reply(e_context, meme_type, head_img)
                    else:
                        reply = Reply(type=ReplyType.TEXT, content="无法获取被@用户的头像！")
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        return
            else:
                # 无 @用户，则使用发送者头像
                head_img = self.channel.get_head_img(msg.actual_user_id, msg.from_user_id)
                self.generate_and_reply(e_context, meme_type, head_img)
            return

        if mentioned_users:
            for username in mentioned_users:
                username = username.strip()
                logger.debug(f"Processing username: {username}")
                user_info = self.get_user_info_by_username(msg.from_user_id, username)

                if user_info:
                    if e_context["context"]["isgroup"]:
                        head_img = self.channel.get_head_img(user_info['UserName'], msg.from_user_id)
                    else:
                        head_img = self.channel.get_head_img(user_info['UserName'])
                else:
                    logger.error(f"User '{username}' not found.")
                    reply = Reply(type=ReplyType.TEXT, content="无法获取被@用户的头像！")
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return

                if not isinstance(head_img, bytes):
                    logger.error(f"Failed to retrieve the avatar for user: {username}")
                    reply = Reply(type=ReplyType.TEXT, content="无法获取被@用户的头像！")
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return

                # 检查双人表情包
                if clean_content in self.two_person_meme:
                    sender_img = self.channel.get_head_img(msg.actual_user_id, msg.from_user_id)
                    if isinstance(sender_img, bytes):
                        meme_type = self.two_person_meme.get(clean_content)
                        self.generate_and_reply(e_context, meme_type, sender_img, head_img, two_person=True)
                    else:
                        reply = Reply(type=ReplyType.TEXT, content="无法获取发送者头像！")
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        return

                # 检查单人表情包
                else:
                    meme_type = self.trigger_to_meme.get(clean_content)
                    self.generate_and_reply(e_context, meme_type, head_img)

        meme_type = self.trigger_to_meme.get(content)

        if meme_type:
            head_img = self.channel.get_head_img(msg.actual_user_id, msg.from_user_id)
            self.generate_and_reply(e_context, meme_type, head_img)

    def extract_at_users_from_content(self, content):
        """从内容中提取用户名称，去除'@'及其之间的空白字符."""
        pattern = r'@([^\s@~]+(?:\s+[^\s@~]+)*)'  # 修改正则以确保提取完整名称
        usernames = re.findall(pattern, content)
        return usernames

    def clean_at_users_from_content(self, content):
        """移除所有提及(包含'@'的用户名)并返回清理后的字符串."""
        clean_content = re.sub(r'@\S+(?:\s+\S+)*\s*', '', content)
        return clean_content.strip()

    def generate_and_reply(self, e_context, meme_type, *head_imgs, two_person=False):
        reply = Reply()
        try:
            current_meme_gen = self.meme_gen.get(meme_type)
            if current_meme_gen is None:
                current_meme_gen = get_meme(meme_type)
                self.meme_gen[meme_type] = current_meme_gen

            if two_person:
                result = current_meme_gen(images=head_imgs, texts=[], args={"circle": True})
            else:
                result = current_meme_gen(images=[head_imgs[0]], texts=[], args={"circle": True})

            if asyncio.iscoroutine(result):
                buf_gif = asyncio.run(result)
            else:
                buf_gif = result

            reply.type = ReplyType.IMAGE
            reply.content = io.BytesIO(buf_gif.getvalue())
        except Exception as e:
            logger.error(f"[Meme] Meme generation error: {e}")
            reply.type = ReplyType.TEXT
            reply.content = "生成动图失败，请稍后重试！"

        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    def get_user_info_by_username(self, group_name, user_name):
        group_info = self.channel.search_chatrooms(None, group_name)

        logger.debug(f"Searching for user '{user_name}' in the group.")
        for member in group_info["MemberList"]:
            logger.debug(f"Checking member: {member['DisplayName']} ({member['NickName']})")
            if member['DisplayName'] == user_name or member['NickName'] == user_name:
                return member
        logger.debug(f"User '{user_name}' not found in {group_name}")
        return None

    def is_admin_in_group(self, context):
        """检查当前用户是否是群组中的管理员。"""
        if context["isgroup"]:
            return context.kwargs.get("msg").actual_user_id in global_config["admin_users"]
        return False

    def handle_enable_disable_commands(self, e_context, content):
        """处理启用和禁用表情命令"""
        msg = e_context["context"].kwargs.get("msg")
        group_id = msg.from_user_id if e_context["context"]["isgroup"] else None
        
        # 检查管理员权限
        if not self.is_admin_in_group(e_context["context"]):
            reply = Reply(ReplyType.TEXT, "只有管理员才有权执行此操作！")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return True

        # 解析命令
        match = re.match(r'^(全局)?(禁用|启用)表情\s+(.+)$', content)
        if not match:
            return False

        is_global, action, meme_name = match.groups()
        
        # 检查表情是否存在
        meme_type = self.trigger_to_meme.get(meme_name)
        if not meme_type and meme_name not in self.two_person_meme:
            reply = Reply(ReplyType.TEXT, "未找到指定的表情！")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return True

        if is_global:  # 全局控制
            if action == "禁用":
                self.globally_disabled_memes.add(meme_name)
                reply_text = f"已全局禁用表情：{meme_name}"
            else:  # 启用
                self.globally_disabled_memes.discard(meme_name)
                reply_text = f"已全局启用表情：{meme_name}"
        else:  # 群组控制
            if group_id:
                if action == "禁用":
                    if group_id not in self.disabled_memes:
                        self.disabled_memes[group_id] = set()
                    self.disabled_memes[group_id].add(meme_name)
                    reply_text = f"已在当前群禁用表情：{meme_name}"
                else:  # 启用
                    if group_id in self.disabled_memes:
                        self.disabled_memes[group_id].discard(meme_name)
                        reply_text = f"已在当前群启用表情：{meme_name}"
            else:
                reply_text = "该命令只能在群聊中使用"

        reply = Reply(ReplyType.TEXT, reply_text)
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS
        return True

    def send_meme_list(self, e_context):
        """整理和发送单人和双人表情的触发词列表."""
        single_meme_list = list(self.trigger_to_meme.keys())
        two_person_meme_list = list(self.two_person_meme.keys())
        
        # 创建列表字符串
        response = "单人表情触发词:\n"
        response += "\n".join(single_meme_list) if single_meme_list else "没有单人表情触发词。\n"
        
        response += "\n双人表情触发词:\n"
        response += "\n".join(two_person_meme_list) if two_person_meme_list else "没有双人表情触发词。"

        # 回复给用户
        reply = Reply(ReplyType.TEXT, response)
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    def get_help_text(self, **kwargs):
        help_text = (
            "输入 '随机表情'，我会生成一个随机表情包。\n"
            "输入相应的触发词，我会为你生成一个动态头像效果。\n"
            "在消息中@用户，我会为被@用户制作表情包。\n"
            "输入 '表情列表' 来获取可用的单人和双人表情触发词。\n"
            "管理员命令：\n"
            "使用 '禁用表情 <表情名>' 或 '启用表情 <表情名>' 来控制当前群聊中的表情。\n"
            "使用 '全局禁用表情 <表情名>' 或 '全局启用表情 <表情名>' 来控制所有群聊的表情。"
        )
        return help_text
