# 谁是卧底 - 在线多人游戏

基于 Flask + Socket.IO 的实时多人"谁是卧底"网页游戏。

## 技术栈

- **后端**: Python / Flask / Flask-SocketIO
- **前端**: 原生 HTML / CSS / JavaScript + Socket.IO
- **通信**: WebSocket 实时双向通信

## 项目结构

```
who_is_undercover/
├── app.py              # Flask 主应用 + WebSocket 事件处理
├── words.json          # 词库（25 组平民词/卧底词配对）
├── requirements.txt    # Python 依赖
├── static/
│   ├── style.css       # 页面样式
│   └── script.js       # 前端交互逻辑
└── templates/
    └── index.html      # 页面模板
```

## 部署步骤

### 1. 环境要求

- Python 3.8+
- pip 包管理器

### 2. 安装依赖

```bash
cd who_is_undercover
pip install -r requirements.txt
```
从 Python 3.11 开始，Debian/Ubuntu 等发行版将系统 Python 标记为"外部管理"，禁止直接用 pip 全局安装包，可以使用以下命令强制安装依赖。
```bash
cd who_is_undercover
pip install -r requirements.txt --break-system-packages
```
也可以使用虚拟环境安装。
### 3. 启动服务

```bash
python app.py
```

启动后终端会显示：

```
 * Serving Flask app 'app'
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

### 4. 访问游戏

- **本机访问**: 浏览器打开 `http://127.0.0.1:5000`
- **局域网访问**: 同一 Wi-Fi 下的其他设备访问 `http://<你的局域网IP>:5000`
  - macOS 查看局域网 IP：`ifconfig | grep "inet "` 或系统偏好设置 → 网络

## 使用说明

### 游戏流程

1. **加入游戏**: 每位玩家打开网页，输入群昵称，点击"加入游戏"
2. **开始游戏**: 至少 4 名玩家加入后，任意玩家点击"开始游戏"
3. **查看词语**: 系统自动分配词语（15-33% 的玩家为卧底），每人只能看到自己的词
4. **开始投票**: 描述讨论结束后，点击"开始本轮投票"
5. **投票**: 15 秒倒计时内，选择一名玩家投票（不能投自己，每人限投一次）
6. **公布结果**: 得票最多的玩家出局，显示其身份；平局则无人出局
7. **下一轮**: 5 秒后自动进入下一轮，重新分配词语
8. **结束游戏**: 任意时刻可点击"结束游戏"，所有玩家回到初始界面

### 规则说明

| 项目 | 说明 |
|------|------|
| 最少人数 | 4 人 |
| 卧底比例 | 15% ~ 33%（随机） |
| 投票时间 | 每轮 15 秒 |
| 投票规则 | 每人一票，不能投自己 |
| 平局处理 | 得票相同则本轮无人出局，进入下一轮 |

### 自定义词库

编辑 `words.json` 文件即可添加或修改词语配对：

```json
{
  "word_pairs": [
    {"civilian": "平民词", "undercover": "卧底词"},
    {"civilian": "另一个平民词", "undercover": "对应的卧底词"}
  ]
}
```

修改后重启服务生效。

## 注意事项

- 游戏开始后新玩家无法加入
- 所有玩家需在同一网络环境下（局域网）或通过公网访问同一服务器
- 如需公网访问，可使用 ngrok 等内网穿透工具：`ngrok http 5000`
### Bug反馈
发现Bug可以发邮箱给huangjiakai14@oulook.com
