from config import Config
from PIL import Image, ImageDraw, ImageFont
import textwrap
import itertools
import unicodedata

config = Config.load_config()

class TextWrapper(textwrap.TextWrapper):
    char_widths = {
        'W' : 2, # Wide
        'Na' : 1, # Narrow
        'F' : 2, # Fullwidth
        'H' : 1, # Half-width
        'A' : 2, # ?
        'N' : 1 # Neutral
    }
    
    def _strlen(self, text):
        """
        Calcaute display length of a line
        """
        charslen = 0
        for char in text:
            charslen += self.char_widths[unicodedata.east_asian_width(char)]
        return charslen

    def _wrap_chunks(self, chunks):
        """_wrap_chunks(chunks : [string]) -> [string]
        Code from https://github.com/python/cpython/blob/3.9/Lib/textwrap.py

        Wrap a sequence of text chunks and return a list of lines of
        length 'self.width' or less.  (If 'break_long_words' is false,
        some lines may be longer than this.)  Chunks correspond roughly
        to words and the whitespace between them: each chunk is
        indivisible (modulo 'break_long_words'), but a line break can
        come between any two chunks.  Chunks should not have internal
        whitespace; ie. a chunk is either all whitespace or a "word".
        Whitespace chunks will be removed from the beginning and end of
        lines, but apart from that whitespace is preserved.
        """
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)
        if self.max_lines is not None:
            if self.max_lines > 1:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            if len(indent) + len(self.placeholder.lstrip()) > self.width:
                raise ValueError("placeholder too large for max width")

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks.reverse()

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            # Maximum width for this line.
            width = self.width - len(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1].strip() == '' and lines:
                del chunks[-1]

            while chunks:
                l = self._strlen(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l

                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and self._strlen(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
                cur_len = sum(map(self._strlen, cur_line))

            # If the last chunk on this line is all whitespace, drop it.
            if self.drop_whitespace and cur_line and cur_line[-1].strip() == '':
                cur_len -= self._strlen(cur_line[-1])
                del cur_line[-1]

            if cur_line:
                if (self.max_lines is None or
                    self._strlen(lines) + 1 < self.max_lines or
                    (not chunks or
                     self.drop_whitespace and
                     self._strlen(chunks) == 1 and
                     not chunks[0].strip()) and cur_len <= width):
                    # Convert current line back to a string and store it in
                    # list of all lines (return value).
                    lines.append(indent + ''.join(cur_line))
                else:
                    while cur_line:
                        if (cur_line[-1].strip() and
                            cur_len + self._strlen(self.placeholder) <= width):
                            cur_line.append(self.placeholder)
                            lines.append(indent + ''.join(cur_line))
                            break
                        cur_len -= len(cur_line[-1])
                        del cur_line[-1]
                    else:
                        if lines:
                            prev_line = lines[-1].rstrip()
                            if (self._strlen(prev_line) + self._strlen(self.placeholder) <=
                                    self.width):
                                lines[-1] = prev_line + self.placeholder
                                break
                        lines.append(indent + self.placeholder.lstrip())
                    break

        return lines
    
    def _get_space_left(self, text, requested_len):
        """
        Calcuate actual space_left
        """
        charslen = 0
        counter = 0
        for char in text:
            counter = counter + 1
            charslen += self.char_widths[unicodedata.east_asian_width(char)]
            if(charslen >= requested_len):
                break
        return counter

    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        """_handle_long_word(chunks : [string],
                             cur_line : [string],
                             cur_len : int, width : int)
        Handle a chunk of text (most likely a word, not whitespace) that
        is too long to fit in any line.
        """
        # Figure out when indent is larger than the specified width, and make
        # sure at least one character is stripped off on every pass
        if width < 1:
            space_left = 1
        else:
            space_left = width - cur_len

        # If we're allowed to break long words, then do so: put as much
        # of the next chunk onto the current line as will fit.
        space_left = self._get_space_left(reversed_chunks[-1], space_left)
        if self.break_long_words:
            cur_line.append(reversed_chunks[-1][:space_left])
            reversed_chunks[-1] = reversed_chunks[-1][space_left:]

        # Otherwise, we have to preserve the long word intact.  Only add
        # it to the current line if there's nothing already there --
        # that minimizes how much we violate the width constraint.
        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

        # If we're not allowed to break long words, and there's already
        # text on the current line, do nothing.  Next time through the
        # main loop of _wrap_chunks(), we'll wind up here again, but
        # cur_len will be zero, so the next line will be entirely
        # devoted to the long word that we can't handle right now.
    def _split_chunks(self, text):
        text = self._munge_whitespace(text)
        return self._split(text)

def text_to_image(text, width=config.text_to_image.width, font_name=config.text_to_image.font_path, font_size=config.text_to_image.font_size, offset_x=config.text_to_image.offset_x, offset_y=config.text_to_image.offset_y):
    # Create a draw object that can be used to measure the size of the text
    draw = ImageDraw.Draw(Image.new('RGB', (width, 1)))

    # Use the specified font to measure the size of the text
    font = ImageFont.truetype(font_name, font_size)
    lines = text.split('\n')
    line_lengths = [draw.textlength(line, font=font) for line in lines]
    text_width = max(line_lengths)
    text_height = font.getsize(text)[1]
    char_width = font.getsize('.')[0]

    wrapper = TextWrapper(width=int(width / char_width), break_long_words=True)
    wrapped_text = [wrapper.wrap(i) for i in lines if i != '']
    wrapped_text = list(itertools.chain.from_iterable(wrapped_text))

    # Calculate the height of the image based on the number of lines of text
    height = text_height * len(wrapped_text)

    # Add the height of the text to the height of the image
    height += text_height

    # Convert the height to an integer
    height = int(height)

    # Create a new image with the calculated height and the specified width
    image = Image.new('RGB', (width + offset_x * 2, height + offset_y), color='white')

    # Create a draw object that can be used to draw on the image
    draw = ImageDraw.Draw(image)

    # Use the specified font to write the text on the image
    font = ImageFont.truetype(font_name, font_size)

    # Draw the wrapped text on the image
    draw.text((offset_x, offset_y), '\n'.join(wrapped_text), font=font, fill='black')

    return image