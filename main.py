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
COMPLETED_TASKS_FILE = "completed_tasks.json"


REGULAR_TASKS = [5, 6, 7, 8, 9, 10, 13, 170, 171, 216, 217, 243, 263]


LIMITED_TASKS = [327, 328, 329, 330, 331, 332, 333]


CHECKIN_TASK = 1


BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                       SideQuest Bot                           ║
║              Author: https://x.com/snifftunes                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""


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
    
    if not os.path.exists(COMPLETED_TASKS_FILE):
        with open(COMPLETED_TASKS_FILE, "w") as f:
            json.dump({}, f, indent=4)
        console.print(f"[yellow]Created empty {COMPLETED_TASKS_FILE}[/yellow]")


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


def load_completed_tasks():
    try:
        with open(COMPLETED_TASKS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_completed_tasks(completed_tasks):
    with open(COMPLETED_TASKS_FILE, "w") as f:
        json.dump(completed_tasks, f, indent=4)


def get_task_type_name(task_id):
    if task_id in REGULAR_TASKS:
        return "常规任务"
    elif task_id in LIMITED_TASKS:
        return "限时任务"
    elif task_id == CHECKIN_TASK:
        return "签到任务"
    else:
        return "未知任务"


def execute_task(account_index, user_id, token, task_id, proxy=None, debug=False, user_name=None):
    if user_name is None:
        user_name = f"账户{account_index+1}"
        
    task_type = get_task_type_name(task_id)
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
                
                user_info = get_user_info(user_id, token)
                points = user_info["user"]["points"] if user_info and "user" in user_info and "points" in user_info["user"] else None
                points_str = f"，当前总积分：{points}" if points is not None else ""
                
                console.print(f"[bold green]{user_name}[/bold green] 已完成{task_type} ID为 [bold cyan]{task_id}[/bold cyan]{points_str} ✅")
                return True
            else:
                console.print(f"[bold yellow]{user_name}[/bold yellow] 完成{task_type} ID为 [bold cyan]{task_id}[/bold cyan] 返回状态码: {response.status_code} ⚠️")
                return True
        except Exception as e:
            if attempt < retry_attempts - 1:
                console.print(f"[bold red]{user_name}[/bold red] 任务错误: {str(e)}, 尝试重试 ({attempt+1}/{retry_attempts}) 🔄")
                time.sleep(retry_delay)
            else:
                console.print(f"[bold red]{user_name}[/bold red] 完成{task_type} ID为 [bold cyan]{task_id}[/bold cyan] 失败: {str(e)} ❌")
                return False


def run_tasks_for_account(account_index, user_id, token, proxy, task_list, completed_tasks, is_limited=False):
    
    user_info = get_user_info(user_id, token)
    user_name = user_info["user"]["name"] if user_info and "user" in user_info and "name" in user_info["user"] else f"账户{account_index+1}"
    
    account_key = f"account_{user_name}"  
    task_type = "限时任务" if is_limited else "常规任务"
    
    if account_key not in completed_tasks:
        completed_tasks[account_key] = {}
    
    config = load_config()
    task_interval = config.get("task_interval", 22)
    debug_mode = config.get("debug_mode", False)
    
    for task_id in task_list:
        task_key = f"task_{task_id}"
        
        
        if task_key in completed_tasks[account_key] and completed_tasks[account_key][task_key]:
            console.print(f"[bold yellow]{user_name}[/bold yellow] 跳过已完成的{task_type} ID为 [bold cyan]{task_id}[/bold cyan] ⏭️")
            continue
        
        
        success = execute_task(account_index, user_id, token, task_id, proxy, debug_mode, user_name)
        
       
        completed_tasks[account_key][task_key] = success
        save_completed_tasks(completed_tasks)
        
       
        if task_id != task_list[-1]:
            time.sleep(task_interval)


def run_all_tasks(is_limited=False):
    tokens = load_tokens()
    user_ids = load_user_ids()
    proxies = load_proxies()
    config = load_config()
    completed_tasks = load_completed_tasks()
    
    if not tokens or not user_ids:
        console.print("[bold red]错误: token.txt 或 id.txt 文件为空! ❌[/bold red]")
        return
    
    
    num_accounts = min(len(tokens), len(user_ids))
    
    if config.get("use_proxies", True) and len(proxies) < num_accounts:
        console.print(f"[bold yellow]警告: 代理数量不足！仅有 {len(proxies)} 个代理但有 {num_accounts} 个账户 ⚠️[/bold yellow]")
        if len(proxies) == 0:
            console.print("[yellow]将不使用代理继续...[/yellow]")
    
    task_list = LIMITED_TASKS if is_limited else REGULAR_TASKS
    task_type = "限时任务" if is_limited else "常规任务"
    
    console.print(f"[bold green]开始执行{task_type}，共 {num_accounts} 个账户 🚀[/bold green]")
    
    max_workers = min(config.get("max_workers", 5), num_accounts)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(num_accounts):
            proxy = proxies[i] if i < len(proxies) and config.get("use_proxies", True) else None
            futures.append(
                executor.submit(
                    run_tasks_for_account,
                    i, user_ids[i], tokens[i], proxy, task_list, completed_tasks, is_limited
                )
            )
        
        
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
    
    
    num_accounts = min(len(tokens), len(user_ids))
    
    if config.get("use_proxies", True) and len(proxies) < num_accounts:
        console.print(f"[bold yellow]警告: 代理数量不足！仅有 {len(proxies)} 个代理但有 {num_accounts} 个账户 ⚠️[/bold yellow]")
    
    for i in range(num_accounts):
        proxy = proxies[i] if i < len(proxies) and config.get("use_proxies", True) else None
        
       
        console.print(f"[bold blue]账户{i+1}[/bold blue] 正在完成签到 🔄")
        success = execute_task(i, user_ids[i], tokens[i], CHECKIN_TASK, proxy)
        
        if success:
            next_checkin = datetime.datetime.now() + datetime.timedelta(days=1)
            next_checkin_str = next_checkin.strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"[bold green]账户{i+1}[/bold green] 签到成功，下次签到时间为: [bold cyan]{next_checkin_str}[/bold cyan] ✅")
        
        
        if i < num_accounts - 1:
            time.sleep(2)
    
    console.print("[bold green]所有账户签到完毕 ✅[/bold green]")


