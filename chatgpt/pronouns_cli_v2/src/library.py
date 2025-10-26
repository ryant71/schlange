import json
class PronounLibrary:
 def __init__(self,pjson,njson):
  self.pronouns=json.load(open(pjson));self.nouns=json.load(open(njson))
  self.items=self.pronouns['items'];self.by_id={i['id']:i for i in self.items}
  self.noun_list=self.nouns['nouns']
