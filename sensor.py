from dataclasses import dataclass, field
import json
import sys
from typing import List, Optional, Dict, Any
from math import sin, pi
from random import randint
from messages import ParentReadyMessage, SetupMessage, DataMessage, shortMessageConsumption, fullMessageConsumption, shortMessageDuration, fullMessageDuration
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
  def __init__(self, id: str = '', energyLevel: float = 0, maxEnergyLevel: float = C * V_MAX * V_MAX / 2, layer: int = 0, index: int = 0, chargingCycles: int = 0, chargingCyclesCounter: int = 0, energyState: str = 'Initial', protocolState: str = 'Initial', parentId: Optional[str] = None, children: Optional[set] = None, scheduledMeetings: Optional[List[float]] = None, tickCount: int = 0, baseStation: bool = False, timeoutCount: int = 0, timeoutLimit: int = 3, setupReady: bool = False, childrenReady: Optional[set] = None, nextMeeting: Optional[int] = None, parentReady: bool = False, data: Optional[Dict[str, Any]] = None):
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
    self.parentScheduled = False # variavel para determinar se o nó já agendou o encontro com o pai nesse tick, a fim de evitar erros
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
    self.childrenReady = childrenReady if childrenReady is not None else set()
    self.parentReady = parentReady
    # self.timeoutFired = timeoutFired if timeoutFired is not None else set()
    self.data = data if data is not None else {}
    self.msgsReceived = 0
    self.msgsIgnored = 0
    self.resetCount = 0
    self.setupMsgsSent = 0
    self.dataMsgsSent = 0
    self.dataMsgsReceived = 0
    self.dataOriginated = 0
    self.uniqueDataReceived = 0
    self.setupMsgsReceived = 0
    self.resetTimestamps = []
    self.parentReadyTimestamps = []
    self._childOriginData = []
    self.latency_record = []

  # definições das ações realizadas nas transições da máquina de estados de protocolo e energia
    self.actions = {
      'harvestEnergy': self.harvestEnergy,
      'energyResume': self.energyResume,
      'updateTickCount': self.updateTickCount,
      'consumeEnergy': self.consumeEnergy,
      # 'energyCharging': self.energyCharging,
      'setupMessage': self.setupMessage,
      'meetChild': self.meetChild,
      'meetParent': self.meetParent,
      # 'dataListening': self.dataListening,
      'getChildData': self.getChildData,
      'reset': self.reset,
      'getParent': self.getParent,
      'waitMeeting': self.waitMeeting,
      # 'setupListening': self.setupListening,
      'sendData': self.sendData,
      'listExpectedChilds': self.listExpectedChilds,
      # 'allListening': self.allListening
      'getParentReady': self.getParentReady

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
    self.setupMsgsSent += 1
    return {'event': 'setupMessage', 'time': time+shortMessageConsumption+randint(1,25), 'message': SetupMessage(senderId=self.id, status=self.setupReady, chargingTime=self.chargingCycles, scheduledMeetings=self.scheduledMeetings, tickCount=self.tickCount, parentId=self.parentId, parentReady=self.parentReady)}

  def checkChildrenReady(self):
    # if len(self.children) == 0:
    #   # self.timeoutCount += 1
    #   if self.timeoutCount > self.timeoutLimit: self.setupReady = True
    # else:
    self.timeoutCount = 0
    self.setupReady = bool(self.childrenReady) and False not in self.childrenReady
    self.childrenReady = set()
    return self.setupReady
    
  def expectedChildsList(self):
    if self.expectedChilds and self.expectedChilds != set(): raise ValueError(f"Node {self.id} already has expected childs defined")
    self.expectedChilds = set()
    self.parentScheduled = False
    for meeting in self.scheduledMeetings:
      if meeting[1] < self.tickCount: raise ValueError(f"Node {self.id} has a scheduled meeting at tick {meeting[1]} but it's already tick {self.tickCount}")
      elif meeting[1] == self.tickCount and meeting[0] != self.parentId: self.expectedChilds.add(meeting[0]) # o encontro é nesse tick e não é um encontro com o pai
      elif meeting[1] > self.tickCount: break
    return self.expectedChilds
  
  def scheduleMeeting(self, suggestedMeetingTick: int, recurrency: int, event: dict):
    prev = None
    next = None
    for meeting in event['message'].scheduledMeetings:
      if meeting[0] == self.id:
        continue
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
    return [self.parentId, suggestedMeetingTick, recurrency]
  
  def removeMeeting(self, event: dict):
    for i in range(len(self.scheduledMeetings)):
      if self.scheduledMeetings[i][0] == event['message'].senderId:
        meeting = self.scheduledMeetings.pop(i)
        return meeting
    raise ValueError(f"Node {self.id} has no scheduled meeting with node {event['message'].senderId}")

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
    # aumentar a carga do nó com a energia disponível na janela de tempo do evento
    self.energyLevel += event['energy']
    if self.energyLevel > self.maxEnergyLevel: self.energyLevel = self.maxEnergyLevel
    return {}
  
  def energyResume(self, event: dict):
    # Identifica que um nó está plenamente carregado ao receber um tick, atualiza a contagem de ticks, zera a contagem do tempo de carga do nó e retorna um evento da retomada das atividades do nó
    self.updateTickCount(event)
    self.parentScheduled = False
    self.chargingCycles = self.chargingCyclesCounter
    self.chargingCyclesCounter  = 0
    # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} fully charged at tick {self.tickCount} and with {len(self.children)} children and timeout count {self.timeoutCount}\n')
    if len(self.children) == 0:
      # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} has no children,  timeout count {self.timeoutCount} and timeout limit {self.timeoutLimit}\n')
      if self.timeoutCount > self.timeoutLimit:
        # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} has reached timeout limit and is now setup ready\n')
        self.setupReady = True
      else: self.timeoutCount += 1
    return {'event': 'energyResume', 'time': event['time'], 'id': self.id}
  
  def updateTickCount(self, event: dict):
    # incrementar a contagem de ticks do nó enquanto o nó aguarda carga máxima ou encontros agendados
    self.tickCount += 1
    self.chargingCyclesCounter += 1
    return {}
  
  def consumeEnergy(self, event: dict):
    # diminuir a carga do nó com a energia consumida pelo evento
    self.energyLevel -= event['energy']
    return {}
  
  # def energyCharging(self, event: dict):  # deprecada
  #   return self.updateTickCount(event)
  #   raise NotImplementedError('energyCharging action not implemented yet')
  
  def setupMessage(self, event: dict):
    #  a BS conta o tick, lista os filhos esperados para esse ciclo e manda uma setupMessage
    if self.expectedChilds and self.expectedChilds != set():
      # print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} has expected childs {self.expectedChilds} at tick {self.tickCount}, resetting node')
      raise ValueError(f"Node {self.id} has expected childs {self.expectedChilds} at tick {self.tickCount}")
    self.updateTickCount(event)
    if len(self.children) > 0:
      self.expectedChildsList() # lista os filhos esperados para o tick atual
    return self.sendSetupMessage(event['time'])
  
  def meetChild(self, event: dict):
    # registrar nó filho (se novo), excluí-lo da lista de esperados e da lista de encontros agendados (se antigo), além de registrar o próximo encontro
    scheduled = False
    for meeting in self.scheduledMeetings:
      if meeting[0] == event['message'].senderId:
        scheduled = True
        break
    if event['message'].senderId in self.expectedChilds: # caso o filho seja esperado
      self.expectedChilds.remove(event['message'].senderId)
      for meeting in self.scheduledMeetings:
        if meeting[0] == event['message'].senderId:
          self.scheduledMeetings.remove(meeting)
          scheduled = False
          self.childrenReady.add(event['message'].status)
          break
      if self.expectedChilds == set():
        self.checkChildrenReady() # verificar se o nó está pronto para ir para a troca de dados
        if self.id == 'base_station' and self.setupReady:
          self.parentReadyTimestamps.append(event['time'])  # NOVO (BS se auto-declara ready)
          self.parentReady = True
    else:
      self.children.add(event['message'].senderId) # adicionar o filho à lista de filhos do nó
    if scheduled: return {}
    for scheduledMeeting in event['message'].scheduledMeetings: # agendar o próximo encontro
      if scheduledMeeting[0] == self.id:
        self.addMeeting([event['message'].senderId, scheduledMeeting[1], scheduledMeeting[2]])
    return {}

  def meetParent(self, event: dict):
    # raise NotImplementedError('meetParent action should not have been triggered')
    # remover o encontro agendado com o pai pois ele já aconteceu utilizando o índice do encontro na remoção
    # for i in range(len(self.scheduledMeetings)):
    #   if self.scheduledMeetings[i][0] == event['message'].senderId:
    #     meeting = self.scheduledMeetings.pop(i)
    #     break
    if not self.parentScheduled:
      meeting = self.removeMeeting(event)
      self.scheduleMeeting(meeting[1] + meeting[2], meeting[2], event) # agendar o próximo encontro
      self.parentScheduled = True
    if event['message'].parentReady: self.parentReady = True
    # for meeting in event['message'].scheduledMeetings: # agendar o próximo encontro
    #   if meeting[0] == self.id:
    #     # melhorar o processo de agendamento para evitar que o encontro seja marcado de forma que algum dos nós não consiga comparecer por não conseguir carregar entre dois encontros sucessivos - o filho deve se adequar aos encontros do pai
    #     self.addMeeting([event['message'].senderId, meeting[1] + meeting[2], meeting[2]])
    return self.sendSetupMessage(event['time'])
  
  def dataListening(self, event: dict): # deprecated
    raise NotImplementedError('dataListening action not implemented yet')
  
  def getChildData(self, event: dict):
    self.data[event['message'].senderId] = event['message'].data
    self.dataMsgsReceived += 1

    if not hasattr(self, '_childOriginData'):
      self._childOriginData = []
    if hasattr(event['message'], 'originDataList'):
      self._childOriginData.extend(event['message'].originDataList)
    # record latency at BS for each data origin in this message
    if self.id == 'base_station' and hasattr(event['message'], 'originDataList'):
      for origin in event['message'].originDataList:
        self.latency_record.append({
          'origin_node': origin['nodeId'],
          'acquire_tick': origin['acquireTick'],
          'origin_send_time': origin['sendTime'],
          'receive_time': event['time'],
          'receive_tick': self.tickCount,
          'latency_ms': event['time'] - origin['sendTime'],
          'latency_ticks': self.tickCount - origin['acquireTick']
        })
      self.uniqueDataReceived += len(event['message'].originDataList)
    # verificar se o filho era esperado para o encontro atual
    if event['message'].senderId in self.expectedChilds:
    # remover o encontro com o filho, pois já ocorreu
      meeting = self.removeMeeting(event)
      self.expectedChilds.remove(event['message'].senderId)
      self.addMeeting([event['message'].senderId, meeting[1] + meeting[2], meeting[2]]) # agendar o próximo encontro
    if self.expectedChilds == set():
        if self.id != 'base_station' and self.setupReady:
          return self.sendData(event)
        if self.parentReady:
          return {'event':'parentReady', 'time': event['time']+randint(1,25), 'message': ParentReadyMessage(senderId=self.id, parentReady=True)}
    return {}
  
  def sendParentReady(self, event: dict):
    self.energyLevel -= shortMessageConsumption
    return {'event':'parentReady', 'time': event['time'], 'message': ParentReadyMessage(senderId=self.id, parentReady=True)}
  
  def reset(self, event: dict):
    if event['event'] == 'tick': self.updateTickCount(event)
    self.resetTimestamps.append(event['time'])  # NOVO
    self.parentId = None
    self.children = set()
    self.scheduledMeetings = []
    self.expectedChilds = set()
    self.timeoutCount = 0
    self.setupReady = False
    self.childrenReady = set()
    self.parentScheduled = False
    self.parentReady = False  # NOVO: resetar parentReady também
    if self.id == 'base_station':
      self.resetCount += 1
      return self.sendSetupMessage(event['time'])
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
    self.scheduleMeeting(suggestedMeetingTick, recurrency, event)
    self.parentScheduled = True
    # prev = None
    # next = None
    # for meeting in event['message'].scheduledMeetings:
    #   if meeting[0] == self.id:
    #     raise ValueError(f"Node {self.id} already has a scheduled meeting with parent {self.parentId}")
    #   if meeting[1] <= suggestedMeetingTick:
    #     prev = meeting
    #   elif meeting[1] > suggestedMeetingTick and next is None:
    #     next = meeting
    #     if prev is not None and suggestedMeetingTick - prev[1] < recurrency:
    #       suggestedMeetingTick = prev[1] + recurrency
    #       next = None
    #       continue
    #     break  
    # self.addMeeting([self.parentId, suggestedMeetingTick, recurrency])
    return self.sendSetupMessage(event['time'])
  
  def waitMeeting(self, event: dict): # deprecated
    raise NotImplementedError('waitMeeting action not implemented yet')
    # waitMeeting() -> esperar pelo tick do próximo encontro
    print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} waiting for meeting at tick {self.tickCount} with meetings {self.scheduledMeetings}, self.expectedChilds {self.expectedChilds} and children {self.children}')
    self.updateTickCount(event)
    # # verificar se o nó não tem filhos para, nesse caso, incrementar a contagem de timeout
    # if len(self.children) == 0:
    #   self.timeoutCount += 1
    #   print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} has no children, incrementing timeout count to {self.timeoutCount}')
    return {}
  
  def listExpectedChilds(self, event: dict):
    if event['event'] == 'tick': self.updateTickCount(event)
    self.data = {} # resetar os dados recebidos dos filhos a cada encontro para evitar que dados antigos sejam passados adiante como se fossem do encontro atual
    self.expectedChildsList() # lista os filhos esperados para o tick atual
    return {}
  
  def setupListening(self, event: dict):
    self.expectedChildsList() # lista os filhos esperados para o tick atual
    return {}
    raise NotImplementedError('setupListening action not implemented yet')
    # atualizar a lista de filhos esperados e verificar se o nó atende aos requisitos de setupReady
    # self.updateTickCount(event)
    # definir os filhos agendados para o nó
    print('setupListening-',sys._getframe().f_lineno, self.id, self.expectedChilds, self.scheduledMeetings, self.tickCount) # 270 node_1_0 set() [['node_0_0', 8, 3]] 9
    if self.expectedChilds: raise ValueError(f"Node {self.id} already has expected childs defined")
    for meeting in self.scheduledMeetings:
      if meeting[1] == self.tickCount and meeting[0] != self.parentId: self.expectedChilds.add(meeting[0]) # o encontro é nesse tick e não é um encontro com o pai
    # verificar se o nó está pronto para ir para a troca de dados
    if len(self.expectedChilds) > 0:
      if False in self.childrenReady:
        self.setupReady = False
        self.childrenReady = set()
      else: self.setupReady = True
    elif len(self.children) == 0:
      if self.timeoutCount >= self.timeoutLimit:
        self.setupReady = True
    else: self.setupReady = False
    return {}
  
  def sendData(self, event: dict):
    self.energyLevel -= fullMessageConsumption
    self.data[self.id] = randint(1,10)
    self.dataMsgsSent += 1
    self.dataOriginated += 1

    # Build the full list of data origins: self + all children
    origin_list = [{'nodeId': self.id, 'acquireTick': self.tickCount, 'sendTime': event['time']}]
    if hasattr(self, '_childOriginData') and self._childOriginData:
      origin_list.extend(self._childOriginData)
      self._childOriginData = []

    if not self.parentScheduled:
      for i in range(len(self.scheduledMeetings)):
        if self.scheduledMeetings[i][0] == self.parentId:
          meeting = self.scheduledMeetings.pop(i)
          break
      self.addMeeting([self.parentId, meeting[1] + meeting[2], meeting[2]])
      self.parentScheduled = True
    return {'event': 'dataMessage', 'time': event['time']+fullMessageDuration+randint(1,25),
            'message': DataMessage(
              senderId=self.id, data=self.data,
              parentId=self.parentId,
              scheduledMeetings=self.scheduledMeetings,
              originDataList=origin_list)}
  
  def allListening(self, event: dict): # deprecated
    raise NotImplementedError('allListening action not implemented yet')
  
  def getParentReady(self, event: dict):
    self.parentReady = True
    self.parentReadyTimestamps.append(event['time'])  # NOVO
    return {}

  def eventHandler(self, event: dict) -> list:
    reactions = []
    if self.baseStation:
      for transition in protocolBS:  
        if transition['source_state'] == self.protocolState and (transition['event'] == event['event'] or transition['event'] is None) and (transition['guard'] is None or eval(transition['guard'])):
          # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking transition {transition} for event {event} and protocol state {self.protocolState}\n')
          # print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking transition {transition} for event {event} and protocol state {self.protocolState}')
          if transition['action'] is not None:
            reactions = addEvent(reactions, self.actions[transition['action']](event))
            # implementar lógica para atualizar as métricas de mensagens recebidas e ignoradas
            if event['event'] == 'dataMessage' or event['event'] == 'setupMessage': self.msgsReceived += 1
          self.protocolState = transition['destination_state']
          # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} transitioning from protocol state {transition["source_state"]} to protocol state {transition["destination_state"]} as satisfied guard {transition["guard"]} and did action {transition["action"]}\n')
          # print(f'[sensor-{sys._getframe().f_lineno}] - Base station transitioning from state {transition["source_state"]} to state {transition["destination_state"]}')
          break
    else:
      if self.energyState == 'Operational':
        for transition in protocolRN:
          # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking protocol transition {transition} for event {event} and protocol state {self.protocolState}\n')
          if transition['source_state'] == self.protocolState and (transition['event'] == event['event'] or transition['event'] is None) and (transition['guard'] is None or eval(transition['guard'])):
            # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking protocol transition {transition} for event {event} and protocol state {self.protocolState}\n')
            # print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking protocol transition {transition} for event {event} and protocol state {self.protocolState}')
            if transition['action'] is not None:
              reactions = addEvent(reactions, self.actions[transition['action']](event))
              # implementar lógica para atualizar as métricas de mensagens recebidas e ignoradas
              if event['event'] == 'dataMessage' or event['event'] == 'setupMessage': self.msgsReceived += 1
            self.protocolState = transition['destination_state']
            # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} transitioning from protocol state {transition["source_state"]} to protocol state {transition["destination_state"]} as satisfied guard {transition["guard"]} and did action {transition["action"]}\n')
            # print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} transitioning from protocol state {transition["source_state"]} to protocol state {transition["destination_state"]}')
            break
      else:
        # implementar lógica para atualizar as métricas de mensagens recebidas e ignoradas
        if event['event'] == 'dataMessage' or event['event'] == 'setupMessage': self.msgsIgnored += 1
      for transition in energyRN:
        if transition['source_state'] == self.energyState and (transition['event'] == event['event'] or transition['event'] is None) and (transition['guard'] is None or eval(transition['guard'])):
          # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking energy transition {transition} for event {event} and energy state {self.energyState}\n')
          # print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} Checking energy transition {transition} for event {event} and energy state {self.energyState}')
          if transition['action'] is not None: reactions = addEvent(reactions, self.actions[transition['action']](event))
          self.energyState = transition['destination_state']
          # with open('simulation_log.txt', 'a') as f: f.write(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} transitioning from protocol state {transition["source_state"]} to protocol state {transition["destination_state"]} as satisfied guard {transition["guard"]} and did action {transition["action"]}\n')
          # print(f'[sensor-{sys._getframe().f_lineno}] - Node {self.id} transitioning from energy state {transition["source_state"]} to energy state {transition["destination_state"]}')
          break
    return reactions