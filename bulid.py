import os
import sys
import subprocess

def create_build():
    print("========================================")
    print("🚀 欢迎使用 YomiKomi 一键智能打包工具")
    print("========================================\n")

    # 1. 尝试寻找 unidic_lite 的安装路径（最容易报错的一步，脚本帮你自动化解决了）
    try:
        import unidic_lite
        unidic_path = os.path.dirname(unidic_lite.__file__)
        dicdir = os.path.join(unidic_path, 'dicdir')
        print(f"✅ 成功找到日文分词字典库路径：{dicdir}")
    except ImportError:
        print("❌ 错误：未安装 unidic-lite！请先在终端运行：pip install unidic-lite")
        input("按回车键退出...")
        return

    # 2. 检查 dicts 文件夹是否存在
    if not os.path.exists("dicts"):
        print("❌ 错误：找不到 dicts 文件夹！请确保当前目录下有 dicts 文件夹，里面装着你的 CSV。")
        input("按回车键退出...")
        return
    print("✅ 成功找到本地词库文件夹 (dicts/)")

    # 3. 拼装 PyInstaller 命令
    # 注意：Windows 系统的 --add-data 分隔符是分号 ; (如果是 Mac 改为冒号 :)
    separator = ";" if sys.platform.startswith("win") else ":"
    
    cmd =[
        "pyinstaller",
        "--noconsole",                # 隐藏黑色控制台窗口
        "--onefile",                  # 打包为单文件
        "--name", "YomiKomi",         # 软件名称
        f"--add-data=dicts{separator}dicts",                    # 塞入自定义词库
        f"--add-data={dicdir}{separator}unidic_lite/dicdir",    # 塞入日语分词字典
        "main.py"                     # 你的主程序文件名（如果叫 test.py 请在这里改一下）
    ]

    # 4. 执行打包
    print("\n🔨 开始疯狂打包中，请耐心等待 1-3 分钟，不要关闭窗口...\n")
    try:
        subprocess.run(cmd, check=True)
        print("\n========================================")
        print("🎉 打包大功告成！")
        print("👉 请在当前目录新生成的 [dist] 文件夹里找到 YomiKomi.exe")
        print("========================================")
    except Exception as e:
        print(f"\n❌ 打包失败，请检查上方红字报错原因。错误信息：{e}")
        
    input("\n按回车键退出...")

if __name__ == "__main__":
    create_build()