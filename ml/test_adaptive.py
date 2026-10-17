from ml.adaptive import CombatTelemetry,strategy
def test_policy():
 assert strategy(CombatTelemetry(attacks=10,dodges=8),100,0)=='delayed_nova'
 assert strategy(CombatTelemetry(attacks=10,dodges=1),300,0)=='bolt_fan'
 assert strategy(CombatTelemetry(attacks=10,dodges=1),100,0)=='sweep'
def test_telemetry():
 s=CombatTelemetry(attacks=10,dodges=3,distance_sum=1000,samples=5,damage_taken=15,duration=10)
 assert s.attack_frequency==1 and s.preferred_distance==200 and s.dodge_frequency==.3
