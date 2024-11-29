#!/usr/bin/env python3

import os
import re
import sys
import json

from rich.markdown import Markdown
# from rich.console import Console
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


def get_translation_from_json(json_file_path, input_text):
    with open(json_file_path, 'r') as file:
        data = json.load(file)
        return f"{data[input_text]}\n\n[json]"


def format_response(response):
    response = "### Translation\n" + response
    # Split the response by sections starting with ###
    sections = re.split(r"(### .+)", response)
    formatted_sections = []
    for i in range(1, len(sections), 2):
        header = sections[i].strip()
        content = sections[i + 1].strip()
        markdown_text = f"{header}\n\n{content}"
        formatted_sections.append(Markdown(markdown_text))
    return formatted_sections


def log_raw_markdown(markdown_file_path, input_text, translation):
    log_text = f"# Input\n{input_text}\n\n# Translation\n{translation}\n\n"
    with open(json_file_path, "a") as log:
        log.write(log_text)


def is_input_in_json(json_file_path, input_text):

    # Open and load the JSON file
    if not os.path.exists(json_file_path):
        with open(json_file_path, 'w+') as file:
            file.write('{}')

    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Check if the input_text exists
    if input_text in data:
        return True
    else:
        return False


def log_to_json(json_file_path, input_text, translation):
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)

        data[input_text] = translation

        with open(json_file_path, 'w+') as file:
            json.dump(data, file, indent=4)

    except FileNotFoundError:
        # print(f"The file '{json_file_path}' does not exist.")
        return
    except json.JSONDecodeError:
        # print(f"Error decoding JSON from the file '{json_file_path}'.")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return


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

    markdown_file_path = os.path.expanduser("~/.german/translations.md")
    json_file_path = os.path.expanduser("~/.german/translations.json")

    try:
        sys.argv[1]
        input_text = " ".join(sys.argv[1:])
    except IndexError:
        input_text = input("Enter word or sentence in German or English: ")

    if not input_text:
        sys.exit()

    if not is_input_in_json(json_file_path, input_text):
        # get translation from chatgpt
        translation = translate_text(input_text)
        log_to_json(json_file_path, input_text, translation)
    else:
        translation = get_translation_from_json(json_file_path, input_text)

    # Format the translation
    formatted_response = format_response(translation)

    app = VerticalLayoutExample()
    app.run()
