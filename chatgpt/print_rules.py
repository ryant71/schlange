#!/usr/bin/env python3

import click
from tabulate import tabulate
from german_rules import GermanGrammarRules

# Create an instance of the GermanGrammarRules class
german_rules = GermanGrammarRules()


@click.command()
@click.option(
    "--rule",
    type=click.Choice(
        [
            "cases",
            "articles",
            "akkusativ_prepositions",
            "dativ_prepositions",
            "pronouns",
        ]
    ),
    required=True,
    help="Choose a rule set to display.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["grid", "markdown"]),
    default="grid",
    help="Choose the output format: 'grid' (default) or 'markdown'.",
)
def display_rule(rule, output_format):
    """Display the selected German grammar rule set in a tabular format."""

    if rule == "cases":
        data = []
        for case, info in german_rules.cases.items():
            # Convert dictionary of articles nicely for Markdown
            articles = ", ".join(
                f"{gender}: {article}" for gender, article in info["articles"].items()
            )
            data.append([case, info["role"], articles, info["example"]])
        headers = ["Case", "Role", "Articles", "Example"]

    elif rule == "articles":
        data = []
        for article_type, articles in german_rules.articles.items():
            for gender, article in articles.items():
                data.append([article_type, gender, article])
        headers = ["Article Type", "Gender/Number", "Article"]

    elif rule == "akkusativ_prepositions":
        data = [
            [preposition, meaning]
            for preposition, meaning in german_rules.akkusativ_prepositions.items()
        ]
        headers = ["Preposition", "Meaning"]

    elif rule == "dativ_prepositions":
        data = [
            [preposition, meaning]
            for preposition, meaning in german_rules.dativ_prepositions.items()
        ]
        headers = ["Preposition", "Meaning"]

    elif rule == "pronouns":
        data = []
        for case, pronouns in german_rules.personal_pronouns.items():
            for pronoun, meaning in pronouns.items():
                data.append([case, pronoun, meaning])
        headers = ["Case", "Pronoun", "Meaning"]

    else:
        click.echo("Invalid rule selection.")
        return

    # Set the correct table format
    table_format = (
        "grid" if output_format == "grid" else "github"
    )  # github is better Markdown

    # Output the table using tabulate
    click.echo(tabulate(data, headers=headers, tablefmt=table_format))


if __name__ == "__main__":
    display_rule()
