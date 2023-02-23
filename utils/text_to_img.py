from io import BytesIO

from PIL import Image
from graia.ariadne.message.element import Image as GraiaImage

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.tables import TableExtension
from mdx_math import MathExtension

from pygments.formatters import HtmlFormatter
from pygments.styles.xcode import XcodeStyle

import imgkit

def md_to_html(text):
    extensions = [
        MathExtension(enable_dollar_delimiter=True),  # 开启美元符号渲染
        CodeHiliteExtension(linenums=False, css_class='highlight', noclasses=False, guess_lang=True),  # 添加代码块语法高亮
        TableExtension(),
        'fenced_code'
    ]
    md = markdown.Markdown(extensions=extensions)
    html = md.convert(text)

    # 获取 Pygments 生成的 CSS 样式
    css_style = HtmlFormatter(style=XcodeStyle).get_style_defs('.highlight')

    # 将 CSS 样式插入到 HTML 中
    html = f"<style>{css_style}</style>\n{html}"

    return html

def text_to_image(text):
    
    content = md_to_html(text)

    with open('./utils/markdown_support_template.html', 'r') as input_file:
        with open('./utils/temp.html', 'w') as output_file:
            for line in input_file:
                if "{{ md_to_html(text) }}" in line:
                    line = line.replace("{{ md_to_html(text) }}", content)
                output_file.write(line)

   
   # wkhtmltoimage是用apt安装的，安装wkhtmltopdf附带，binary文件在/usr/bin/wkhtmltoimage
    config = imgkit.config(wkhtmltoimage='/usr/bin/wkhtmltoimage')

    options = {
        "enable-local-file-access": None, # wkhtmltoimage默认禁用local，所以需要开启读取local文件的权限
        "width": 500 # 图片宽度
    }

    # 调用imgkit将html转为图片
    image1 = imgkit.from_file(filename="./utils/temp.html",  config=config, options=options, output_path="temp.jpg")

    # 调用PIL将图片读取为PNG，RGB格式
    image = Image.open('temp.jpg').convert('RGB')

    return image


def to_image(text) -> GraiaImage:
    img = text_to_image(text=text)
    b = BytesIO()
    img.save(b, format="png")
    return GraiaImage(data_bytes=b.getvalue())
