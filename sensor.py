from dataclasses import dataclass, field
import json
import sys
from typing import List, Optional, Dict, Any
from math import sin, pi
from random import randint
from messages import SetupMessage, shortMessageConsumption, fullMessageConsumption, addMessage
from random import random

# leitura das máquinas de estados nos arquivos json e salvamento em dicionários para uso na simulação
# atributos das transições: source_state, event, guard, action, destination_state
with open('fsm_jsons/energy_rn.json') as f: energyRN = json.load(f)
with open('fsm_jsons/protocol_rn.json') as f: protocolRN = json.load(f)
with open('fsm_jsons/protocol_bs.json') as f: protocolBS = json.load(f)

def addEvent(eventList : List[dict], event: dict):
  if eventList is None: return [event]
  if event is None: return eventList
  i = 0
  while i < len(eventList) and eventList[i]['time'] <= event['time']:
    i += 1
  eventList.insert(i, event)
  return eventList

def mergeEvents(eventList1: List[dict], eventList2: List[dict]):
  mergedList = []
  i = j = 0
  while i < len(eventList1) and j < len(eventList2):
    if eventList1[i] == {}:
      i += 1
      continue
    elif eventList2[j] == {}:
      j += 1
      continue
    if eventList1[i]['time'] <= eventList2[j]['time']:
      mergedList.append(eventList1[i])
      i += 1
    else:
      mergedList.append(eventList2[j])
      j += 1
  while i < len(eventList1):
    mergedList.append(eventList1[i])
    i += 1
  while j < len(eventList2):
    mergedList.append(eventList2[j])
    j += 1
  return mergedList

# energia = c*v*v/2 (J)
# W = J/s

C = 100e-6  # capacitancia em farads
V_MAX = 5  # voltagem máxima em volts

