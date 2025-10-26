ENDINGS={('nom','m'):'',('nom','f'):'e',('nom','n'):'',('nom','pl'):'e',('dat','m'):'em',('dat','f'):'er',('dat','n'):'em',('dat','pl'):'en'}
def stem(p):return 'eur' if p=='euer' else p
def decline_possessive(p,case,g,noun):
 e=ENDINGS.get((case,g),'');det=stem(p)+e;rule=f'ein-word ending for {case}+{g} is -{e or "∅"}'
 return f'{det} {noun}',rule
