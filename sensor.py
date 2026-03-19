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
  if event is None or event == {}: return eventList
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
  def __init__(self, id: str = '', energyLevel: float = 0, maxEnergyLevel: float = C * V_MAX * V_MAX / 2, layer: int = 0, index: int = 0, chargingCycles: int = 0, chargingCyclesCounter: int = 0, energyState: str = 'Initial', protocolState: str = 'Initial', parentId: Optional[str] = None, children: Optional[set] = None, scheduledMeetings: Optional[List[float]] = None, tickCount: int = 0, baseStation: bool = False, timeoutCount: int = 0, timeoutLimit: int = 3, setupReady: bool = False, childrenSetupReady: Optional[set] = None, nextMeeting: Optional[int] = None):
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
    # self.newChildren = set() # set de nos que compareceram ao encontro de forma não agendada
    self.tickCount = tickCount
    # self.activeTick = activeTick
    self.baseStation = baseStation
    self.timeoutCount = timeoutCount
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


  # métodos dos nós

  def addMeeting(self, meeting: List[float]):
    i = 0
    while i < len(self.scheduledMeetings) and self.scheduledMeetings[i][1] <= meeting[1]:
      i += 1
    self.scheduledMeetings.insert(i, meeting)
    return self.scheduledMeetings

  def sendSetupMessage(self, time: int):
    self.energyLevel -= shortMessageConsumption
    return {'event': 'setupMessage', 'time': self.tickCount, 'message': SetupMessage(senderId=self.id, status=self.setupReady, chargingTime=self.chargingCycles, scheduledMeetings=self.scheduledMeetings, tickCount=self.tickCount, sendtime= time+randint(1,25), parentId=self.parentId)}

  # ações de tratamentos dos eventos

