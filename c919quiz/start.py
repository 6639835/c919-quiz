#!/usr/bin/env python3
"""
C919飞机机型培训题库练习系统启动脚本
"""
import os
import sys
import webbrowser
import time
import subprocess
import signal
from threading import Thread

# 全局变量，用于退出清理
is_exiting = False

def signal_handler(sig, frame):
    """处理程序退出信号"""
    global is_exiting
    if is_exiting:  # 防止重复执行
        return
    
    is_exiting = True
    print("\n正在关闭应用...")
    clean_temp_files()
    sys.exit(0)

def clean_temp_files():
    """清理临时文件"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cache_dir = os.path.join(current_dir, 'cache')
        
        if os.path.exists(cache_dir):
            print("清理临时缓存文件...")
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"无法删除文件 {file_path}: {e}")
    except Exception as e:
        print(f"清理临时文件时出错: {e}")

def open_browser():
    """在默认浏览器中打开应用程序"""
    time.sleep(1.5)  # 给服务器一些启动时间
    try:
        webbrowser.open('http://127.0.0.1:5000/')
        print("已在浏览器中打开应用。")
    except Exception as e:
        print(f"无法自动打开浏览器: {e}")
        print("请手动访问: http://127.0.0.1:5000/")

def install_dependencies():
    """安装所需依赖"""
    print("\n正在检查并安装必要的依赖...")
    required_packages = ['flask', 'pandas', 'openpyxl']
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"- {package} 已安装")
        except ImportError:
            print(f"- 安装 {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"  {package} 安装成功")
            except subprocess.CalledProcessError as e:
                print(f"  安装 {package} 失败: {e}")
                return False
    return True

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 50)
    print("C919飞机机型培训题库练习系统")
    print("=" * 50)
    
    # 检查必要的依赖是否已安装
    if not install_dependencies():
        print("\n依赖安装失败，程序无法启动。")
        input("按任意键退出...")
        sys.exit(1)
    
    # 检查数据文件是否存在
    data_file = os.path.join(current_dir, 'data', 'C919飞机机型培训题库.xlsx')
    if not os.path.exists(data_file):
        print(f"错误: 找不到题库文件: {data_file}")
        print("请确保题库文件已放置在正确的位置。")
        input("按任意键退出...")
        sys.exit(1)
    
    print("\n正在启动应用服务器...")
    print("应用将在默认浏览器中自动打开...\n")
    
    # 自动在浏览器中打开应用
    Thread(target=open_browser).start()
    
    # 启动Flask应用
    try:
        from app import app
        # 只在本地启动时使用 host='0.0.0.0'
        app.run(host='127.0.0.1', port=5000, debug=False)
    except Exception as e:
        print(f"启动应用服务器失败: {e}")
        input("按任意键退出...")
        sys.exit(1) 