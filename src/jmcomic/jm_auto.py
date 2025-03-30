import time
import os
import re
import threading
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
import jmcomic
import logging

# 日志文件路径
LOG_PATH = 'D:\Library\Repository\JMComic-Crawler-Python2\jmauto.log'
# 下载配置文件路径
OPTION_PATH = 'D:\Library\Repository\JMComic-Crawler-Python2\option.yml'
# 要监控的文件路径
pack_path = "D:\Library\Repository\JMComic-Crawler-Python2\pack.txt"
# 下载历史记录路径
HISTORY_PATH = 'D:\Library\Repository\JMComic-Crawler-Python2\history.txt'
# 延时处理等待时间
DELAY_TIME = 10
"""
日志级别：该日志仅限自动下载模块，使用以下几个标志位控制，请按需更改
LOG_HISTORY：仅打印处理的历史记录日志，只有处理行和历史记录文件写入日志
LOG_RUN：仅打印运行日志，包含运行日志
LOG_ALL：打印全部日志，包含启停日志

    如需修改JMcomic模块日志，请前往option.yml
"""
LOG_HISTORY = False
LOG_RUN = False
LOG_ALL = False

# 修改日志配置
logging.basicConfig(
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
    level=logging.INFO
)

# 自定义方法，处理文件修改事件
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, target_filename):
        super().__init__()
        self.target_filename = target_filename
        # 延迟处理的秒数
        self.delay = DELAY_TIME
        # 用于控制延迟处理的计时器
        self.timer = None
        # 线程锁防止资源竞争
        self.lock = threading.Lock()
    
    def on_modified(self, event):
        # 只处理pack.txt文件的修改事件
        if not event.is_directory and os.path.basename(event.src_path) == "pack.txt":
            if LOG_ALL | LOG_RUN :
                logging.info(f"文件已修改: {event.src_path}")
            with self.lock:
                # 如果已有计时器在运行，先取消
                if self.timer is not None:
                    self.timer.cancel()
                # 创建新计时器，延迟执行处理
                self.timer = threading.Timer(self.delay, self.process_pack_file, args=(event.src_path,))
                self.timer.start()
                if LOG_ALL | LOG_RUN :
                    logging.info(f"检测到文件修改，等待 {self.delay} 秒后处理...")

    def process_pack_file(self, pack_path):
        # 读取pack.txt中的所有行
        with open(pack_path, "r") as f:
            lines = f.readlines()
        
        if (not lines) & (LOG_ALL | LOG_RUN):
            logging.info("pack.txt文件为空，无需处理。")
            return

        # 使用正则表达式匹配5到7位数字
        pattern = re.compile(r"^\d{5,7}$")

        # 处理每一非空行
        processed_lines = []
        for line in lines:
            id_value = line.strip()
            if pattern.match(id_value):
                if LOG_ALL | LOG_RUN | LOG_HISTORY:
                    logging.info(f"处理ID: {id_value}")

                # 在此添加自定义逻辑（如调用API、写入数据库等）
                # 注意配置文件路径，默认为项目根目录
                jmcomic.create_option_by_file(OPTION_PATH).download_album(id_value)
                # 添加处理记录
                processed_lines.append(id_value)
        
        # 重新打开文件后清空文件（或保留未处理内容）
        with open(pack_path, "w") as f:
            f.seek(0)
            f.truncate()
            f.close()

        # 将文件内容添加到history.txt文件中
        with open(HISTORY_PATH, "a") as f:
            # 在字符串末尾加入换行避免与此后任务错误拼接
            f.write('\n'.join(processed_lines)+'\n')
            f.close()
        if LOG_ALL | LOG_RUN | LOG_HISTORY:
            logging.info(f"已将历史记录添加到 history.txt")

if __name__ == "__main__":
    # 获取绝对路径和目录
    target_abspath = os.path.abspath(pack_path)
    target_dir = os.path.dirname(target_abspath)
    target_filename = os.path.basename(target_abspath)

    if LOG_ALL :
        logging.info("监控目标:\n路径: %s\n目录: %s\n文件名: %s", target_abspath, target_dir, target_filename)

    event_handler = FileChangeHandler(target_filename)
    # 实例化Observer对象，设置监控路径和是否递归监控子目录（recursive=False表示不递归）
    # 使用轮询监控，保证docker正常运行（容器中普通观察者只能观测到容器级别的更改，来自宿主机的外部更改无法观测）
    # 非docker用户可以使用普通观察者
    observer = PollingObserver()
    observer.schedule(event_handler, path=target_dir, recursive=False)
    observer.start()
    if LOG_ALL :
        logging.info(f"开始监控文件: {target_abspath}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        # 确保退出前取消可能存在的计时器
        with event_handler.lock:
            if event_handler.timer is not None:
                event_handler.timer.cancel()
        if LOG_ALL :
            logging.info("停止监控")
    observer.join()