# Objetivo das funções:
# - updateTickCount -> incrementar o tickCount
# - harvestEnergy -> aumentar a carga do nó com a energia disponível na janela de tempo do evento
# - consumeEnergy -> diminuir a carga do nó com a energia consumida pelo evento
# - getParent -> registrar nó pai, marcar o próximo encontro e mandar a sua própria setupMessage
# - meetChild -> registrar nó filho (se novo), excluí-lo da lista de esperados e da lista de encontros agendados (se antigo), além de registrar o próximo encontro
# - meet Parent - excuir o encontro atual da lista de agendados e adicionar o próximo, além de mandar sua própria setupMessage
# - reset() - Resetar encontros, pais e filhos
# waitMeeting() -> esperar pelo tick do próximo encontro
# setupListening () -> atualizar a lista de filhos esperados e verificar se o nó atende aos requisitos de setupReady
# getChildData -> receber e registrar o dado do filho para passar adiante posteriormente
# sendData () -> enviar a mensagem com os próprios dados, e os dos filhos, agendar e esperar o próximo encontro
# dataListening -> identifica o momento de ativar a antena e, no caso dos nós folha, enviar a dataMessage para seus pais


  def harvestEnergy(self, event: dict):
    self.energyLevel += event['energy']
    if self.energyLevel > self.maxEnergyLevel: self.energyLevel = self.maxEnergyLevel
    return {}
  
  def energyResume(self, event: dict):
    # atualiza a contagem de ticks, zera a contagem do tempo de carga do nó e retorna um evento da retomada das atividades do nó
    self.updateTickCount(event)
    self.chargingCycles = self.chargingCyclesCounter
    self.chargingCyclesCounter  = 0
    return {'event': 'energyResume', 'time': event['time'], 'nodeId': self.id}
  
  def updateTickCount(self, event: dict):
    # incrementar a contagem de ticks do nó
    self.tickCount += 1
    self.chargingCyclesCounter += 1
    return {}
  
  def consumeEnergy(self, event: dict):
    # diminuir a carga do nó com a energia consumida pelo evento
    self.energyLevel -= event['energy']
    return {}
  
  def energyCharging(self, event: dict):
    # deprecated
    return self.updateTickCount(event)
    raise NotImplementedError('energyCharging action not implemented yet')
  
  def setupMessage(self, event: dict):
    #  a BS conta o tick, lista os filhos esperados para esse ciclo e manda uma setupMessage
    if self.expectedChilds and self.expectedChilds != set():
      print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} has expected childs {self.expectedChilds} at tick {self.tickCount}, resetting node')
      self.reset(event) 
    else:
      self.updateTickCount(event)
      for meeting in self.scheduledMeetings:
        if meeting[1] == self.tickCount: self.expectedChilds.add(meeting[0]) # o encontro é nesse tick e o filho é esperado
    return self.sendSetupMessage(event['time'])
  
  def meetChild(self, event: dict):
    # registrar nó filho (se novo), excluí-lo da lista de esperados e da lista de encontros agendados (se antigo), além de registrar o próximo encontro
    # caso o filho seja esperado
    print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} with meetings {self.scheduledMeetings}, expecting {self.expectedChilds} meeting child {event["message"]} at tick {self.tickCount}')
    if event['message'].senderId in self.expectedChilds:
      raise NotImplementedError('meetChild action for expected child not implemented yet')
    else:
      self.children.add(event['message'].senderId) # adicionar o filho à lista de filhos do nó
    for scheduledMeeting in event['message'].scheduledMeetings: # agendar o próximo encontro
      if scheduledMeeting[0] == self.id:
        self.addMeeting([event['message'].senderId, scheduledMeeting[1], scheduledMeeting[2]])
    # if event['message'].senderId in self.expectedChilds:
    #   self.expectedChilds.remove(event['message'].senderId)
    #   for meeting in self.scheduledMeetings:
    #     if meeting[0] == event['message'].senderId:
    #       expectedMeeting = meeting
    #       self.scheduledMeetings.remove(meeting)
    #       self.childrenSetupReady.add(event['message'].status)
    #       break
    #   # melhorar o processo de agendamento para evitar que o encontro seja marcado de forma que algum dos nós não consiga comparecer por não conseguir carregar entre dois encontros sucessivos - o filho deve se adequar aos encontros do pai
    #   self.addMeeting([event['message'].senderId, expectedMeeting[1]+expectedMeeting[2], expectedMeeting[2]])
    # # caso o filho não seja esperado
    # else:
    #   # verificar se é o primeiro filho
    #   if len(self.children) == 0:       
    #     self.timeoutCount = 0 # resetar a contagem de timeout
    #   else:
    #     self.children.add(event['message'].senderId) # adicionar o filho à lista de filhos do nó
    #   # print(sys._getframe().f_lineno, self.scheduledMeetings, event['message'])
    #   for meeting in event['message'].scheduledMeetings: # agendar o próximo encontro
    #     if meeting[0] == self.id:
    #       # melhorar o processo de agendamento para evitar que o encontro seja marcado de forma que algum dos nós não consiga comparecer por não conseguir carregar entre dois encontros sucessivos - o filho deve se adequar aos encontros do pai
    #       self.addMeeting([event['message'].senderId, meeting[1] + meeting[2], meeting[2]])
    #   self.childrenSetupReady.add(event['message'].status) 
    return {}

  def meetParent(self, event: dict):
    for meeting in self.scheduledMeetings: # remover o encontro agendado com pai visto que ele já aconteceu
      if meeting[0] == event['message'].senderId:
        self.scheduledMeetings.remove(meeting)
        break
    for meeting in event['message'].scheduledMeetings: # agendar o próximo encontro
      if meeting[0] == self.id:
        # melhorar o processo de agendamento para evitar que o encontro seja marcado de forma que algum dos nós não consiga comparecer por não conseguir carregar entre dois encontros sucessivos - o filho deve se adequar aos encontros do pai
        self.addMeeting([event['message'].senderId, meeting[1] + meeting[2], meeting[2]])
    return self.sendSetupMessage(event['time'])
  
  def dataListening(self, event: dict):
    raise NotImplementedError('dataListening action not implemented yet')
  
  def getChildData(self, event: dict):
    raise NotImplementedError('getChildData action not implemented yet')
  
  def reset(self, event: dict):
    if event['event'] == 'tick': self.updateTickCount(event)
    self.parentId = None
    self.children = set()
    self.scheduledMeetings = []
    self.expectedChilds = set()
    self.timeoutCount = 0
    self.setupReady = False
    self.childrenSetupReady = set()
    return {}
  
  def getParent(self, event: dict):
    # registrar pai e mandar setupMessage
    self.parentId = event['message'].senderId
    #print(event) # 'message': SetupMessage(senderId='base_station', senderIdLayer=-1, status='setup', chargingTime=0, scheduledMeetings=[], received=set(), ignored=set(), tickCount=1, sendtime=0, parentId='root')
    # melhorar o processo de agendamento para evitar que o encontro seja marcado de forma que algum dos nós não consiga comparecer por não conseguir carregar entre dois encontros sucessivos - o filho deve se adequar aos encontros do pai
    if self.scheduledMeetings: raise ValueError(f"Node {self.id} already has scheduled meetings defined")
    recurrency = 1 + max(self.chargingCycles, event['message'].chargingTime)
    suggestedMeetingTick = event['message'].tickCount + recurrency
    # verificar se o encontro sugerido é viável para o pai, pois ele tem que conseguir carregar no intervalo de tempo entre o encontro sugerido e o anterior e o sucessor já agendados para o pai - o filho que se adequa ao calendário do pai
    prev = None
    next = None
    for meeting in event['message'].scheduledMeetings:
      if meeting[0] == self.id:
        raise ValueError(f"Node {self.id} already has a scheduled meeting with parent {self.parentId}")
      if meeting[1] <= suggestedMeetingTick:
        prev = meeting
      elif meeting[1] > suggestedMeetingTick and next is None:
        next = meeting
        if prev is not None and suggestedMeetingTick - prev[1] < recurrency:
          suggestedMeetingTick = prev[1] + recurrency
          next = None
          continue
        break  
    self.addMeeting([self.parentId, suggestedMeetingTick, recurrency])
    return self.sendSetupMessage(event['time'])
  
  def waitMeeting(self, event: dict):
    # waitMeeting() -> esperar pelo tick do próximo encontro
    print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} waiting for meeting at tick {self.tickCount} with meetings {self.scheduledMeetings}, self.expectedChilds {self.expectedChilds} and children {self.children}')
    self.updateTickCount(event)
    # # verificar se o nó não tem filhos para, nesse caso, incrementar a contagem de timeout
    # if len(self.children) == 0:
    #   self.timeoutCount += 1
    #   print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} has no children, incrementing timeout count to {self.timeoutCount}')
    return {}
  
  def setupListening(self, event: dict):
    # atualizar a lista de filhos esperados e verificar se o nó atende aos requisitos de setupReady
    self.updateTickCount(event)
    # definir os filhos agendados para o nó
    print('setupListening-',sys._getframe().f_lineno, self.id, self.expectedChilds, self.scheduledMeetings, self.tickCount) # 270 node_1_0 set() [['node_0_0', 8, 3]] 9
    if self.expectedChilds: raise ValueError(f"Node {self.id} already has expected childs defined")
    for meeting in self.scheduledMeetings:
      if meeting[1] == self.tickCount and meeting[0] != self.parentId: self.expectedChilds.add(meeting[0]) # o encontro é nesse tick e não é um encontro com o pai
    # verificar se o nó está pronto para ir para a troca de dados
    if len(self.expectedChilds) > 0:
      if False in self.childrenSetupReady:
        self.setupReady = False
        self.childrenSetupReady = set()
      else: self.setupReady = True
    elif len(self.children) == 0:
      if self.timeoutCount >= self.timeoutLimit:
        self.setupReady = True
    else: self.setupReady = False
    return {}
  
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