@dataclass
class Sensor:
  def __init__(self, id: str = '', energyLevel: float = 0, maxEnergyLevel: float = C * V_MAX * V_MAX / 2, layer: int = 0, index: int = 0, chargingCycles: int = 0, chargingCyclesCounter: int = 0, energyState: str = 'Initial', protocolState: str = 'Initial', parentId: Optional[str] = None, children: Optional[set] = None, scheduledMeetings: Optional[List[float]] = None, tickCount: int = 0, baseStation: bool = False, timeoutCount: dict = None, timeoutLimit: int = 3, setupReady: bool = False, childrenSetupReady: Optional[set] = None):
    self.id = id
    self.energyLevel = energyLevel
    self.maxEnergyLevel = maxEnergyLevel
    # self.layer = layer
    # self.index = index
    self.chargingCycles = chargingCycles
    self.chargingCyclesCounter = chargingCyclesCounter
    self.energyState = energyState # Initial / Charging / Operational
    self.protocolState = protocolState # Initial / Setup Listening / Orphan / Wait Meeting Setup / Data Listening / Wait Meeting Data
    self.parentId = parentId
    self.children = children if children is not None else set()
    self.scheduledMeetings = scheduledMeetings if scheduledMeetings is not None else [] # lista de listas com os encontros agendados: [id do par, proximo encontro, periodicidade]
    self.expectedChilds = set() # set de nos que devem comparecer ao encontro agendado
    self.newChildren = set() # set de nos que compareceram ao encontro de forma não agendada
    self.tickCount = tickCount
    # self.activeTick = activeTick
    self.baseStation = baseStation
    self.timeoutCount = timeoutCount if timeoutCount is not None else dict()
    self.timeoutLimit = timeoutLimit
    self.setupReady = setupReady
    self.childrenSetupReady = childrenSetupReady if childrenSetupReady is not None else set()
    # self.timeoutFired = timeoutFired if timeoutFired is not None else set()

  # definições das ações realizadas nas transições da máquina de estados de protocolo e energia
    self.actions = {
      'harvestEnergy': self.harvestEnergy,
      'energyResume': self.energyResume,
      'updateTickCount': self.updateTickCount,
      'consumeEnergy': self.consumeEnergy,
      'energyCharging': self.energyCharging,
      'setupMessage': self.setupMessage,
      'meetChild': self.meetChild,
      'meetParent': self.meetParent,
      'dataListening': self.dataListening,
      'getChildData': self.getChildData,
      'reset': self.reset,
      'getParent': self.getParent,
      'waitMeeting': self.waitMeeting,
      'setupListening': self.setupListening,
      'sendData': self.sendData
    }

  def harvestEnergy(self, event: dict):
    self.energyLevel += event['energy']
    if self.energyLevel > self.maxEnergyLevel: self.energyLevel = self.maxEnergyLevel
    return {}
  
  def energyResume(self, event: dict):
    # atualiza a contagem de ticks e retorna um evento da retomada das atividades do nó
    self.updateTickCount(event)
    self.chargingCycles = self.chargingCyclesCounter
    self.chargingCyclesCounter  = 0
    return {'event': 'energyResume', 'time': event['time']}
  
  def updateTickCount(self, event: dict):
    self.tickCount += 1
    self.chargingCyclesCounter += 1
    return {}
  
  def consumeEnergy(self, event: dict):
    self.energyLevel -= event['energy']
    return {}
  
  def energyCharging(self, event: dict):
    raise NotImplementedError('energyCharging action not implemented yet')
  
  def setupMessage(self, event: dict):
    # print(event) # {'event': 'tick', 'time': 1000}
    self.updateTickCount(event)
    return {'event': 'setupMessage', 'time': event['time']+randint(1,25), 'message': SetupMessage(senderId=self.id, status='setup', chargingTime=self.chargingCycles, scheduledMeetings=self.scheduledMeetings, tickCount=self.tickCount, parentId=self.parentId)}
  
  def meetChild(self, event: dict):
    print(self.id, event)
    raise NotImplementedError('meetChild action not implemented yet')
  
  def meetParent(self, event: dict):
    raise NotImplementedError('meetParent action not implemented yet')
  
  def dataListening(self, event: dict):
    raise NotImplementedError('dataListening action not implemented yet')
  
  def getChildData(self, event: dict):
    raise NotImplementedError('getChildData action not implemented yet')
  
  def reset(self, event: dict):
    raise NotImplementedError('reset action not implemented yet')
  
  def getParent(self, event: dict):
    # registrar pai e mandar setupMessage
    self.parentId = event['message'].senderId
    #print(event) # 'message': SetupMessage(senderId='base_station', senderIdLayer=-1, status='setup', chargingTime=0, scheduledMeetings=[], received=set(), ignored=set(), tickCount=1, sendtime=0, parentId='root')
    recurrency = 1 + max(self.chargingCycles, event['message'].chargingTime)
    newMeeting = [self.parentId, event['message'].tickCount + recurrency, recurrency]
    i = 0
    while i < len(self.scheduledMeetings) and self.scheduledMeetings[i][1] <= newMeeting[1]:
      i += 1
    self.scheduledMeetings.insert(i, newMeeting)
    self.energyLevel -= 2*shortMessageConsumption
    return {'event': 'setupMessage', 'time': event['time']+randint(1,25), 'message': SetupMessage(senderId=self.id, status='setup', chargingTime=self.chargingCycles, scheduledMeetings=self.scheduledMeetings, tickCount=self.tickCount, parentId=self.parentId)}
  
  def waitMeeting(self, event: dict):
    raise NotImplementedError('waitMeeting action not implemented yet')
  
  def setupListening(self, event: dict):
    raise NotImplementedError('setupListening action not implemented yet')
  
  def sendData(self, event: dict):
    raise NotImplementedError('sendData action not implemented yet')
  
  def eventHandler(self, event: dict) -> list:
    reactions = []
    if self.baseStation:
      for transition in protocolBS:  
        if transition['source_state'] == self.protocolState and (transition['event'] == event['event'] or transition['event'] is None) and (transition['guard'] is None or eval(transition['guard'])):
          print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking transition {transition} for event {event} and protocol state {self.protocolState}')
          if transition['action'] is not None: reactions = addEvent(reactions, self.actions[transition['action']](event))
          self.protocolState = transition['destination_state']
          print(f'[sensor-{sys._getframe().f_lineno}] - Base station transitioning from state {transition["source_state"]} to state {transition["destination_state"]}')
          break
    else:
      for transition in energyRN:
        if transition['source_state'] == self.energyState and (transition['event'] == event['event'] or transition['event'] is None) and (transition['guard'] is None or eval(transition['guard'])):
          print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking energy transition {transition} for event {event} and energy state {self.energyState}')
          if transition['action'] is not None: reactions = addEvent(reactions, self.actions[transition['action']](event))
          self.energyState = transition['destination_state']
          print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} transitioning from energy state {transition["source_state"]} to energy state {transition["destination_state"]}')
          break
      if self.energyState != 'Operational': return reactions
      for transition in protocolRN:
        if transition['source_state'] == self.protocolState and (transition['event'] == event['event'] or transition['event'] is None) and (transition['guard'] is None or eval(transition['guard'])):
          print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking protocol transition {transition} for event {event} and protocol state {self.protocolState}')
          if transition['action'] is not None: reactions = addEvent(reactions, self.actions[transition['action']](event))
          self.protocolState = transition['destination_state']
          print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} transitioning from protocol state {transition["source_state"]} to protocol state {transition["destination_state"]}')
          break
    return reactions
