# german_rules.py

class GermanGrammarRules:
    def __init__(self):
        # Table 1: Cases in German
        self.cases = {
            'Nominativ': {
                'role': 'Subject (who or what is performing the action)',
                'articles': {
                    'Masculine': 'der',
                    'Feminine': 'die',
                    'Neuter': 'das',
                    'Plural': 'die'
                },
                'example': 'Der Mann liest. (The man reads.)'
            },
            'Akkusativ': {
                'role': 'Direct object (who or what is receiving the action)',
                'articles': {
                    'Masculine': 'den',
                    'Feminine': 'die',
                    'Neuter': 'das',
                    'Plural': 'die'
                },
                'example': 'Ich sehe den Hund. (I see the dog.)'
            },
            'Dativ': {
                'role': 'Indirect object (to whom/for whom something is done)',
                'articles': {
                    'Masculine': 'dem',
                    'Feminine': 'der',
                    'Neuter': 'dem',
                    'Plural': 'den'
                },
                'example': 'Ich gebe dem Kind ein Buch. (I give the child a book.)'
            },
            'Genitiv': {
                'role': 'Possession or relationship (whose)',
                'articles': {
                    'Masculine': 'des',
                    'Feminine': 'der',
                    'Neuter': 'des',
                    'Plural': 'der'
                },
                'example': 'Das Auto des Mannes. (The man’s car.)'
            }
        }

        # Table 2: Definite and Indefinite Articles
        self.articles = {
            'Definite': {
                'Masculine': 'der',
                'Feminine': 'die',
                'Neuter': 'das',
                'Plural': 'die'
            },
            'Indefinite': {
                'Masculine': 'ein',
                'Feminine': 'eine',
                'Neuter': 'ein'
            }
        }

        # Table 3: Akkusativ Prepositions
        self.akkusativ_prepositions = {
            'durch': 'through',
            'für': 'for',
            'ohne': 'without',
            'gegen': 'against',
            'um': 'around/about'
        }

        # Table 4: Dativ Prepositions
        self.dativ_prepositions = {
            'aus': 'from/out of',
            'bei': 'at/near/with',
            'mit': 'with',
            'nach': 'after/to',
            'seit': 'since/for',
            'von': 'from',
            'zu': 'to/at'
        }

        # Table 5: Word Order
        self.word_order_examples = {
            'simple_sentence': 'Ich liebe den Film. (I love the movie.)',
            'questions': 'Liebst du den Film? (Do you love the movie?)',
            'subordinate_clause': 'Ich weiß, dass du den Film liebst. (I know that you love the movie.)'
        }

        # Table 6: Verb Conjugation (Present Tense)
        self.regular_verb_conjugation = {
            'lieben': {
                'ich': 'liebe',
                'du': 'liebst',
                'er/sie/es': 'liebt',
                'wir': 'lieben',
                'ihr': 'liebt',
                'sie/Sie': 'lieben'
            }
        }

        # Table 7: Separable Verbs
        self.separable_verbs = {
            'ankommen': ('to arrive', 'Er kommt um 8 Uhr an. (He arrives at 8 o\'clock.)'),
            'aufstehen': ('to get up', 'Ich stehe früh auf. (I get up early.)'),
            'mitbringen': ('to bring with', 'Sie bringt ihren Freund mit. (She brings her friend along.)')
        }

        # Table 8: Personal Pronouns in Different Cases
        self.personal_pronouns = {
            'Nominativ': {
                'ich': 'I',
                'du': 'you',
                'er': 'he',
                'sie': 'she',
                'es': 'it',
                'wir': 'we',
                'ihr': 'you all',
                'sie': 'they',
                'Sie': 'you formal'
            },
            'Akkusativ': {
                'mich': 'me',
                'dich': 'you',
                'ihn': 'him',
                'sie': 'her',
                'es': 'it',
                'uns': 'us',
                'euch': 'you all',
                'sie': 'them',
                'Sie': 'you formal'
            },
            'Dativ': {
                'mir': 'to me',
                'dir': 'to you',
                'ihm': 'to him',
                'ihr': 'to her',
                'ihm (neuter)': 'to it',
                'uns': 'to us',
                'euch': 'to you all',
                'ihnen': 'to them',
                'Ihnen': 'to you formal'
            }
        }

        # Table 9: Modal Verbs
        self.modal_verbs = {
            'können': 'can, to be able to',
            'müssen': 'must, to have to',
            'wollen': 'to want to',
            'sollen': 'should, ought to',
            'dürfen': 'may, to be allowed to',
            'mögen': 'to like'
        }

        # Table 10: Plural Forms of Nouns
        self.plural_forms = {
            'katze': ('die Katze', 'die Katzen', 'the cat → the cats'),
            'kind': ('das Kind', 'die Kinder', 'the child → the children'),
            'blume': ('die Blume', 'die Blumen', 'the flower → the flowers'),
            'auto': ('das Auto', 'die Autos', 'the car → the cars'),
            'lehrer': ('der Lehrer', 'die Lehrer', 'the teacher → the teachers')
        }

    def get_case_info(self, case):
        """Return information about a given grammatical case."""
        return self.cases.get(case, "Case not found.")

    def get_article_info(self, type_of_article):
        """Return definite or indefinite article info."""
        return self.articles.get(type_of_article, "Article type not found.")

    def get_prepositions(self, case):
        """Return prepositions based on case."""
        if case == 'Akkusativ':
            return self.akkusativ_prepositions
        elif case == 'Dativ':
            return self.dativ_prepositions
        else:
            return "Prepositions for this case not found."

    def get_word_order_example(self, sentence_type):
        """Return word order example for a specific sentence type."""
        return self.word_order_examples.get(sentence_type, "Sentence type not found.")

    def get_verb_conjugation(self, verb):
        """Return conjugation for a given verb."""
        return self.regular_verb_conjugation.get(verb, "Verb not found.")

    def get_separable_verb(self, verb):
        """Return information about a separable verb."""
        return self.separable_verbs.get(verb, "Separable verb not found.")

    def get_personal_pronouns(self, case):
        """Return personal pronouns for a given case."""
        return self.personal_pronouns.get(case, "Case not found.")

    def get_modal_verb(self, verb):
        """Return information about a modal verb."""
        return self.modal_verbs.get(verb, "Modal verb not found.")

    def get_plural_form(self, singular_noun):
        """Return the plural form of a noun."""
        return self.plural_forms.get(singular_noun, "Noun not found.")
