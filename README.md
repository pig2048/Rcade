# SideQuest Bot

一个用于自动化处理 SideQuest 游戏机器人，支持完成任务以及每日签到。

## 功能

- 自动化完成常规任务和限时任务。
- 每 24 小时自动执行每日签到。

## 安装说明

1. 克隆仓库到本地：
```bash
git clone https://github.com/pig2048/Rcade.git
cd Rcade
```

2. 创建并激活虚拟环境：
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 配置文件

### config.json

- 控制代理开关，并发数，时间间隔(默认任务是每隔22秒执行)

#### token.txt：包含身份验证令牌，每行一个。

#### id.txt：包含用户 ID，每行一个。

#### proxy.txt：包含代理地址，每行一个（可选）。

## 运行程序：
```bash
python main.py
```

