import os
import subprocess
import sys

from kirara_ai.entry import init_application, run_application
from kirara_ai.internal import get_and_reset_restart_flag


def main():
    container = init_application()
    try:
        run_application(container)
    finally:
        if get_and_reset_restart_flag():
            # 重新启动程序
            process = subprocess.Popen([sys.executable, "-m", "kirara_ai"], env=os.environ, cwd=os.getcwd())
            process.wait()

if __name__ == "__main__":
    main()