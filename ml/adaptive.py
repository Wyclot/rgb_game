"""Interpretable boss policy matching the GDScript FSM; no trained-model claim."""
from dataclasses import dataclass
@dataclass
class CombatTelemetry:
 attacks:int=0
 dodges:int=0
 distance_sum:float=0
 samples:int=0
 damage_taken:float=0
 duration:float=0
 @property
 def preferred_distance(self):return self.distance_sum/max(1,self.samples)
 @property
 def attack_frequency(self):return self.attacks/max(1,self.duration)
 @property
 def dodge_frequency(self):return self.dodges/max(1,self.duration)
def strategy(stats:CombatTelemetry,current_distance:float,next_attack:int):
 if stats.dodges>stats.attacks*.65:return 'delayed_nova'
 if current_distance>230:return 'bolt_fan'
 return ('sweep','delayed_nova','bolt_fan')[next_attack%3]
