# Explorer
密室NPC Agent

## 环境要求
- Python 3.6+ 
- 依赖库：
  - tkinter (Python标准库)
  - Pillow (PIL)
  - numpy

## 安装依赖
```bash
pip install Pillow numpy
```

## 游玩方式
直接输入指令，如：
- 081号，查询你现在所处的位置！收到请回复！
- 前进，进入最右侧的门！（如果有多扇门）
- 后退，返回前一个房间！
根据设定，玩家至多可以与智能体进行10次对话，超过次数后游戏结束。