import json, os, random, re
UMLAUT_MAP={'ä':'ae','ö':'oe','ü':'ue','ß':'ss'}
def alt_forms(s):
 s=s.strip();forms={s,s.lower()}
 for f in list(forms):
  for k,v in UMLAUT_MAP.items(): forms|={f.replace(k,v),f.replace(v,k)}
 return [re.sub(r'\s+',' ',x).strip() for x in forms]
def is_correct(u,a):return bool(set(alt_forms(u))&set(alt_forms(a)))
