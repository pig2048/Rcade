import requests
import json
import time
import os
import sys
import threading
import random
import datetime
import schedule
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()


DEFAULT_CONFIG = {
    "use_proxies": True,
    "max_workers": 5,
    "task_interval": 22,
    "retry_attempts": 3,
    "retry_delay": 5,
    "debug_mode": False
}


TOKEN_FILE = "token.txt"
ID_FILE = "id.txt"
PROXY_FILE = "proxy.txt"
CONFIG_FILE = "config.json"



CHECKIN_TASK = 1


BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                       SideQuest Bot                           ║
║              Author: https://x.com/snifftunes                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""


def get_user_info(user_id, token):
    url = f"https://lb.backend-sidequest.rcade.game/users/{user_id}"
    headers = {
        "authority": "lb.backend-sidequest.rcade.game",
        "accept": "*/*",
        "accept-language": "zh-HK,zh;q=0.9,zh-TW;q=0.8",
        "authorization": f"Bearer {token}",
        "origin": "https://sidequest.rcade.game",
        "referer": "https://sidequest.rcade.game/",
        "sec-ch-ua": "\"Chromium\";v=\"130\", \"Google Chrome\";v=\"130\", \"Not?A_Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        console.print(f"[bold red]获取用户信息失败: {str(e)} ❌[/bold red]")
        return None


def get_available_tasks(user_id, token):
    
    try:
        user_info = get_user_info(user_id, token)
        if not user_info:
            return [], []
            
        
        completed_task_ids = set(user_info.get("user", {}).get("quests", {}).keys())
        
    
        all_available_tasks = user_info.get("availableQuests", [])
        
        
        regular_tasks = []
        limited_tasks = []
        
        for task in all_available_tasks:
            task_id = task["_id"]
            
            if task_id not in completed_task_ids:
               
                if task.get("endTS", 0) > 0:
                    limited_tasks.append(int(task_id))
                else:
                    regular_tasks.append(int(task_id))
        
        return regular_tasks, limited_tasks
    except Exception as e:
        console.print(f"[bold red]获取可用任务失败: {str(e)} ❌[/bold red]")
        return [], []


def ensure_files_exist():
    for file in [TOKEN_FILE, ID_FILE, PROXY_FILE]:
        if not os.path.exists(file):
            with open(file, "w") as f:
                f.write("")
            console.print(f"[yellow]Created empty {file}[/yellow]")
    
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        console.print(f"[yellow]Created default {CONFIG_FILE}[/yellow]")


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def load_tokens():
    with open(TOKEN_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def load_user_ids():
    with open(ID_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def load_proxies():
    with open(PROXY_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def get_task_type_name(task_id, regular_tasks, limited_tasks):
    if task_id in regular_tasks:
        return "常规任务"
    elif task_id in limited_tasks:
        return "限时任务"
    elif task_id == CHECKIN_TASK:
        return "签到任务"
    else:
        return "未知任务"


def execute_task(account_index, user_id, token, task_id, regular_tasks, limited_tasks, proxy=None, debug=False, user_name=None):
    if user_name is None:
        user_name = f"账户{account_index+1}"
        
    task_type = get_task_type_name(task_id, regular_tasks, limited_tasks)
    url = f"https://lb.backend-sidequest.rcade.game/users/{user_id}/quests/{task_id}"
    
    headers = {
        "authority": "lb.backend-sidequest.rcade.game",
        "accept": "*/*",
        "accept-language": "zh-HK,zh;q=0.9,zh-TW;q=0.8",
        "authorization": f"Bearer {token}",
        "content-length": "2",
        "content-type": "text/plain;charset=UTF-8",
        "origin": "https://sidequest.rcade.game",
        "referer": "https://sidequest.rcade.game/",
        "sec-ch-ua": "\"Chromium\";v=\"130\", \"Google Chrome\";v=\"130\", \"Not?A_Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    
    proxies = None
    if proxy:
        if proxy.startswith("socks5://"):
            proxies = {"http": proxy, "https": proxy}
        else:
            if not proxy.startswith("http://") and not proxy.startswith("https://"):
                proxy = f"http://{proxy}"
            proxies = {"http": proxy, "https": proxy}
    
    console.print(f"[bold blue]{user_name}[/bold blue] 正在完成{task_type} ID为 [bold cyan]{task_id}[/bold cyan] 🔄")
    
    config = load_config()
    retry_attempts = config.get("retry_attempts", 3)
    retry_delay = config.get("retry_delay", 5)
    
    for attempt in range(retry_attempts):
        try:
            response = requests.post(url, headers=headers, proxies=proxies, timeout=30, data="{}")
            
            if debug:
                console.print(f"Debug - Response Code: {response.status_code}, Content: {response.text[:100]}")
            
            if response.status_code == 200:
                # 获取最新用户信息，包括积分
                user_info = get_user_info(user_id, token)
                points = user_info["user"]["points"] if user_info and "user" in user_info and "points" in user_info["user"] else None
                points_str = f"，当前总积分：{points}" if points is not None else ""
                
                console.print(f"[bold green]{user_name}[/bold green] 已完成{task_type} ID为 [bold cyan]{task_id}[/bold cyan]{points_str} ✅")
                return True
            else:
                console.print(f"[bold yellow]{user_name}[/bold yellow] 完成{task_type} ID为 [bold cyan]{task_id}[/bold cyan] 返回状态码: {response.status_code} ⚠️")
                return False
        except Exception as e:
            if attempt < retry_attempts - 1:
                console.print(f"[bold red]{user_name}[/bold red] 任务错误: {str(e)}, 尝试重试 ({attempt+1}/{retry_attempts}) 🔄")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]{user_name}[/bold red] 完成{task_type} ID为 [bold cyan]{task_id}[/bold cyan] 失败: {str(e)} ❌")
                return False


def run_tasks_for_account(account_index, user_id, token, proxy, task_list, regular_tasks, limited_tasks, is_limited=False):
    # 获取用户信息
    user_info = get_user_info(user_id, token)
    user_name = user_info["user"]["name"] if user_info and "user" in user_info and "name" in user_info["user"] else f"账户{account_index+1}"
    
    task_type = "限时任务" if is_limited else "常规任务"
    
    config = load_config()
    task_interval = config.get("task_interval", 22)
    debug_mode = config.get("debug_mode", False)
    
    for task_id in task_list:
        # 执行任务
        success = execute_task(account_index, user_id, token, task_id, regular_tasks, limited_tasks, proxy, debug_mode, user_name)
        
        # 如果不是最后一个任务，等待一段时间
        if task_id != task_list[-1]:
            time.sleep(task_interval)


def run_all_tasks(is_limited=False):
    tokens = load_tokens()
    user_ids = load_user_ids()
    proxies = load_proxies()
    config = load_config()
    
    if not tokens or not user_ids:
        console.print("[bold red]错误: token.txt 或 id.txt 文件为空! ❌[/bold red]")
        return
    
    # 计算账户数量
    num_accounts = min(len(tokens), len(user_ids))
    
    if config.get("use_proxies", True) and len(proxies) < num_accounts:
        console.print(f"[bold yellow]警告: 代理数量不足！仅有 {len(proxies)} 个代理但有 {num_accounts} 个账户 ⚠️[/bold yellow]")
        if len(proxies) == 0:
            console.print("[yellow]将不使用代理继续...[/yellow]")
    
    task_type = "限时任务" if is_limited else "普通任务"
    
    console.print(f"[bold green]开始执行{task_type}，共 {num_accounts} 个账户 🚀[/bold green]")
    
    max_workers = min(config.get("max_workers", 5), num_accounts)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(num_accounts):
            proxy = proxies[i] if i < len(proxies) and config.get("use_proxies", True) else None
            
            # 获取该账户的可用任务
            regular_tasks, limited_tasks = get_available_tasks(user_ids[i], tokens[i])
            
            # 根据类型选择任务列表
            task_list = limited_tasks if is_limited else regular_tasks
            
            if not task_list:
                console.print(f"[bold yellow]账户{i+1} 没有可用的{task_type} ⚠️[/bold yellow]")
                continue
                
            futures.append(
                executor.submit(
                    run_tasks_for_account,
                    i, user_ids[i], tokens[i], proxy, task_list, regular_tasks, limited_tasks, is_limited
                )
            )
        
        # 等待所有任务完成
        for future in futures:
            future.result()
    
    console.print(f"[bold green]所有{task_type}执行完毕 ✅[/bold green]")


def run_checkin():
    tokens = load_tokens()
    user_ids = load_user_ids()
    proxies = load_proxies()
    config = load_config()
    
    if not tokens or not user_ids:
        console.print("[bold red]错误: token.txt 或 id.txt 文件为空! ❌[/bold red]")
        return
    
    # 计算账户数量
    num_accounts = min(len(tokens), len(user_ids))
    
    if config.get("use_proxies", True) and len(proxies) < num_accounts:
        console.print(f"[bold yellow]警告: 代理数量不足！仅有 {len(proxies)} 个代理但有 {num_accounts} 个账户 ⚠️[/bold yellow]")
    
    for i in range(num_accounts):
        proxy = proxies[i] if i < len(proxies) and config.get("use_proxies", True) else None
        
        # 获取该账户的可用任务
        regular_tasks, limited_tasks = get_available_tasks(user_ids[i], tokens[i])
        
        # 执行签到任务
        console.print(f"[bold blue]账户{i+1}[/bold blue] 正在完成签到 🔄")
        success = execute_task(i, user_ids[i], tokens[i], CHECKIN_TASK, regular_tasks, limited_tasks, proxy)
        
        if success:
            next_checkin = datetime.datetime.now() + datetime.timedelta(days=1)
            next_checkin_str = next_checkin.strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"[bold green]账户{i+1}[/bold green] 签到成功，下次签到时间为: [bold cyan]{next_checkin_str}[/bold cyan] ✅")
        
        # 如果不是最后一个账户，等待一段时间
        if i < num_accounts - 1:
            time.sleep(2)
    
    console.print("[bold green]所有账户签到完毕 ✅[/bold green]")


def schedule_daily_checkin_and_tasks():
    schedule.clear()
    
    # 添加每24小时执行签到和检查任务
    schedule.every(24).hours.do(run_daily_tasks)
    
    console.print("[bold green]已设置每24小时自动签到并检查任务 ⏰[/bold green]")
    
    # 创建守护线程执行定时任务
    checkin_thread = threading.Thread(target=run_scheduler)
    checkin_thread.daemon = True
    checkin_thread.start()
    
    # 立即执行一次
    run_daily_tasks()


def run_daily_tasks():
    """执行每日任务：签到和检查新任务"""
    console.print("[bold cyan]执行每日签到和任务检查...[/bold cyan]")
    # 先执行签到
    run_checkin()
    # 检查并执行限时任务
    run_all_tasks(is_limited=True)
    # 检查并执行普通任务
    run_all_tasks(is_limited=False)
    console.print("[bold green]每日任务执行完毕 ✅[/bold green]")


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次是否有定时任务需要执行


def display_status():
    tokens = load_tokens()
    user_ids = load_user_ids()
    proxies = load_proxies()
    config = load_config()
    
    table = Table(title="SideQuest Bot 状态")
    
    table.add_column("项目", style="cyan")
    table.add_column("状态", style="green")
    
    table.add_row("账户数量", str(len(tokens)))
    table.add_row("代理数量", str(len(proxies)))
    table.add_row("代理状态", "启用" if config.get("use_proxies", True) else "禁用")
    table.add_row("并发数量", str(config.get("max_workers", 5)))
    table.add_row("任务间隔", f"{config.get('task_interval', 22)}秒")
    
    # 显示每个账户的任务状态和积分
    if tokens and user_ids:
        account_table = Table(title="账户信息")
        account_table.add_column("账户", style="cyan")
        account_table.add_column("积分", style="green")
        account_table.add_column("可用普通任务", style="yellow")
        account_table.add_column("可用限时任务", style="magenta")
        
        for i in range(min(len(tokens), len(user_ids))):
            user_info = get_user_info(user_ids[i], tokens[i])
            
            if user_info and "user" in user_info:
                user_name = user_info["user"].get("name", f"账户{i+1}")
                points = user_info["user"].get("points", "未知")
                
                # 获取可用任务
                regular_tasks, limited_tasks = get_available_tasks(user_ids[i], tokens[i])
                
                account_table.add_row(
                    user_name, 
                    str(points), 
                    str(len(regular_tasks)), 
                    str(len(limited_tasks))
                )
            else:
                account_table.add_row(f"账户{i+1}", "获取失败", "未知", "未知")
        
        console.print(table)
        console.print(account_table)
    else:
        console.print(table)


def show_menu():
    console.print(Panel(BANNER))
    
    while True:
        console.print("\n[bold cyan]==== SideQuest Bot 菜单 =====[/bold cyan]")
        console.print("1. [green]24小时签到并检查任务情况[/green]")
        console.print("2. [yellow]查看状态信息[/yellow]")
        console.print("3. [red]退出程序[/red]")
        
        choice = input("\n请选择操作 (1-3): ")
        
        if choice == '1':
            console.print("[bold green]启动24小时自动签到和任务检查模式，程序将持续运行。按 Ctrl+C 可以停止程序。[/bold green]")
            schedule_daily_checkin_and_tasks()
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("[bold red]\n自动签到和任务检查已停止 ⛔[/bold red]")
                break
                
        elif choice == '2':
            display_status()
        elif choice == '3':
            console.print("[bold green]感谢使用 SideQuest Bot! 👋[/bold green]")
            break
        else:
            console.print("[bold red]无效的选择，请重试![/bold red]")


if __name__ == "__main__":
    try:
        # 确保所需文件存在
        ensure_files_exist()
        
        # 加载配置
        config = load_config()
        console.print("[bold green]配置文件加载成功 ✅[/bold green]")
        
        # 显示菜单
        show_menu()
    except KeyboardInterrupt:
        console.print("[bold red]\n程序被用户中断 ⛔[/bold red]")
    except Exception as e:
        console.print(f"[bold red]错误: {str(e)} ❌[/bold red]")
        import traceback
        console.print(traceback.format_exc())
