extends Node
var game
var callback
var elapsed=0.0
func _ready():
 callback=JavaScriptBridge.create_callback(command)
 JavaScriptBridge.get_interface("window").runeforgeAction=callback
func command(args):
 var action=str(args[0])
 var value=args[1] if args.size()>1 else ""
 match action:
  "start":game.start(false)
  "continue":game.start(true)
  "save":game.save_game()
  "inventory":game.overlay="inventory"
  "items":game.overlay="rgb"
  "close":game.overlay=""
  "trial":game.overlay="trial";game.net.begin_trial()
  "attack","guard","rest":game.net.trial_action(action)
  "equip":game.net.equip_item(int(value))
  "transfer":game.net.transfer_item(int(value),game.net.profiles.B.id)
  "profile":game.net.switch_profile(str(value))
func _process(delta):
 elapsed+=delta
 if elapsed<0.1:return
 elapsed=0
 var n=game.net
 var snapshot={"state":game.state,"overlay":game.overlay,"hero":[game.hero.x,game.hero.y],"health":game.health,"stamina":game.stamina,"damage":game.weapon_damage(),"inventory":game.inventory,"quest":game.quest,"busy":n.busy,"online":n.online,"profile":n.profile,"slot":n.profile_slot,"items":n.items,"history":n.history,"trial":n.trial,"message":n.message,"service":n.service,"equipment":n.equipment}
 JavaScriptBridge.eval("window.runeforgeState="+JSON.stringify(snapshot),true)
