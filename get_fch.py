#!/usr/bin/env python3

import pandas as pd
import sys

if len(sys.argv) < 2:                                                          
    print("Usage: python get_fch.py <Trader dataframe file>")       
    sys.exit()                                                                 
                                                                                
traderdf_file = sys.argv[1]                                                        
                                                                                
# Read in the trading data frame
df = pd.read_pickle(f'{traderdf_file}')                                  
df = df.reset_index().rename({'index' : 'timestamp'}, axis=1)
event = df.loc[df['EventType']=='FINAL_HOLDINGS']
s = event.Event.values[0]

# Convert the final holdings into a dict
s=s.replace(':','')
s=s.replace(',','')
s=s[s.find("{")+1:s.find("}")].strip().split()
b = dict(zip(s[::2], s[1::2]))
b = dict(zip(b.keys(), [int(v) for v in b.values()]))

# Show the final holdings
CASH = b['CASH']
print(f"FINAL CASH HOLDINGS: {CASH}")
JPM = 0
if 'JPM' in b:
    JPM = b['JPM'] 
print(f"REMAINING SHARES OF JPM (SHOULD BE 0): {JPM}")
