import markdown
from PIL import Image, ImageDraw, ImageFont
import textwrap
import itertools

def text_to_image(text, width=620, font_name='fonts/sarasa-mono-sc-regular.ttf', font_size=30, offset_x=50, offset_y=50):
    # Create a draw object that can be used to measure the size of the text
    draw = ImageDraw.Draw(Image.new('RGB', (width, 1)))

    # Use the specified font to measure the size of the text
    font = ImageFont.truetype(font_name, font_size)
    lines = text.split('\n')
    line_lengths = [draw.textlength(line, font=font) for line in lines]
    text_width = max(line_lengths)
    text_height = font.getsize(text)[1]

    char_width, char_height = font.getsize('测')

    # Wrap the text to the next line if it's too long to fit on a single line
    wrapper = textwrap.TextWrapper(width=int(width / char_width))
    wrapped_text = [wrapper.wrap(i) for i in lines if i != '']
    wrapped_text = list(itertools.chain.from_iterable(wrapped_text))

    # Calculate the height of the image based on the number of lines of text
    height = text_height * len(wrapped_text)

    # Add the height of the text to the height of the image
    height += text_height

    # Convert the height to an integer
    height = int(height)

    # Create a new image with the calculated height and the specified width
    image = Image.new('RGB', (width + offset_x, height + offset_y), color='white')

    # Create a draw object that can be used to draw on the image
    draw = ImageDraw.Draw(image)

    # Use the specified font to write the text on the image
    font = ImageFont.truetype(font_name, font_size)

    # Draw the wrapped text on the image
    draw.text((offset_x, offset_y), '\n'.join(wrapped_text), font=font, fill='black')

    return image