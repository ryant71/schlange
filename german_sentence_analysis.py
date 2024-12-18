#!/usr/bin/env python3

import os
import re
import sys

from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import Horizontal, Vertical
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def analyze_german_sentence(sentence):
    # The prompt instructs ChatGPT to analyze the German sentence
    prompt = f"Analyze the following German sentence: '{sentence}'. Explain the grammar, vocabulary, and meaning."

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
    analysis = response.choices[0].message.content
    return analysis


def translate_text(input_text):
    # The prompt instructs ChatGPT to analyze the German input_text
    prompt = (f"Translate the following German sentence or word: '{input_text}'. Correct, if necessary.\n"
              "- Provide pronouns, articles, conjugations for all nouns\n"
              "- Provide simple example sentences for Nominative, Accusative, Dative\n"
              "- Try use the same nouns in the example sentences")

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
    analysis = response.choices[0].message.content
    return analysis


def format_response(response):
    response = "### Analysis/Translation\n" + response
    # Split the response by sections starting with ###
    sections = re.split(r"(### .+)", response)
    formatted_sections = []
    for i in range(1, len(sections), 2):  # Skip the first entry, which is the "Analysis:" line
        header = sections[i].strip()
        content = sections[i + 1].strip()
        markdown_text = f"{header}\n\n{content}"
        formatted_sections.append(Markdown(markdown_text))
    return formatted_sections


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

    if '-r' in sys.argv:
        raw = True
        sys.argv.remove('-r')
    else:
        raw = False

    if '-t' in sys.argv:
        translate = True
    else:
        translate = False

    input_text = input("Enter a German sentence: ")
    if not input_text:
        sys.exit()

    # Get analysis]
    if translate:
        analysis = translate_text(input_text)
    else:
        analysis = analyze_german_sentence(input_text)

    # Format the analysis
    formatted_response = format_response(analysis)

    if raw:
        print(analysis)
        print("--------------------")
        print(formatted_response)
    else:
        app = VerticalLayoutExample()
        app.run()
