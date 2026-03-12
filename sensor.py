from dataclasses import dataclass, field
import sys
from typing import List, Optional, Dict, Any
from math import sin, pi
from random import randint
from messages import SetupMessage, shortMessageConsumption, fullMessageConsumption, addMessage
from random import random

# energia = c*v*v/2 (J)
# W = J/s

def energyHarvested(simulation_time: float, variation: int = 7) -> float:
  """
  Calculate the total energy harvested over a given simulation time.

  Parameters:
  simulation_time (float): The total time of the simulation in seconds.
  variation (int): The percentage variation in harvested energy.

  Returns:
  float: The energy harvested in watts.
  """

  max_power = 0.4  # Maximum power in watts
  frequency = 1/(24*60*60)
  phi = 3*pi/2
  minimum_power = 1e-6 # Minimum power in watts
  harvestedPower = max_power * sin(2 * pi * frequency * simulation_time + phi)
  if harvestedPower < minimum_power:
      harvestedPower = minimum_power
  return harvestedPower * (1 + randint(-variation, variation) / 100)

C = 100e-6  # capacitancia em farads
V_MAX = 5  # voltagem máxima em volts

@dataclass
class Sensor:
    def __init__(self, id: str = '', energyLevel: float = 0, maxEnergyLevel: float = C * V_MAX * V_MAX / 2, layer: int = 0, index: int = 0, chargingCycles: int = 0, chargingCyclesCounter: int = 0, modeState: str = 'setup', energyState: str = 'energyDischarged', protocolState: str = 'setupParentListening', parentId: Optional[str] = None, children: Optional[set] = None, scheduledMeetings: Optional[List[float]] = None, tickCount: int = 0, charged: bool = False, activeTick: bool = False, baseStation: bool = False, timeoutCount: dict = None, timeoutLimit: int = 3, timeoutFired: set = None):
      self.id = id
      self.energyLevel = energyLevel
      self.maxEnergyLevel = maxEnergyLevel
      self.layer = layer
      self.index = index
      self.chargingCycles = chargingCycles
      self.chargingCyclesCounter = chargingCyclesCounter
      self.modeState = modeState # setup / data
      self.energyState = energyState # energyDischarged / energyIdle / energyActive / energyReset / energyOprhan
      self.protocolState = protocolState # setupParentListening / setupChildBroadcasting / setupReady / setupReset / setupChildListening / setupNewChild / setupSetup / setupData / dataParentListening / dataMessageChild / dataChildListening / dataReady / dataReset / dataDone
      self.parentId = parentId
      self.children = children if children is not None else set()
      self.scheduledMeetings = scheduledMeetings if scheduledMeetings is not None else [] # lista de listas com os encontros agendados: [id do par, proximo encontro, periodicidade]
      self.expectedMessage = set() # set de nos que devem comparecer ao encontro agendado
      self.attendedMessage = set() # set de nos que compareceram ao encontro agendado
      self.tickCount = tickCount
      self.charged = charged  
      self.activeTick = activeTick
      self.baseStation = baseStation
      self.timeoutCount = timeoutCount if timeoutCount is not None else dict()
      self.timeoutLimit = timeoutLimit
      self.timeoutFired = timeoutFired if timeoutFired is not None else set()
      self.status = {
        'energyDischarged': self.energyDischarged,
        'energyIdle': self.energyIdle,
        'energyActive': self.energyActive,
        'energyReset': self.energyReset,
        'energyOprhan': self.energyOprhan,
        'setupParentListening': self.setupParentListening,
        'setupChildBroadcasting': self.setupChildBroadcasting,
        'setupReady': self.setupReady,
        'setupReset': self.setupReset,
        'setupChildListening': self.setupChildListening,
        'setupNewChild': self.setupNewChild,
        'setupSetup': self.setupSetup,
        'setupData': self.setupData,
        'dataParentListening': self.dataParentListening,
        'dataMessageChild': self.dataMessageChild,
        'dataChildListening': self.dataChildListening,
        'dataReady': self.dataReady,
        'dataReset': self.dataReset,
        'dataDone': self.dataDone
      }

    def stateRun(self, operator: str, step: int, tick: bool, messagesSent: List):
      if operator in self.status:
        self.status[operator](step, tick, messagesSent)
      else:
        raise ValueError(f'Invalid operator: {operator}')
      
    def fullCharged(self) -> bool:
      # verifica se o nó está com a carga completa
      return self.energyLevel >= self.maxEnergyLevel

    def resetMeetingControl(self):
      # função para resetar o controle de encontros agendados
      self.expectedMessage = set()
      self.attendedMessage = set()

    def energyDischarged(self, step: int, tick: bool, messagesSent: List):
      # acumular energia até atingir o nível máximo -> o nó passa a estar carregado
      if self.fullCharged() and not self.charged and not self.activeTick:
        self.energyLevel = self.maxEnergyLevel
        self.charged = True
        with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} fully charged at tick {self.tickCount}\n')

      # se o nó recebe um tick, ele deve verificar se tem energia suficiente para executar o protocolo e, caso tenha, passar para o estado de idle, scheduled ou oprhan dependendo se tem encontros agendados ou não. Caso tenha encontros mas não tenha energia suficiente, passar para o estado de reset
      if tick:
        self.tickCount += 1
        if self.charged:
          if self.parentId:
            if self.scheduledMeetings and self.scheduledMeetings[0][1] == self.tickCount:
                self.modeState = 'energyActive'
                self.activeTick = True
                with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} went to energyActive state due to meeting with {self.scheduledMeetings[0][0]} at tick {self.tickCount}\n')
            else:
              self.modeState = 'energyIdle'
              with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} went to energyIdle state at tick {self.tickCount} due to meeting with {self.scheduledMeetings[0][0]} at tick{self.scheduledMeetings[0][1]} \n')
          else:
            self.modeState = 'energyOprhan'
            with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} went to energyOprhan state at tick {self.tickCount}\n')
        else:
          if self.scheduledMeetings and self.scheduledMeetings[0][1] == self.tickCount:
            self.modeState = 'energyReset'
            with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} went to energyReset state due to missing meeting with {self.scheduledMeetings[0][0]} at tick {self.tickCount}\n') 
      
    def energyIdle(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de idle
      raise NotImplementedError('Implementar código para estado unscheduled')

    def energyActive(self, step: int, tick: bool, messagesSent: List):
      # executar o protocolo de comunicação de acordo com o estado do protocolo (setup ou data)
      print(f'Node {self.id} is active with protocol state {self.protocolState} at tick {self.tickCount}')
      newMessages = self.stateRun(self.protocolState, step, tick, messagesSent)
      # verifica se o nó está ativo ao receber um tick para desativá-lo para recarga no próximo ciclo
      if tick:
        self.tickCount += 1
        if self.activeTick and not self.baseStation:
          self.activeTick = False
          with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} deactivated at tick {self.tickCount}\n')
          self.energyState = 'energyDischarged'
      return newMessages

    def energyReset(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de reset
      raise NotImplementedError('Implementar código para estado reset')

    def energyOprhan(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de oprhan
      raise NotImplementedError('Implementar código para estado oprhan')

    def setupParentListening(self, step: int, tick: bool, messagesSent: List):
      # objetivo do estado: esperar pelo broadcast do pai para se registrar como filho e agendar encontros
      # resultados possíveis: se o pai enviar a mensagem, ir para o estado setupChildBroadcasting, caso o pai não envie a mensagem até a chegada do tick, ir para setupReset 
      
      # verificar se o nó configurou o pai como esperado para o encontro agendado, caso contrário, configurar o pai como esperado
      if not self.expectedMessage: self.expectedMessage.add(self.parentId)

      # caso o nó seja a base station, ele não precisa de mensagem do pai por ser o nó raiz
      if self.baseStation:
        self.protocolState = 'setupChildBroadcasting'
        with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} is the base station and is starting setupChildBroadcasting at tick {self.tickCount}\n')
        print(f'Node {self.id} is the base station and is starting setupChildBroadcasting at tick {self.tickCount}')
        self.resetMeetingControl()
        return []

      # verificar se o pai enviou uma mensagem de broadcast - se sim, passar para o estado de setupChildBroadcasting
      for message in messagesSent:
        if message['senderIdLayer'] == self.layer-1 and message['status'] == 'setup' and message['senderId'] == self.parentId:
          self.protocolState = 'setupChildBroadcasting'
          with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} received setup message from parent {self.parentId} at tick {self.tickCount}\n')
          print(f'Node {self.id} received setup message from parent {self.parentId} at tick {self.tickCount}')
          self.resetMeetingControl()
          return []

      # verificar se o nó recebeu um tick - se sim, passar para o estado de setupReset
      if tick:
        self.protocolState = 'setupReset'
        with open('simulation.log', 'a') as f: f.write(f'{sys._getframe().f_lineno} - Node {self.id} did not receive setup message from parent {self.parentId} and is resetting at tick {self.tickCount}\n')
        print(f'Node {self.id} did not receive setup message from parent {self.parentId} and is resetting at tick {self.tickCount}')
        self.resetMeetingControl()
      return []
    
    def setupChildBroadcasting(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de setupChildBroadcasting
      raise NotImplementedError('Implementar código para estado setupChildBroadcasting')
    
    def setupReady(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de setupReady
      raise NotImplementedError('Implementar código para estado setupReady')
    
    def setupReset(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de setupReset
      raise NotImplementedError('Implementar código para estado setupReset')
    
    def setupChildListening(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de setupChildListening
      raise NotImplementedError('Implementar código para estado setupChildListening')
    
    def setupNewChild(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de setupNewChild
      raise NotImplementedError('Implementar código para estado setupNewChild')
    
    def setupSetup(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de setupSetup
      raise NotImplementedError('Implementar código para estado setupSetup')
    
    def setupData(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de setupData
      raise NotImplementedError('Implementar código para estado setupData')
    
    def dataParentListening(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de dataParentListening
      raise NotImplementedError('Implementar código para estado dataParentListening')
    
    def dataMessageChild(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de dataMessageChild
      raise NotImplementedError('Implementar código para estado dataMessageChild')
    
    def dataChildListening(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de dataChildListening
      raise NotImplementedError('Implementar código para estado dataChildListening')
    
    def dataReady(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de dataReady
      raise NotImplementedError('Implementar código para estado dataReady')

    def dataReset(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de dataReset
      raise NotImplementedError('Implementar código para estado dataReset')
    
    def dataDone(self, step: int, tick: bool, messagesSent: List):
      # implementar a lógica de quando o nó está com o estado de dataDone
      raise NotImplementedError('Implementar código para estado dataDone')

    def hardwareStep(self, step: int, tick: bool, messagesSent: List) -> List:
      # hardwareStep (ve estado externo do nó):
      # - equivalente ao hardware (ligado à energia)
      # -- (des)carrega, (in)ativa a execução
      # -- recebe e conta tick
      # -- simula timers

      # incrementar o nível de energia com a energia colhida
      print(f'Node {self.id} hardware step with energy level {self.energyLevel} and energy state {self.energyState}')
      # self.energyLevel += energyHarvested(simulationTime) # modelo adaptado do real
      self.energyLevel += 1e-2 * step # modelo simplificado para teste [J/ms]
      if self.energyLevel > self.maxEnergyLevel:
        self.energyLevel = self.maxEnergyLevel
      # chama a função de execução do estado atual do nó
      return self.stateRun(self.energyState, step, tick, messagesSent)

    def addMeeting(self, meeting):
      i = 0
      for meeting in self.scheduledMeetings:
        while i < len(self.scheduledMeetings) and self.scheduledMeetings[i][2] <= meeting[2]:
          i += 1
        break
      self.scheduledMeetings.insert(i, meeting)
    
'''
\If{node counts a tick} \label{if:tick count}
    \If{node has full energy storage} \label{ if:full energy}
        \State update charging count  \label{st:update charge count}
        \If{build-up mode} \label{if:build-up}
            \If{node has a parent} \label{if:parent}
                \State send setup message with id, layer, status, charging time and scheduled meetings \label{st:setup message}
            \EndIf
            \If{node receives a setup message} \label{if:receive setup message}
                \If{it is unscheduled} \label{if:unscheduled}
                    \If{the node has no parent and the message comes from a higher layer} \label{if:no parent and message from higher layer}
                        \State Answer it with its own charging time \label{st:answer message}
                        \If{the parent notices the child charging time does not fit in the agenda} \label{if:no agenda}
                            \State The parent sends a new setup message with updated scheduled meetings \label{st:resend setup message}
                        \EndIf
                        \State Register the sender as the parent and register its own layer as the parent's plus one \label{st:register parent and layer}
                        \State Broadcast a setup message to find children \label{st:broadcast new setup message}
                        \State Start the timeout count \label{st:start timeout}
                    \Else
                        \If{the node has a parent, sent its broadcast and the message comes from lower layer} \label{if:node has parent and the message comes from a lower layer}
                            \State Register the sender as a child and also record its charging time and scheduled meeting times \label{st:register child and meeting}
                        \EndIf 
                    \EndIf
                \Else
                    \If{it has ready status and comes from lower layer} \label{if:lower layer ready}
                        \State Change the status to ready \label{st:becomes ready from child}
                    \Else
                        \State Reset the timeout count \label{st:reset timeout}
                    \EndIf
                \EndIf
            \EndIf
            \If{timeout expires} \label{if:timeout expires}
                \State Change status to ready \label{st:becomes ready by itself}
            \EndIf
            \If{ready} \label{if:ready}
                \State Send setup message with new status \label{st:send ready status message}
            \EndIf
        \Else
        % transfer mode
            \If{scheduled moment} \label{if:scheduled message}
                \If{communication is successful} \label{if:successful communication}
                    \State Keep the schedule \label{st:keep schedule}
                \Else
                    \State Go back to the build-up mode \label{st:restart build-up mode}
                \EndIf
            \EndIf
        \EndIf
    \EndIf
    \If{node has at least minimum energy storage} \label{if:minimum energy}
        \State update ticks count \label{st:update tick count}
    \EndIf
\EndIf
'''