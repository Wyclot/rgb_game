"""Deterministic, server-owned tactical trial. Inputs are intentions, never hit/loot claims."""
INTENTS=('sweep','heavy','recover','bolt','heavy','recover')
def initial():
 return dict(hp=100,enemy_hp=180,stamina=100,turn=0,intent=INTENTS[0],status='active',log='The Guardian raises its blade.')
def advance(state,action):
 s=dict(state)
 if s['status']!='active':raise ValueError('Trial is finished')
 cost={'attack':24,'guard':10,'rest':0}[action]
 if s['stamina']<cost:raise ValueError('Not enough stamina; rest to recover')
 s['stamina']-=cost
 intent=s['intent']
 if action=='attack':s['enemy_hp']=max(0,s['enemy_hp']-(38 if intent=='recover' else 26))
 incoming={'sweep':16,'heavy':34,'recover':0,'bolt':18}[intent]
 if action=='guard':incoming=0 if intent=='heavy' else incoming//4
 if action=='rest':s['stamina']=min(100,s['stamina']+38)
 s['stamina']=min(100,s['stamina']+8)
 if s['enemy_hp']>0:s['hp']=max(0,s['hp']-incoming)
 s['turn']+=1
 s['intent']=INTENTS[s['turn']%len(INTENTS)]
 if s['enemy_hp']==0:s['status']='won'
 elif s['hp']==0 or s['turn']>=60:s['status']='lost'
 s['log']=f"{action.capitalize()}: {incoming if s['enemy_hp'] else 0} damage received. " + ('Victory verified by the server.' if s['status']=='won' else f"Next attack: {s['intent']}.")
 return s
