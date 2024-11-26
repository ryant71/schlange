#!/usr/bin/env python3

import os
import re
import sys

from rich.markdown import Markdown
from rich.console import Console
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal, Vertical
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def translate_text(input_text):
    # The prompt instructs ChatGPT to analyze the German input_text
    prompt = ("Translate the following German to english "
              f"or english to German: '{input_text}'.\n"
              "If a single word is given, provide the singular and plural"
              "forms and articles. Mention the gender of the articles.\n"
              "Correct, if necessary.\n")

    # Send the prompt to ChatGPT
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    # Extract the response text
    translation = response.choices[0].message.content
    return translation


def format_response(response):
    response = "### Translation\n" + response
    # Split the response by sections starting with ###
    sections = re.split(r"(### .+)", response)
    formatted_sections = []
    for i in range(1, len(sections), 2):  # Skip the first entry, which is the "Analysis:" line
        header = sections[i].strip()
        content = sections[i + 1].strip()
        markdown_text = f"{header}\n\n{content}"
        formatted_sections.append(Markdown(markdown_text))
    return formatted_sections


def log_raw_markdown(input_text, translation):
    log_text = f"# Input\n{input_text}\n\n# Translation\n{translation}\n\n"
    file_path = os.path.expanduser("~/.german/translations.md")
    with open(file_path, "a") as log:
        log.write(log_text)


def make_rows(format_response):
    for line in formatted_response:
        yield Static(line, classes="box")


class VerticalLayoutExample(App):

    DEFAULT_CSS = """

    Screen {
        layout: horizontal;
        overflow-y: auto;
        height: 1fr;
    }

    .left-column {
        width: 20%;
    }

    .right-column {
        width: 80%;
        overflow-y: auto;
    }

    .box {
        border: solid green;
        padding: 1;
        padding-left: 1;
        padding-right: 2;
        margin-bottom: 0;
    }

    """

    def compose(self) -> ComposeResult:

        with Horizontal():

            with Vertical(classes="left-column"):
                yield Static(input_text, classes="box")

            with Vertical(classes="right-column"):
                for row in make_rows(formatted_response):
                    yield row

    def on_key(self, event):
        """Handle key presses"""
        if event.key == "q":
            self.exit()


if __name__ == "__main__":

    try:
        sys.argv[1]
        input_text = " ".join(sys.argv[1:])
    except IndexError:
        input_text = input("Enter word or sentence in German or English: ")

    if not input_text:
        sys.exit()

    translation = translate_text(input_text)

    # Format the translation
    formatted_response = format_response(translation)

    log_raw_markdown(input_text, translation)

    app = VerticalLayoutExample()
    app.run()
