import os
import subprocess
import shutil

def build():
    # 确保安装 pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.check_call(["pip", "install", "pyinstaller"])

    # 清理旧的构建文件
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    print("开始打包...")

    # 打包命令
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=warehouse",
        "--icon=icon.ico",
        "--add-data=config.json;.",
        "--add-data=icon.ico;.",
        "--hidden-import=customtkinter",
        "--hidden-import=PIL",
        "--hidden-import=pymupdf",
        "--hidden-import=pypinyin",
        "--hidden-import=pyperclip",
        "main.py"
    ]

    subprocess.check_call(cmd)

    print("\n打包完成！")
    print("可执行文件位置: dist/warehouse.exe")

if __name__ == "__main__":
    build()
