import os,sys,argparse
def main():
 p=argparse.ArgumentParser();p.add_argument('--sentence',required=True);a=p.parse_args()
 from openai import OpenAI
 key=os.getenv('OPENAI_API_KEY') or sys.exit('Need OPENAI_API_KEY')
 c=OpenAI(api_key=key)
 r=c.chat.completions.create(model='gpt-4o-mini',messages=[{'role':'user','content':a.sentence}])
 print(r.choices[0].message.content)
if __name__=='__main__':main()
