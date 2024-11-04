#!/usr/bin/env python3

import sys
import random

from libnouns import nouns


def quiz(prompt_lang):
    while True:
        try:
            # Select a random category and word pair
            category = random.choice(list(nouns.keys()))
            german_word, english_word = random.choice(list(nouns[category].items()))

            if prompt_lang == "german":
                while True:
                    answer = input(f"What is the English for '{german_word}'? ")
                    if answer.lower() == english_word:
                        print("Correct!")
                        break
                    else:
                        print(f"Incorrect. The correct answer is '{english_word}'.")
                        print("Write it again: ")

            elif prompt_lang == "english":
                while True:
                    answer = input(f"What is the German (with correct gender) for '{english_word}'? ")
                    if answer.lower() == german_word.lower():
                        print("Correct!")
                        break
                    else:
                        print(f"Incorrect. The correct answer is '{german_word}'.")
                        print("Write it again: ")

        except KeyboardInterrupt:
            sys.exit()


# Command line interaction
if __name__ == "__main__":
    direction = input("Choose quiz direction: Type 'german' for German-to-English or 'english' for English-to-German: ").lower()
    if direction in ["german", "english"]:
        quiz(direction)
    else:
        print("Invalid choice. Please restart and type 'german' or 'english'.")
