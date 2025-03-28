import time
import os
import re
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import jmcomic

# 自定义方法，处理文件修改事件
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, target_filename):
        super().__init__()
        self.target_filename = target_filename
        # 延迟处理的秒数
        self.delay = 20
        # 用于控制延迟处理的计时器
        self.timer = None
        # 线程锁防止资源竞争
        self.lock = threading.Lock()
    
    def on_modified(self, event):
        # 只处理pack.txt文件的修改事件
        if not event.is_directory and os.path.basename(event.src_path) == "pack.txt":
            print(f"文件已修改: {event.src_path}")
            with self.lock:
                # 如果已有计时器在运行，先取消
                if self.timer is not None:
                    self.timer.cancel()
                # 创建新计时器，延迟执行处理
                self.timer = threading.Timer(self.delay, self.process_pack_file, args=(event.src_path,))
                self.timer.start()
                print(f"检测到文件修改，等待 {self.delay} 秒后处理...")

    def process_pack_file(self, file_path):
        # 读取pack.txt中的所有行
        with open(file_path, "r") as f:
            lines = f.readlines()
        
        if not lines:
            print("pack.txt文件为空，无需处理。")
            return

        # 使用正则表达式匹配5到7位数字
        pattern = re.compile(r"^\d{5,7}$")

        # 处理每一非空行
        processed_lines = []
        for line in lines:
            line = line.strip()
            if pattern.match(line):
                print(f"处理行: {line}")

                id_value = line
                # 在此添加自定义逻辑（如调用API、写入数据库等）
                # 注意配置文件路径，默认为项目根目录
                jmcomic.create_option_by_file('../../option.yml').download_album(id_value)

                processed_lines.append(line)
        
        # 清空文件（或保留未处理内容）
        with open(file_path, "w") as f:
            f.seek(0)
            f.truncate()

        # 将文件内容添加到同目录下的history.txt文件中
        history_file = os.path.join(os.path.dirname(file_path), "history.txt")
        with open(history_file, "a") as f:
            f.write('\n'+'\n'.join(processed_lines))
        print(f"已将 id: {id_value} 添加到 history.txt")

if __name__ == "__main__":
    # 要监控的文件路径
    FILE_PATH = "../../pack.txt"
    # 获取绝对路径和目录
    target_abspath = os.path.abspath(FILE_PATH)
    target_dir = os.path.dirname(target_abspath)
    target_filename = os.path.basename(target_abspath)

    print(target_abspath ,'\n' , target_dir , '\n', target_filename)

    event_handler = FileChangeHandler(target_filename)
    # 实例化Observer对象，设置监控路径和是否递归监控子目录（recursive=False表示不递归）
    observer = Observer()
    observer.schedule(event_handler, path=target_dir, recursive=False)
    observer.start()
    print(f"开始监控文件: {target_abspath}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        # 确保退出前取消可能存在的计时器
        with event_handler.lock:
            if event_handler.timer is not None:
                event_handler.timer.cancel()
        print("停止监控")
    observer.join()
