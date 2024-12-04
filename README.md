# meme (头像表情包插件)
基于chatgpt-on-wechat创建的制作表情包插件，可发GIF动图

## 功能介绍

这是一个用于[meme-generator](https://github.com/MeetWq/meme-generator)生成各种头像相关表情包的[cow](https://github.com/zhayujie/chatgpt-on-wechat)插件。支持制作单人表情包、双人表情包、随机表情包功能。

**演示**

![表情演示](images/演示.gif)

## 安装meme-generator

1. **使用 pip 安装meme-generator**

   - `pip install -U meme_generator`

2. **下载表情包图片**

   - `meme download`

3. **配置文件（可选）**

   - 具体步骤前往[meme-generator](https://github.com/MeetWq/meme-generator/wiki/%E9%85%8D%E7%BD%AE%E6%96%87%E4%BB%B6)进行配置

## 在cow上面安装meme插件

- clone或下载本仓库源代码到[chatgpt-on-wechat](https://github.com/zhayujie/chatgpt-on-wechat)的plugins文件夹中
- 启动chatgpt-on-wechat，即可自动加载并启用本插件

## 基于[Godcmd插件](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins/godcmd)安装
- `#auth <口令>`
- `#installp https://github.com/WoodGoose/meme.git`
- `#scanp`

## 基础功能

1. **单人表情包**
   - 输入 `配置文件中定义的触发词` - 生成发送人头像的表情包

2. **随机表情包**
   - 输入 `随机表情` - 随机生成一个发送人头像的表情包效果

3. **双人表情包**
   - 输入 `撞@用户` - 使用发送者和被@用户的头像生成对应表情下的双人表情包
  
4. **表情列表**
   - 输入 `表情列表` - 获取双人表情跟单人表情的触发列表

## 管理功能

管理员可以通过以下命令控制表情包的使用：

1. **群聊控制**
   - `禁用表情 <表情名>` - 在当前群禁用指定表情
   - `启用表情 <表情名>` - 在当前群启用指定表情

2. **全局控制**
   - `全局禁用表情 <表情名>` - 在所有群禁用指定表情
   - `全局启用表情 <表情名>` - 在所有群启用指定表情
  
## 配置说明

插件使用 `config.json` 配置文件来定义表情包：

```
{
    "one_PicEwo": {
        "触发词1": "表情类型1",
        "触发词2": "表情类型2"
    },
    "two_PicEwo": {
        "触发词3": "双人表情类型1",
        "触发词4": "双人表情类型2"
    }
}
```

- `one_PicEwo`: 定义单人表情包的触发词和对应类型
- `two_PicEwo`: 定义双人表情包的触发词和对应类型

## 使用限制

1. 管理员功能仅限于被设置为管理员的用户使用
2. 群组控制命令仅在群聊中有效
3. 管理员认证同[Godcmd插件](https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins/godcmd)认证即可
4. 因原本的itchat里面不支持发送GIF图，需修改lib/itchat/components/messages.py下的`def send_image(self, fileDir=None, toUserName=None, mediaId=None, file_=None)`

```
def send_image(self, fileDir=None, toUserName=None, mediaId=None, file_=None):
    logger.debug('Request to send a image(mediaId: %s) to %s: %s' % (
        mediaId, toUserName, fileDir))
    if fileDir or file_:
        flag_gif = False
        if hasattr(fileDir, 'read'):
            if fileDir.read(3) == b'GIF':
                flag_gif = True
            fileDir.seek(0)
            file_, fileDir = fileDir, None
        if fileDir is None:
            fileDir = 'tmp.jpg'  # specific fileDir to send gifs
        if flag_gif:
            fileDir = 'tmp.gif'
```

## 交流联系
- 任何想法、建议、需求、咨询、BUG等，欢迎加入交流
- 如果您有任何改进意见或功能请求,请随时提交 Pull Request 或创建 Issue.

![qr](images/qr.png)
