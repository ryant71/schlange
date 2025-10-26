#!/usr/bin/env python3
import random,sys
from library import PronounLibrary
from morphology import decline_possessive
from utils import is_correct
CASES=['nom','dat']
POS=['mein','dein','sein','ihr','unser','euer','Ihr','ihr']
def ask(p):
 try:return input(p).strip()
 except(EOFError,KeyboardInterrupt):print('\nBye');sys.exit()
def main():
 L=PronounLibrary('data/pronouns.json','data/nouns.json')
 for _ in range(5):
  p=random.choice(POS);c=random.choice(CASES);n=random.choice(L.noun_list);
  g=n['gender'];noun=n['lemma'];ans,rule=decline_possessive(p,c,g,noun);
  u=ask(f'{p} {noun} ({c},{g}) → ')
  print('✅' if is_correct(u,ans) else f'❌ {ans}',rule)
if __name__=='__main__':main()
