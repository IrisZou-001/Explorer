# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import os
import platform
import numpy as np

# --- 配置区 ---
MAZE_SIZE = 800  # 图片尺寸
ROOM_SIZE = 180   # 房间大小
WALL_THICKNESS = 5  # 墙厚度
PADDING = 80     # 边距
ITEM_FONT_SIZE = 36  # 物品文字大小
ROOM_NUM_FONT_SIZE = 24 # 房间号文字大小

# 颜色定义 (已修改为白色背景配色)
COLOR_WALL = "#e0e0e0"
COLOR_PATH = "#888888"
COLOR_ROOM_FILL = "#f0f0f0"  # 不透明的浅灰色
COLOR_EXPLORER = "#ff4444"
COLOR_TEXT = "#ffffff"
COLOR_ITEM = "#cc7700" # 更深的橙色，在浅色背景下更清晰

# --- 迷宫结构定义 ---
rooms = {
    1: {"children": [4], "item": "高原盐湖晶石", "parent": None},
    2: {"children": [3], "item": "藏刀", "parent": 4},
    3: {"children": [], "item": "酥油茶壶", "parent": 2},
    4: {"children": [2, 5, 7], "item": "牦牛奶酪", "parent": 1},
    5: {"children": [], "item": "青稞酒", "parent": 4},
    6: {"children": [], "item": "松石玉石", "parent": 7},
    7: {"children": [6], "item": "银饰扣件", "parent": 4},  # 通关道具
}
visit_path = [1,4,7,6,7,4,2,3,2,4,5]



visited = np.zeros((8,8))
for i in range(1, 8):
    visited[i][i]= 1
# for i in range(1, 8):
#     visited[i][1] = 1
#     visited[5][i] = 1
# visited[4][1] = 1
# visited[2][4] = 1
# visited[3][4] = 1
# visited[3][2] = 1
# visited[7][4] = 1
# visited[5][4] = 1
# visited[6][4] = 1
# visited[6][7] = 1
# visited[7][2] = 1
# visited[7][3] = 1
# visited[6][2] = 1
# visited[6][3] = 1


#计算visited矩阵非零元
for i in range(len(visit_path)):
    for j in range(0, i):
        visited[visit_path[i]][visit_path[j]] = 1

# 获取系统默认中文字体
def get_default_chinese_font(size):
    try:
        if platform.system() == "Windows":
            font_path = "C:/Windows/Fonts/simhei.ttf"  # 黑体
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
                
        elif platform.system() == "Darwin":  # macOS
            font_path = "/System/Library/Fonts/PingFang.ttc"  # 苹方
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
                
        elif platform.system() == "Linux":
            font_paths = [
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
            ]
            for path in font_paths:
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
        
        return ImageFont.load_default()
        
    except Exception:
        return ImageFont.load_default()

