# -*- coding: utf-8 -*-
from __future__ import division, unicode_literals
import re
import io
from itertools import *
from . import config
from .messages import *

'''
Explanation of the BSFONT font file format:

BSFONT is a plain-text font format designed to be hand-authorable and easily readable.

A BSFONT file starts with one or more metadata lines.
These are lines of the form "Key: Value".
* **Character Height**: Required.  It specifies how many lines tall each character in the font is.  (All letters must be the same height.)
* **Space Width**: Optional.  This specifies the width of an ASCII space character in the font.  (Writing a space in the normal character format is hard to read.)

The first line that doesn't match the metadata format is assumed to be the start of the character data.
The character data is composed of groups of lines each specifying how to render one character.
The first line of each group is the character being described.  It should be the only text on the line.
The next several lines (equal to the **Character Height**) are the character itself, rendered as ASCII art.

For ASCII letters, if you define only one casing,
that rendering is used for both casings.
That is, if you only want capital letters,
just define it for "A", "B", etc,
and it'll automatically apply to "a", "b", etc as well.

Here is an example BSFONT file:

```
Character Height: 7
Space Width: 5
A
   ███
  ██ ██
 ██   ██
██     ██
█████████
██     ██
██     ██
B
████████
██     ██
██     ██
████████
██     ██
██     ██
████████
```

This defines a font capable of rendering text composed of "A", "B", "a", "b", and " ".

'''

class Font(object):
    def __init__(self, fontfilename=config.scriptPath + "/bigblocks.bsfont"):
        try:
            lines = io.open(fontfilename, 'r', encoding="utf-8").readlines()
        except Exception, e:
            die("Couldn't find font file “{0}”:\n{1}", fontfilename, e)
        self.metadata, lines = parseMetadata(lines)
        self.characters = parseCharacters(self.metadata, lines)

    def write(self, text):
        output = ['']*self.metadata["height"]
        for letterIndex, letter in enumerate(text):
            if letter in self.characters:
                for i, line in enumerate(self.characters[letter]):
                    if letterIndex != 0:
                        output[i] += " "
                    output[i] += line
            else:
                die("The character “{0}” doesn't appear in the specified font.", letter)
        output = [line + "\n" for line in output]
        return output


def parseMetadata(lines):
    # Each metadata line is of the form "key: value".
    # First line that's not of that form ends the metadata.
    # Returns the parsed metadata, and the non-metadata lines
    md = {}
    nameMapping = {
        "Character Height": "height",
        "Space Width": "space-width"
    }
    valProcessors = {
        "height": int,
        "space-width": int
    }
    for i, line in enumerate(lines):
        match = re.match(r"([^:]+):\s+(\S.*)", line)
        if not match:
            break
        key = match.group(1)
        val = match.group(2)
        if key in nameMapping:
            key = nameMapping[key]
        else:
            die("Unrecognized font metadata “{0}”", key)
        if key in valProcessors:
            val = valProcessors[key](val)
        md[key] = val
    return md, lines[i:]

def parseCharacters(md, lines):
    import string
    height = md['height']
    characters = {}
    if "space-width" in md:
        characters[" "] = [" "*md['space-width']]*height
    for bigcharlines in grouper(lines, height+1):
        littlechar = bigcharlines[0][0]
        bigchar = [line.strip("\n") for line in bigcharlines[1:]]
        width = max(len(l) for l in bigchar)
        for i, line in enumerate(bigchar):
            # Make sure the letter is a rectangle.
            if len(line) < width:
                bigchar[i] += " " * (width - len(line))
        characters[littlechar] = bigchar
    for char in string.ascii_lowercase:
        # Allow people to specify only one case for letters if they want.
        if char in characters and char.upper() not in characters:
            characters[char.upper()] = characters[char]
        if char.upper() in characters and char not in characters:
            characters[char] = characters[char.upper()]
    return characters

def replaceComments(font, inputFilename=None, outputFilename=None):
    lines, inputFilename = getInputLines(inputFilename)
    replacements = []
    for i, line in enumerate(lines):
        match = re.match(r"\s*<!--\s*Big Text:\s*(\S.*)-->", line)
        if match:
            newtext = ["<!--\n"] + font.write(match.group(1).strip()) + ["-->\n"]
            replacements.append({
                'line': i,
                'content': newtext
            })
    for r in reversed(replacements):
        lines[r['line']:r['line']+1] = r['content']
    writeOutputLines(outputFilename, inputFilename, lines)






# Some utility functions

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return (list(x) for x in izip_longest(fillvalue=fillvalue, *args))

def getInputLines(inputFilename):
    if inputFilename is None:
        # Default to looking for a *.bs file.
        # Otherwise, look for a *.src.html file.
        # Otherwise, use standard input.
        import glob
        if glob.glob("*.bs"):
            inputFilename = glob.glob("*.bs")[0]
        elif glob.glob("*.src.html"):
            inputFilename = glob.glob("*.src.html")[0]
        else:
            inputFilename = "-"
    try:
        if inputFilename == "-":
            lines = [unicode(line, encoding="utf-8") for line in sys.stdin.readlines()]
        else:
            lines = io.open(inputFilename, 'r', encoding="utf-8").readlines()
    except OSError:
        die("Couldn't find the input file at the specified location '{0}'.", inputFilename)
        return []
    except IOError:
        die("Couldn't open the input file '{0}'.", inputFilename)
        return []
    return lines, inputFilename

def writeOutputLines(outputFilename, inputFilename, lines):
    if outputFilename is None:
        outputFilename = inputFilename
    try:
        if outputFilename == "-":
            outputFile = sys.stdout.write(''.join(lines))
        else:
            with io.open(outputFilename, "w", encoding="utf-8") as f:
                f.write(''.join(lines))
    except Exception, e:
        die("Something prevented me from saving the output document to {0}:\n{1}", outputFilename, e)