def schedule_daily_checkin():
    schedule.clear()
    schedule.every(24).hours.do(run_checkin)
    
    console.print("[bold green]已设置每24小时自动签到 ⏰[/bold green]")
    
    
    checkin_thread = threading.Thread(target=run_scheduler)
    checkin_thread.daemon = True
    checkin_thread.start()
    
    
    run_checkin()


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  


def display_status():
    tokens = load_tokens()
    user_ids = load_user_ids()
    proxies = load_proxies()
    config = load_config()
    completed_tasks = load_completed_tasks()
    
    table = Table(title="SideQuest Bot 状态")
    
    table.add_column("项目", style="cyan")
    table.add_column("状态", style="green")
    
    table.add_row("账户数量", str(len(tokens)))
    table.add_row("代理数量", str(len(proxies)))
    table.add_row("代理状态", "启用" if config.get("use_proxies", True) else "禁用")
    table.add_row("并发数量", str(config.get("max_workers", 5)))
    table.add_row("任务间隔", f"{config.get('task_interval', 22)}秒")
    
    
    total_tasks = len(REGULAR_TASKS) + len(LIMITED_TASKS)
    completed_count = 0
    total_count = 0
    
    for account in completed_tasks:
        for task_key, completed in completed_tasks[account].items():
            total_count += 1
            if completed:
                completed_count += 1
    
    completion_rate = (completed_count / total_count * 100) if total_count > 0 else 0
    table.add_row("任务完成率", f"{completion_rate:.2f}% ({completed_count}/{total_count})")
    
    console.print(table)


def reset_completed_tasks():
    confirmation = input("确认重置所有任务完成状态？这将导致所有任务重新执行。(y/n): ")
    if confirmation.lower() == 'y':
        with open(COMPLETED_TASKS_FILE, "w") as f:
            json.dump({}, f, indent=4)
        console.print("[bold green]已重置所有任务完成状态 ✅[/bold green]")
    else:
        console.print("[yellow]已取消重置操作[/yellow]")


def show_menu():
    console.print(Panel(BANNER))
    
    while True:
        console.print("\n[bold cyan]==== SideQuest Bot 菜单 =====[/bold cyan]")
        console.print("1. [green]执行限时任务和普通任务[/green]")
        console.print("2. [green]启动24小时自动签到[/green]")
        console.print("3. [yellow]查看状态信息[/yellow]")
        console.print("4. [red]退出程序[/red]")
        
        choice = input("\n请选择操作 (1-4): ")
        
        if choice == '1':
            console.print("\n[bold]执行方式选择:[/bold]")
            console.print("1. [green]仅执行限时任务[/green]")
            console.print("2. [green]仅执行普通任务[/green]")
            console.print("3. [green]执行全部任务[/green]")
            
            task_choice = input("\n请选择执行方式 (1-3): ")
            
            if task_choice == '1':
                run_all_tasks(is_limited=True)
            elif task_choice == '2':
                run_all_tasks(is_limited=False)
            elif task_choice == '3':
                run_all_tasks(is_limited=True)
                time.sleep(2)
                run_all_tasks(is_limited=False)
            else:
                console.print("[bold red]无效的选择，请重试![/bold red]")
                
        elif choice == '2':
            console.print("[bold green]启动24小时自动签到模式，程序将持续运行。按 Ctrl+C 可以停止程序。[/bold green]")
            schedule_daily_checkin()
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("[bold red]\n自动签到已停止 ⛔[/bold red]")
                return
        elif choice == '3':
            display_status()
        elif choice == '4':
            console.print("[bold green]感谢使用 SideQuest Bot! 👋[/bold green]")
            break
        else:
            console.print("[bold red]无效的选择，请重试![/bold red]")


if __name__ == "__main__":
    try:
       
        ensure_files_exist()
        
        
        config = load_config()
        console.print("[bold green]配置文件加载成功 ✅[/bold green]")
        
       
        show_menu()
    except KeyboardInterrupt:
        console.print("[bold red]\n程序被用户中断 ⛔[/bold red]")
    except Exception as e:
        console.print(f"[bold red]错误: {str(e)} ❌[/bold red]")
        import traceback
        console.print(traceback.format_exc())


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