# 计算房间位置
def calculate_room_positions(rooms):
    positions = {}
    positions[1] = (MAZE_SIZE // 2 - ROOM_SIZE // 2, PADDING)
    positions[4] = (MAZE_SIZE // 2 - ROOM_SIZE // 2, PADDING + ROOM_SIZE + WALL_THICKNESS * 3)
    positions[2] = (MAZE_SIZE // 2 - ROOM_SIZE // 2 + ROOM_SIZE + WALL_THICKNESS * 3, PADDING + ROOM_SIZE + WALL_THICKNESS * 3)
    positions[7] = (MAZE_SIZE // 2 - ROOM_SIZE // 2 - ROOM_SIZE - WALL_THICKNESS * 3, PADDING + ROOM_SIZE + WALL_THICKNESS * 3)
    positions[5] = (MAZE_SIZE // 2 - ROOM_SIZE // 2, PADDING + ROOM_SIZE * 2 + WALL_THICKNESS * 6)
    positions[6] = (MAZE_SIZE // 2 - ROOM_SIZE // 2 - ROOM_SIZE - WALL_THICKNESS * 3, PADDING + ROOM_SIZE * 2 + WALL_THICKNESS * 6)
    positions[3] = (MAZE_SIZE // 2 - ROOM_SIZE // 2 + ROOM_SIZE  + WALL_THICKNESS * 3, PADDING + ROOM_SIZE * 2 + WALL_THICKNESS * 6)
    return positions

# --- 生成图片函数 ---
def generate_maze_images(rooms, positions):
    """生成探索者在每个房间的迷宫图片"""
    room_num_font = get_default_chinese_font(ROOM_NUM_FONT_SIZE)
    item_font = get_default_chinese_font(ITEM_FONT_SIZE)
    room_numbers = sorted(rooms.keys())
    
    for room_num in room_numbers:
        # 1. 创建白色背景画布 (修改点)
        img = Image.new('RGB', (MAZE_SIZE, MAZE_SIZE), (255, 255, 255))
        
        draw = ImageDraw.Draw(img)
        
        # 2. 绘制所有路径
        for parent_num in rooms:
            if visited[room_num][parent_num] == 0:
                continue
            for child_num in rooms[parent_num]["children"]:
                if visited[room_num][child_num] == 0: # 增加检查，确保只绘制已访问的路径
                    continue
                px, py = positions[parent_num]
                cx, cy = positions[child_num]
                
                parent_center_x = px + ROOM_SIZE // 2
                parent_center_y = py + ROOM_SIZE // 2
                child_center_x = cx + ROOM_SIZE // 2
                child_center_y = cy + ROOM_SIZE // 2
                
                draw.line(
                    [(parent_center_x, parent_center_y), (parent_center_x, child_center_y)],
                    fill=COLOR_PATH,
                    width=WALL_THICKNESS
                )
                
                if child_center_x > parent_center_x:
                    horizontal_start_x = parent_center_x
                    horizontal_end_x = child_center_x
                else:
                    horizontal_start_x = child_center_x
                    horizontal_end_x = parent_center_x
                
                draw.line(
                    [(horizontal_start_x, child_center_y), (horizontal_end_x, child_center_y)],
                    fill=COLOR_PATH,
                    width=WALL_THICKNESS
                )

        # 3. 绘制所有房间
        for num in room_numbers:
            if visited[room_num][num] == 0:
                continue
            x, y = positions[num]
            draw.rectangle(
                [(x, y), (x + ROOM_SIZE, y + ROOM_SIZE)],
                fill=COLOR_ROOM_FILL, # 使用新的房间填充色
                outline=COLOR_WALL,
                width=WALL_THICKNESS
            )
            item_text = rooms[num]["item"]
            if len(item_text) > 4:
                item_text = item_text[:4] + "\n" + item_text[4:]
            draw.multiline_text(
                (x + ROOM_SIZE // 2, y + ROOM_SIZE * 2 // 3),
                item_text,
                fill=COLOR_ITEM, # 使用新的物品文字色
                anchor="mm",
                font=item_font,
                align="center",
                spacing=5
            )

        # 4. 绘制探索者
        explorer_x, explorer_y = positions[room_num]
        triangle_size = 25
        yshift = ROOM_SIZE // 6
        points = [
            (explorer_x + ROOM_SIZE // 2, explorer_y + ROOM_SIZE // 2 - triangle_size - yshift),
            (explorer_x + ROOM_SIZE // 2 - triangle_size, explorer_y + ROOM_SIZE // 2 + triangle_size // 2 - yshift),
            (explorer_x + ROOM_SIZE // 2 + triangle_size, explorer_y + ROOM_SIZE // 2 + triangle_size // 2 - yshift)
        ]
        draw.polygon(points, fill=COLOR_EXPLORER, outline=COLOR_TEXT, width=2)

        # 5. 保存图片
        img.save(f"maze_explorer_at_room_{room_num}.png")
        print(f"已生成: maze_explorer_at_room_{room_num}.png")

# --- 执行生成 ---
if __name__ == "__main__":
    room_positions = calculate_room_positions(rooms)
    generate_maze_images(rooms, room_positions)