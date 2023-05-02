from zipimport import zipimporter


# zipimport patch to fix Markdown module unable installing to embedded Python
# Refer to https://gitee.com/zmister/MrDoc/issues/I3P1AK#note_5014508_link
def create_module(self, spec):
    return None


zipimporter.create_module = create_module


def exec_module(self, module):
    exec(self.get_code(module.__name__), module.__dict__)


zipimporter.exec_module = exec_module

def patch():
    # 仅仅是为了防止 IDE 自动优化
    pass