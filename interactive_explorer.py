import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import http.client
import json
import ssl
import os
import sys
# 禁用libpng警告
os.environ["PNG_SKIP_sRGB_CHECK"] = "1"
from PIL import Image, ImageTk, ImageDraw, ImageFont

# 全局变量用于存储显示的图像，防止垃圾回收
displayed_image = None
import platform
import numpy as np
import threading
import re
import io
# 导入maze.py中的函数
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import maze

class InteractiveExplorer:
    def __init__(self, root):
        self.root = root
        self.root.title("智能体探索者")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        # 设置中文字体支持
        self.default_font = self._get_default_chinese_font(12)
        
        # 初始化聊天记录和当前房间
        self.chat_history = []
        self.current_room = None
        
        # 防止地图图像重复更新的标志
        self.map_update_in_progress = False
        
        # 初始化path列表，用于存储访问路径
        self.path = []
        
        # 对话状态标志，表示对话是否已经终止
        self.conversation_terminated = False
        self.termination_reason = None
        
        # 创建UI
        self._create_ui()
        
        # 迷宫相关配置
        self._initialize_maze_config()
        
        # API调用配置
        self._initialize_api_config()
        
        # 不设置默认房间，所有房间都将在API调用返回后显示
        # 初始状态下地图区域为空，等待API响应
    
    def _get_default_chinese_font(self, size):
        """获取系统默认中文字体"""
        try:
            if platform.system() == "Windows":
                font_path = "C:/Windows/Fonts/simhei.ttf"  # 黑体
                if os.path.exists(font_path):
                    return ("SimHei", size)
            elif platform.system() == "Darwin":  # macOS
                return ("PingFang SC", size)
            elif platform.system() == "Linux":
                return ("WenQuanYi Micro Hei", size)
        except Exception:
            pass
        return ("Arial", size)
    
    def _initialize_maze_config(self):
        """初始化迷宫配置"""
        # 直接使用maze.py中的迷宫配置
        self.rooms = maze.rooms
        # 初始化path列表，但不在此覆盖__init__中设置的值
        
        # 计算房间位置
        self.room_positions = maze.calculate_room_positions(self.rooms)
        
    def _initialize_api_config(self):
        """初始化API配置"""
        # 注意：实际使用时需要替换为有效的API密钥
        # 从readme.md中获取的API信息
        self.api_key = "e6794ed4d67116edb49fe6a1d323ae6e"
        self.api_secret = "M2YyNGUxNWZiYzNjYWVmYzY5MmQxZWMy"
        self.flow_id = "7377160082599239682"
        
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self.api_key}:{self.api_secret}",
        }
        self.api_url = "xingchen-api.xf-yun.com"
        self.api_endpoint = "/workflow/v1/chat/completions"
        self.uid = "123"
        # 添加模拟模式，当API不可用时使用
        self.mock_mode = False
    

    
    def _create_ui(self):
        """创建用户界面"""
        # 主框架
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧对话区域 (三分之二宽度)
        left_frame = tk.Frame(main_frame, bg="#ffffff", width=800)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 聊天显示区域
        self.chat_display = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, font=self.default_font, 
                                                      bg="#ffffff", relief=tk.FLAT, bd=0)
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # 输入区域
        input_frame = tk.Frame(left_frame, bg="#f0f0f0", height=50)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        self.message_entry = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, font=self.default_font, 
                                                       height=3, bd=1, relief=tk.SUNKEN)
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.message_entry.bind("<Return>", lambda event: self._send_message())
        
        self.send_button = tk.Button(input_frame, text="发送", command=self._send_message, 
                                    bg="#4CAF50", fg="white", font=self.default_font, 
                                    height=1, width=10)
        self.send_button.pack(side=tk.RIGHT)
        
        # 右侧地图区域 (三分之一宽度)
        right_frame = tk.Frame(main_frame, bg="#ffffff", width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 地图显示区域
        self.map_canvas = tk.Canvas(right_frame, bg="#ffffff", bd=0, highlightthickness=0)
        self.map_canvas.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 状态栏
        status_bar = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _add_message_to_display(self, sender, message):
        """将消息添加到聊天显示区域，实现一左一右的聊天气泡样式"""
        self.chat_display.config(state=tk.NORMAL)
        
        # 更新聊天历史，用于API调用
        role = "user" if sender == "你" else "assistant"
        if len(self.chat_history) > 10:  # 限制历史消息数量
            self.chat_history.pop(0)
        self.chat_history.append({
            "role": role,
            "content_type": "text",
            "content": message
        })
        
        # 先插入一个空行，为聊天气泡提供空间
        self.chat_display.insert(tk.END, "\n\n")
        
        # 处理消息内容，分割换行符
        message_lines = message.split('\n')
        
        # 根据发送者设置不同的聊天气泡样式和位置
        if sender == "你":
            # 用户消息 - 右对齐，绿色气泡
            for line in message_lines:
                # 添加足够的空格来右对齐消息
                spaces = " " * 50  # 根据需要调整空格数量
                self.chat_display.insert(tk.END, spaces + line, "user_message")
                if line != message_lines[-1]:
                    self.chat_display.insert(tk.END, "\n")
            # 设置用户聊天气泡样式
            self.chat_display.tag_config("user_message", background="#dcf8c6", 
                                         foreground="#000000", justify=tk.RIGHT,
                                         lmargin1=100, lmargin2=100, rmargin=10)
            
            # 如果是用户消息且处于模拟模式，处理模拟响应
            if hasattr(self, 'mock_mode') and self.mock_mode:
                self._handle_mock_response(message)
        else:
            # 探索人员消息 - 左对齐，灰色气泡
            self.chat_display.insert(tk.END, f"{sender}:\n", "sender")
            for line in message_lines:
                self.chat_display.insert(tk.END, line, "agent_message")
                if line != message_lines[-1]:
                    self.chat_display.insert(tk.END, "\n")
            # 设置探索人员聊天气泡样式
            self.chat_display.tag_config("agent_message", background="#f0f0f0",
                                        foreground="#000000", justify=tk.LEFT,
                                        lmargin1=10, lmargin2=10, rmargin=100)
            # 设置发送者标签样式
            self.chat_display.tag_config("sender", font=(self.default_font[0], self.default_font[1], "bold"),
                                        foreground="#444444", lmargin1=10)
            
            # 严格根据API响应提取当前房间信息并更新地图
            # 这是关键：不管是真实API调用还是模拟模式，都只从响应文本中提取房间号
            self._update_room_from_response(message)
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # 滚动到最新消息
    
    def _process_api_response(self, parsed_response):
        """处理解析后的API响应，更新UI和房间信息"""
        # 判断响应类型
        print(parsed_response)
        if isinstance(parsed_response, dict):
            print("dict")
            # 这是一个完整的响应字典，包含output、current_room等字段
            output = parsed_response.get("output", "")
            current_room = parsed_response.get("current_room")
            finished = parsed_response.get("finished", False)
            oxygen = parsed_response.get("oxygen", None)
            print(output)
            # 更新UI显示聊天内容
            if output:
                self.root.after(0, self._add_message_to_display, "081号探索人员", output)
            
            # 直接使用API返回的current_room字段更新房间信息
            if current_room is not None:
                self._update_room_from_api(current_room)
            
            # 处理任务完成或氧气耗尽的情况
            if finished:
                self.root.after(0, self._show_task_complete)
            elif oxygen == 0:
                self.root.after(0, self._show_disconnected)
        else:
            # 这是纯文本响应，回退到旧的处理方式
            self.root.after(0, self._add_message_to_display, "081号探索人员", parsed_response)
            # 如果没有直接获取到current_room，尝试从文本中提取
            self._update_room_from_response(parsed_response)
            
    def _update_room_from_api(self, room_number):
        """直接从API返回的current_room字段更新房间信息"""
        try:
            # 确保房间号是整数
            room_number = int(room_number)
            # 验证房间号是否有效
            if room_number in self.rooms:
                # 只根据API响应更新当前房间
                self.current_room = room_number
                
                
                self.path.append(room_number)
                # 立即更新地图，不使用锁机制
                self._update_map()
                print(f"根据API返回的current_room字段更新房间: {room_number}")
        except ValueError:
            print(f"API返回的房间号格式无效: {room_number}")
    
    def _update_room_from_response(self, response):
        """从响应文本中提取房间信息（备用方案）"""
        # 这是备用方案，当API没有直接返回current_room字段时使用
        # 使用正则表达式尝试从响应中提取房间号
        match = re.search(r'房间(\d+)', response)
        if match:
            try:
                room_number = int(match.group(1))
                # 验证房间号是否有效
                if room_number in self.rooms:
                    # 只根据API响应更新当前房间
                    self.current_room = room_number
                    # 确保房间只添加一次到path列表中（防止重复添加）
                    if room_number not in self.path:
                        self.path.append(room_number)
                    # 立即更新地图，不使用锁机制
                    self._update_map()
                    print(f"从响应文本中提取并更新房间: {room_number}")
            except ValueError:
                print(f"从响应中提取房间号失败: {response}")
                pass
    
    def _show_task_complete(self):
        """显示任务完成信息并终止对话"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n\n--------------------------------------------------------------------\n")
        self.chat_display.insert(tk.END, "任务完成\n", "system_message")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.tag_config("system_message", foreground="#ff0000", font=(self.default_font[0], self.default_font[1], "bold"))
        self.chat_display.see(tk.END)
        
        # 设置对话终止标志和原因
        self.conversation_terminated = True
        self.termination_reason = "任务完成"
    
    def _show_disconnected(self):
        """显示对方已失联信息并终止对话"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n\n--------------------------------------------------------------------\n")
        self.chat_display.insert(tk.END, "对方已失联\n", "system_message")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.tag_config("system_message", foreground="#ff0000", font=(self.default_font[0], self.default_font[1], "bold"))
        self.chat_display.see(tk.END)
        
        # 设置对话终止标志和原因
        self.conversation_terminated = True
        self.termination_reason = "对方已失联"
    
    def _update_map(self):
        """更新地图显示，重新设计为立即执行的更新逻辑"""
        try:
            if self.current_room is None:
                # 即使没有当前房间，也显示一些调试信息表明画布正常工作
                canvas_width = self.map_canvas.winfo_width() or 400
                canvas_height = self.map_canvas.winfo_height() or 400
                self.map_canvas.delete("all")
                self.map_canvas.create_text(canvas_width // 2, canvas_height // 2,
                                           text="等待探索开始...",
                                           fill="gray", font=('SimHei', 12))
                return
            
            # 创建白色背景画布
            img = Image.new('RGB', (maze.MAZE_SIZE, maze.MAZE_SIZE), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # 获取中文字体
            room_num_font = maze.get_default_chinese_font(maze.ROOM_NUM_FONT_SIZE)
            item_font = maze.get_default_chinese_font(maze.ITEM_FONT_SIZE)
            
            # 确定已访问的房间集合
            visited_rooms = set(self.path)
            
            # 绘制所有已访问房间之间的路径
            # 为每个已访问的房间，检查其相邻的已访问房间
            for room_num in visited_rooms:
                for neighbor_num in self.rooms[room_num]["children"]:
                    # 确保只绘制已访问房间之间的路径，且避免重复绘制
                    if neighbor_num in visited_rooms and room_num < neighbor_num:
                        # 获取两个房间的位置
                        room_x, room_y = self.room_positions[room_num]
                        neighbor_x, neighbor_y = self.room_positions[neighbor_num]
                        
                        # 计算房间中心点
                        room_center_x = room_x + maze.ROOM_SIZE // 2
                        room_center_y = room_y + maze.ROOM_SIZE // 2
                        neighbor_center_x = neighbor_x + maze.ROOM_SIZE // 2
                        neighbor_center_y = neighbor_y + maze.ROOM_SIZE // 2
                        
                        # 绘制房间之间的路径（直线连接）
                        draw.line(
                            [(room_center_x, room_center_y), (neighbor_center_x, neighbor_center_y)],
                            fill=maze.COLOR_PATH,
                            width=maze.WALL_THICKNESS
                        )
            
            # 绘制所有已访问的房间
            for num in visited_rooms:
                x, y = self.room_positions[num]
                draw.rectangle(
                    [(x, y), (x + maze.ROOM_SIZE, y + maze.ROOM_SIZE)],
                    fill=maze.COLOR_ROOM_FILL,
                    outline=maze.COLOR_WALL,
                    width=maze.WALL_THICKNESS
                )
                
                # 绘制物品文字
                item_text = maze.rooms[num]["item"]
                if len(item_text) > 4:
                    item_text = item_text[:4] + "\n" + item_text[4:]
                draw.multiline_text(
                    (x + maze.ROOM_SIZE // 2, y + maze.ROOM_SIZE * 2 // 3),
                    item_text,
                    fill=maze.COLOR_ITEM,
                    anchor="mm",
                    font=item_font,
                    align="center",
                    spacing=5
                )
            
            # 只在当前房间绘制探索者三角形（确保三角形只在已访问的房间内显示）
            if self.current_room in visited_rooms:
                explorer_x, explorer_y = self.room_positions[self.current_room]
                triangle_size = 25
                yshift = maze.ROOM_SIZE // 6
                points = [
                    (explorer_x + maze.ROOM_SIZE // 2, explorer_y + maze.ROOM_SIZE // 2 - triangle_size - yshift),
                    (explorer_x + maze.ROOM_SIZE // 2 - triangle_size, explorer_y + maze.ROOM_SIZE // 2 + triangle_size // 2 - yshift),
                    (explorer_x + maze.ROOM_SIZE // 2 + triangle_size, explorer_y + maze.ROOM_SIZE // 2 + triangle_size // 2 - yshift)
                ]
                draw.polygon(points, fill=maze.COLOR_EXPLORER, outline=maze.COLOR_TEXT, width=2)
            
            # 保存图像用于调试
            img_path = f"maze_explorer_at_room_{self.current_room}.jpg"
            img.save(img_path, "JPEG", quality=95)
            print(f"地图图像已保存到: {img_path}")
            
            # 调整图像大小以适应画布
            canvas_width = self.map_canvas.winfo_width()
            canvas_height = self.map_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                # 画布尚未初始化，使用默认大小
                canvas_width = 400
                canvas_height = 400
            
            # 保持图像比例
            img_ratio = img.width / img.height
            canvas_ratio = canvas_width / canvas_height
            
            if img_ratio > canvas_ratio:
                # 图像更宽，按宽度缩放
                new_width = canvas_width - 20  # 留出一些边距
                new_height = int(new_width / img_ratio)
            else:
                # 图像更高，按高度缩放
                new_height = canvas_height - 20  # 留出一些边距
                new_width = int(new_height * img_ratio)
            
            # 简化的图像转换和显示逻辑
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            rgb_img = resized_img.convert('RGB')
            
            # 使用全局变量存储图像对象，防止垃圾回收
            global displayed_image
            displayed_image = ImageTk.PhotoImage(rgb_img)
            
            # 清除并显示图像
            self.map_canvas.delete("all")
            self.map_canvas.create_image(canvas_width // 2, canvas_height // 2, image=displayed_image)
            
            # 强制更新画布
            self.root.update_idletasks()
            print(f"地图图像已成功显示: 房间{self.current_room}")
            
        except Exception as e:
            # 如果出现错误，在画布上显示错误信息
            error_msg = f"图像显示错误: {str(e)}"
            print(error_msg)
            canvas_width = self.map_canvas.winfo_width() or 400
            canvas_height = self.map_canvas.winfo_height() or 400
            self.map_canvas.delete("all")
            self.map_canvas.create_text(canvas_width // 2, canvas_height // 2,
                                        text=error_msg,
                                        fill="red", font=('SimHei', 10))
    

    

    

    
    def _send_message(self):
        """发送消息并调用智能体API"""
        # 检查对话是否已经终止
        if self.conversation_terminated:
            # 如果对话已终止，显示相应的终止信息
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"\n{self.termination_reason}\n", "system_message")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.tag_config("system_message", foreground="#ff0000", font=(self.default_font[0], self.default_font[1], "bold"))
            self.chat_display.see(tk.END)
            # 清空输入框
            self.message_entry.delete("1.0", tk.END)
            return
        
        message = self.message_entry.get("1.0", tk.END).strip()
        if not message:
            return
        
        # 清空输入框
        self.message_entry.delete("1.0", tk.END)
        
        # 在界面上显示用户消息，使用'你'作为称呼
        self._add_message_to_display("你", message)
        
        # 在单独的线程中调用API，避免阻塞UI
        threading.Thread(target=self._call_agent_api, args=(message,)).start()
    
    def _call_agent_api(self, user_input):
        """调用智能体API"""
        # 如果启用了模拟模式，直接返回模拟响应
        if self.mock_mode:
            self._handle_mock_response(user_input)
            return
            
        try:
            # 构建请求数据
            data = {
                "flow_id": self.flow_id,
                "uid": self.uid,
                "parameters": {"AGENT_USER_INPUT": user_input},
                "ext": {"bot_id": "workflow", "caller": "workflow"},
                "stream": False,
                "history": self.chat_history
            }
            payload = json.dumps(data)
            
            # 创建HTTPS连接
            conn = http.client.HTTPSConnection(self.api_url, timeout=120)
            conn.request(
                "POST", self.api_endpoint, payload, self.headers, encode_chunked=True
            )
            
            # 获取响应
            res = conn.getresponse()
            
            # 检查响应状态
            if res.status != 200:
                error_msg = f"API调用失败，状态码: {res.status}, 原因: {res.reason}"
                self.root.after(0, messagebox.showerror, "API调用错误", error_msg)
                conn.close()
                return
            
            # 处理响应
            if data.get("stream"):
                # 流式响应处理
                response_content = ""
                while chunk := res.readline():
                    response_content += chunk.decode("utf-8")
                # 打印完整的API响应
                print(f"\n===== 完整API响应（流式）: =====")
                print(response_content)
                print("============================\n")
                # 尝试解析JSON响应
                parsed_response = self._parse_api_response(response_content)
                # 在主线程中更新UI和处理房间信息
                self.root.after(0, self._process_api_response, parsed_response)
            else:
                # 非流式响应处理
                response_data = res.readline()
                response_content = response_data.decode("utf-8")
                # 打印完整的API响应
                print(f"\n===== 完整API响应（非流式）: =====")
                print(response_content)
                print("============================\n")
                # 尝试解析JSON响应
                parsed_response = self._parse_api_response(response_content)
                # 在主线程中更新UI和处理房间信息
                self.root.after(0, self._process_api_response, parsed_response)
                
            conn.close()
        except http.client.HTTPException as e:
            # HTTP错误处理
            self.root.after(0, messagebox.showerror, "HTTP错误", f"网络请求异常: {str(e)}")
        except json.JSONDecodeError as e:
            # JSON解析错误处理
            self.root.after(0, messagebox.showerror, "响应解析错误", f"无法解析API响应: {str(e)}")
        except ssl.SSLError as e:
            # SSL错误处理
            self.root.after(0, messagebox.showerror, "SSL错误", f"SSL连接异常: {str(e)}")
        except Exception as e:
            # 其他错误处理
            self.root.after(0, messagebox.showerror, "API调用错误", f"未知错误: {str(e)}")
            # 尝试使用模拟响应
            self.root.after(0, self._handle_mock_response, user_input)
            
    def _parse_api_response(self, raw_response):
        """解析API响应，提取有用信息"""
        try:
            # 尝试解析JSON响应
            response_json = json.loads(raw_response)
            
            # 检查是否为OpenAI风格的响应（包含choices字段）
            if "choices" in response_json and len(response_json["choices"]) > 0:
                # 获取content字段内容
                content = None
                if "delta" in response_json["choices"][0] and "content" in response_json["choices"][0]["delta"]:
                    content = response_json["choices"][0]["delta"]["content"]
                elif "message" in response_json["choices"][0] and "content" in response_json["choices"][0]["message"]:
                    content = response_json["choices"][0]["message"]["content"]
                
                # 检查content是否为JSON字符串
                if content and isinstance(content, str) and content.startswith('{') and content.endswith('}'):
                    try:
                        # 尝试解析content中的嵌套JSON
                        nested_json = json.loads(content)
                        # 处理字段名差异：将"current room"转换为"current_room"
                        if "current room" in nested_json and "current_room" not in nested_json:
                            nested_json["current_room"] = nested_json["current room"]
                        # 处理oxygen字段格式
                        if "oxygen" in nested_json:
                            try:
                                nested_json["oxygen"] = int(nested_json["oxygen"])
                            except (ValueError, TypeError):
                                pass
                        return nested_json
                    except json.JSONDecodeError:
                        # 如果嵌套JSON解析失败，返回原始content
                        return content
                return content
            
            # 处理直接包含output、current_room等字段的响应
            if "output" in response_json:
                # 处理字段名差异：将"current room"转换为"current_room"
                if "current room" in response_json and "current_room" not in response_json:
                    response_json["current_room"] = response_json["current room"]
                # 处理oxygen字段格式
                if "oxygen" in response_json:
                    try:
                        response_json["oxygen"] = int(response_json["oxygen"])
                    except (ValueError, TypeError):
                        pass
                return response_json
            
            return raw_response
        except (json.JSONDecodeError, KeyError):
            # 如果解析失败，返回原始响应
            return raw_response
            
    def _handle_mock_response(self, user_input):
        """处理模拟响应，用于测试"""
        # 模拟响应字典
        mock_responses = {
            "你好": "你好！我是081号探索人员，很高兴为你服务。你可以探索房间1，那里有高原盐湖晶石。",
            "探索房间1": "你现在位于房间1，这里有高原盐湖晶石。你可以前往房间4继续探索。",
            "房间4": "你现在位于房间4，这里有牦牛奶酪。从这里你可以前往房间2、房间5或房间7。",
            "房间2": "你现在位于房间2，这里有藏刀。你可以前往房间3。",
            "房间3": "你现在位于房间3，这里有酥油茶壶。这是一个死胡同，你需要返回房间2。",
            "房间5": "你现在位于房间5，这里有青稞酒。这是一个死胡同，你需要返回房间4。",
            "房间7": "你现在位于房间7，这里有银饰扣件。你可以前往房间6。",
            "房间6": "你现在位于房间6，这里有松石玉石。恭喜你找到了通关道具！",
            "我想知道房间2有什么": "你现在位于房间2，这里有藏刀。你可以前往房间3。",
        }
        
        # 查找匹配的响应
        response_found = False
        for key, response in mock_responses.items():
            if key in user_input:
                # 注意：这里不是直接从用户输入获取房间号，而是先获取完整响应
                self.root.after(0, self._add_message_to_display, "081号探索人员", response)
                response_found = True
                break
                
        # 如果没有匹配的响应，返回默认响应
        if not response_found:
            default_response = "感谢你的提问。我是081号探索人员，你可以问我关于房间探索的问题。\n\n例如：\n- 探索房间1\n- 房间4有什么\n- 我现在在哪里" 
            self.root.after(0, self._add_message_to_display, "081号探索人员", default_response)

def save_maze_map():
    """保存迷宫地图图片到文件"""
    try:
        # 设置访问路径
        maze.visit_path = [1, 4, 2, 3, 4, 7, 6]  # 模拟访问路径
        
        # 重新计算visited矩阵
        maze.visited = np.zeros((8,8))
        for i in range(len(maze.visit_path)):
            for j in range(0, i):
                maze.visited[maze.visit_path[i]][maze.visit_path[j]] = 1
        
        # 使用maze.py中的函数生成地图
        room_positions = maze.calculate_room_positions(maze.rooms)
        
        # 创建白色背景画布
        img = Image.new('RGB', (maze.MAZE_SIZE, maze.MAZE_SIZE), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 获取中文字体
        room_num_font = maze.get_default_chinese_font(maze.ROOM_NUM_FONT_SIZE)
        item_font = maze.get_default_chinese_font(maze.ITEM_FONT_SIZE)
        
        # 绘制所有路径
        for parent_num in maze.rooms:
            if maze.visited[4][parent_num] == 0:  # 在房间4查看
                continue
            for child_num in maze.rooms[parent_num]["children"]:
                if maze.visited[4][child_num] == 0:
                    continue
                
                px, py = room_positions[parent_num]
                cx, cy = room_positions[child_num]
                
                parent_center_x = px + maze.ROOM_SIZE // 2
                parent_center_y = py + maze.ROOM_SIZE // 2
                child_center_x = cx + maze.ROOM_SIZE // 2
                child_center_y = cy + maze.ROOM_SIZE // 2
                
                # 绘制垂直线
                draw.line(
                    [(parent_center_x, parent_center_y), (parent_center_x, child_center_y)],
                    fill=maze.COLOR_PATH,
                    width=maze.WALL_THICKNESS
                )
                
                # 绘制水平线
                if child_center_x > parent_center_x:
                    horizontal_start_x = parent_center_x
                    horizontal_end_x = child_center_x
                else:
                    horizontal_start_x = child_center_x
                    horizontal_end_x = parent_center_x
                
                draw.line(
                    [(horizontal_start_x, child_center_y), (horizontal_end_x, child_center_y)],
                    fill=maze.COLOR_PATH,
                    width=maze.WALL_THICKNESS
                )
        
        # 绘制所有房间
        room_numbers = sorted(maze.rooms.keys())
        for num in room_numbers:
            if maze.visited[4][num] == 0:
                continue
            
            x, y = room_positions[num]
            draw.rectangle(
                [(x, y), (x + maze.ROOM_SIZE, y + maze.ROOM_SIZE)],
                fill=maze.COLOR_ROOM_FILL,
                outline=maze.COLOR_WALL,
                width=maze.WALL_THICKNESS
            )
            
            # 绘制物品文字
            item_text = maze.rooms[num]["item"]
            if len(item_text) > 4:
                item_text = item_text[:4] + "\n" + item_text[4:]
            draw.multiline_text(
                (x + maze.ROOM_SIZE // 2, y + maze.ROOM_SIZE * 2 // 3),
                item_text,
                fill=maze.COLOR_ITEM,
                anchor="mm",
                font=item_font,
                align="center",
                spacing=5
            )
        
        # 绘制探索者
        explorer_x, explorer_y = room_positions[4]  # 在房间4
        triangle_size = 25
        yshift = maze.ROOM_SIZE // 6
        points = [
            (explorer_x + maze.ROOM_SIZE // 2, explorer_y + maze.ROOM_SIZE // 2 - triangle_size - yshift),
            (explorer_x + maze.ROOM_SIZE // 2 - triangle_size, explorer_y + maze.ROOM_SIZE // 2 + triangle_size // 2 - yshift),
            (explorer_x + maze.ROOM_SIZE // 2 + triangle_size, explorer_y + maze.ROOM_SIZE // 2 + triangle_size // 2 - yshift)
        ]
        draw.polygon(points, fill=maze.COLOR_EXPLORER, outline=maze.COLOR_TEXT, width=2)
        
        # 保存图像到文件
        output_path = "maze_map.jpg"
        img.save(output_path, "JPEG", quality=95)
        print(f"迷宫地图已保存到: {output_path}")
        
    except Exception as e:
        print(f"保存迷宫地图时出错: {str(e)}")

# 运行应用程序
if __name__ == "__main__":
    # 解析命令行参数
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--save-map":
        # 保存地图模式
        save_maze_map()
    else:
        # 正常运行应用程序
        root = tk.Tk()
        app = InteractiveExplorer(root)
        
        # 绑定窗口大小变化事件，以便调整地图大小
        def on_resize(event):
            app._update_map()
        
        root.bind("<Configure>", on_resize)
        
        # 添加一个简单的菜单，允许用户切换模拟模式
        menubar = tk.Menu(root)
        options_menu = tk.Menu(menubar, tearoff=0)
        
        # 模拟模式开关
        mock_var = tk.BooleanVar(value=app.mock_mode)
        def toggle_mock_mode():
            app.mock_mode = mock_var.get()
            status_text = "就绪（模拟模式）" if app.mock_mode else "就绪"
            status_bar.config(text=status_text)
            
        options_menu.add_checkbutton(label="启用模拟模式", variable=mock_var, command=toggle_mock_mode)
        menubar.add_cascade(label="选项", menu=options_menu)
        root.config(menu=menubar)
        
        # 更新状态栏
        status_bar = tk.Label(root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        root.mainloop()