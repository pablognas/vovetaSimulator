import sys
import argparse
from dataclasses import dataclass, field
from typing import List
from sensor import Sensor, addEvent, mergeEvents
from math import sin, pi
from random import randint

# energia = c*v*v/2 (J)
# W = J/s

constEnergyHarvest = 1e-2  # energia colhida em W no modo constante
radioOn = 3.88e-6 # energia do radio ligado em W ~\cite{fabbri2018micropower}

def energyHarvested(simulation_time: float, variation: int = 7, source: str = 'const') -> float:
  """
  Calculate the total energy harvested over a given simulation time.

  Parameters:
  simulation_time (float): The total time of the simulation in seconds.
  variation (int): The percentage variation in harvested energy.

  Returns:
  float: The energy harvested in watts.
  """
  if source == 'solar':
    max_power = 0.4  # Maximum power in watts
    frequency = 1/(24*60*60)
    phi = 3*pi/2
    minimum_power = 1e-6 # Minimum power in watts
    harvestedPower = max_power * sin(2 * pi * frequency * simulation_time + phi)
    if harvestedPower < minimum_power:
        harvestedPower = minimum_power
    return harvestedPower * (1 + randint(-variation, variation) / 100)
  elif source == 'const': return constEnergyHarvest


# classe Meio que representa o ambiente de simulação da WSN, incluindo a topologia da rede, o tempo de simulação, os eventos (ticks, mensagens, colheita e consumo de energia), e as métricas de avaliação
@dataclass
class Meio:
  simulationTime: int = 0
  tickCount: int = 0
  tickPeriod: int = 1000 # ms
  events: List = field(default_factory=dict) # lista de eventos agendados para a simulação - cada evento é representado por um dicionário [tipo do evento, tempo do evento] | tipos de eventos: tick, harvest, consume, setupMessage, dataMessage, energyResume - a lista é ordenada pelo tempo do evento para facilitar o processamento dos eventos no passo da simulação
  eventsNow: List = field(default_factory=list) # lista de eventos que devem ser processados no step atual
  cycles: int = 5
  harvestingVariation: float = 7
  layers: int = 2
  nodesPerLayer: int = 2
  msgsReceived: int = 0
  msgsLost: int = 0
  wsn: List[Sensor] = field(default_factory=list) # lista de nós da rede - cada nó é representado por um objeto da classe Sensor
  step: int = 100 # ms - passo da simulação

  def __init__(self, harvestingVariation:float = 7, tickPeriod:float = 1000, cycles:int = 5, layers:int = 2, nodesPerLayer:int = 2):
    # inicialização das variáveis de simulação e métricas de avaliação
    self.simulationTime = 0
    self.step = 100 # ms - passo da simulação
    self.tickCount = 0
    self.tickPeriod = tickPeriod
    self.events = [{'event': 'consume', 'time': 0, 'energy': 0},{'event': 'harvest', 'time': 0, 'energy': 0} ,{'event': 'tick', 'time': self.tickPeriod}] # início da simulação com um evento de colheita de energia e um tick
    self.eventsNow = []
    self.cycles = cycles
    self.harvestingVariation = harvestingVariation
    self.layers = layers
    self.nodesPerLayer = nodesPerLayer
    self.msgsReceived = 0
    self.msgsLost = 0
    self.wsn = self.criaRede()
    # self.wsn.insert(0, Sensor(id='base_station', energyLevel = 10000, layer = -1, index = 0, baseStation=True, maxEnergyLevel=1,parentId='root', energyState='Initial'))
    self.wsn['-1'] = [Sensor(id='base_station', energyLevel = 10000, index = 0, baseStation=True, maxEnergyLevel=1,parentId='root', energyState='Initial')]

    with open('simulation_log.txt', 'w') as f: f.write(f'Simulation started with harvesting_variation={self.harvestingVariation}, tick_period={self.tickPeriod}, cycles={self.cycles}, layers={self.layers}, nodes_per_layer={self.nodesPerLayer}\n')
    # print(f'Running simulation with harvesting_variation={self.harvestingVariation}, tick_period={self.tickPeriod}, cycles={self.cycles}, layers={self.layers}, nodes_per_layer={self.nodesPerLayer}')

  # função para criar a topologia da rede com base no número de camadas e nós por camada
  def criaRede(self):
    wsn = {}
    for layer in range(self.layers):
      wsn[f'{layer}'] = []
      # adaptando para remover as informações de topologia da rede dos nós
      for index in range(self.nodesPerLayer): wsn[f'{layer}'].append(Sensor(id=f'node_{layer}_{index}'))
    return wsn
  
  def eventHandlerLoop(self,event):
    # reactions = []
    for layer in self.wsn.keys():
      reactions = []
      for node in self.wsn[layer]: reactions = mergeEvents(reactions, node.eventHandler(event)) # self.events = mergeEvents(self.events, node.eventHandler(event))
      if reactions == [{}]:
        self.events = mergeEvents(self.events, reactions)
        continue
      i = 0
      while i < len(reactions) and reactions[i]['time'] <= self.simulationTime:
        i += 1
      self.eventsNow = mergeEvents(self.eventsNow, reactions[:i])
      self.events = mergeEvents(self.events, reactions[i:])
  
  def eventHandler(self):
    # função para processar os eventos agendados para o passo atual da simulação
    while self.events and self.events[0]['time'] <= self.simulationTime:
      self.eventsNow.append(self.events.pop(0))
    # processamento dos eventos do passo atual
    while self.eventsNow:
      # mudar a logica para avaliar camada a camada da rede se os nós estão no alcance dos eventos de mensagem, os demais não são afetados - fazer o for nas camadas dentro de cada if de tipo de evento (o for deve virar uma função para ecnomizar código)
      event = self.eventsNow.pop(0)
      with open('simulation_log.txt', 'a') as f: f.write(95*'-'+'\n'+f'[vs4-{sys._getframe().f_lineno}] - Processing event {event} at simulation time {self.simulationTime} ms\n')
      # print(f'[vs4-{sys._getframe().f_lineno}] - Processing event {event} at simulation time {self.simulationTime} ms')
      if event['event'] == 'harvest':
        # vericar se a simulação ainda está acontecendo
        harvestedEnergy = 0
        harvestTime = 0
        while harvestTime < self.step:
          harvestedEnergy += energyHarvested(self.simulationTime + harvestTime, self.harvestingVariation) / 1000 # energia colhida em J no período de tempo do passo da simulação
          harvestTime += 1
        if self.tickCount < self.cycles:
          # adicionar o próximo evento de colheita de energia respeitando a ordem cronológica da lista events
          self.events = addEvent(self.events, {'event': 'harvest', 'time': self.simulationTime + self.step, 'energy': harvestedEnergy})
        # fazer o loop de nós para que eles tratem o evento
        self.eventHandlerLoop(event)
      elif event['event'] == 'consume':
        if self.tickCount < self.cycles:
          self.events = addEvent(self.events, {'event': 'consume', 'time': self.simulationTime + self.step, 'energy': radioOn * self.step / 1000})
        self.eventHandlerLoop(event)
      elif event['event'] == 'tick':
        if self.tickCount < self.cycles:
          self.tickCount += 1
          # adicionar o próximo evento de tick respeitando a ordem cronológica da lista events
          self.events = addEvent(self.events, {'event': 'tick', 'time': self.simulationTime + self.tickPeriod})
        self.eventHandlerLoop(event)
      elif event['event'] == 'energyResume': self.eventHandlerLoop(event)
      elif event['event'] in ['setupMessage', 'dataMessage']:
        # fazer o loop de nós para que eles tratem o evento - aqui deve ser avaliado se os nós estão no alcance do evento de mensagem, os demais não são afetados
        senderLayer = None
        for layer in self.wsn.keys():
          for node in self.wsn[layer]:
            if node.id == event['message'].senderId:
              senderLayer = layer
              break
          if senderLayer is not None: break
        if senderLayer is None: raise ValueError(f"Sender node with id {event['message'].senderId} not found in the network")
        for layer in self.wsn.keys():
          for node in self.wsn[layer]:
            reactions = [{}]
            if abs(int(layer) - int(senderLayer)) <= 1 and node.id != event['message'].senderId: # avaliando se o nó está no alcance do evento de mensagem (alcance de 1 camada) e se ele não é o nó que enviou a mensagem)
              reactions = mergeEvents(node.eventHandler(event), reactions) # self.events = mergeEvents(self.events, node.eventHandler(event))
            if reactions == [{}]:
              self.events = mergeEvents(self.events, reactions)
              continue
            i = 0
            while i < len(reactions) and reactions[i]['time'] <= self.simulationTime:
              i += 1
            self.eventsNow = mergeEvents(self.eventsNow, reactions[:i])
            self.events = mergeEvents(self.events, reactions[i:])
      elif event['event'] in ['parentReady']:
        # fazer o loop de nós para que eles tratem o evento - aqui deve ser avaliado se os nós estão no alcance do evento de mensagem, os demais não são afetados - porém nesse caso, o nó que envia a mensagem também deve tratar o evento
        senderLayer = None
        for layer in self.wsn.keys():
          for node in self.wsn[layer]:
            if node.id == event['message'].senderId:
              senderLayer = layer
              break
          if senderLayer is not None: break
        if senderLayer is None: raise ValueError(f"Sender node with id {event['message'].senderId} not found in the network")
        for layer in self.wsn.keys():
          for node in self.wsn[layer]:
            reactions = [{}]
            if abs(int(layer) - int(senderLayer)) <= 1: # avaliando se o nó está no alcance do evento de mensagem (alcance de 1 camada) e se ele não é o nó que enviou a mensagem)
              reactions = mergeEvents(node.eventHandler(event), reactions) # self.events = mergeEvents(self.events, node.eventHandler(event))
            if reactions == [{}]:
              self.events = mergeEvents(self.events, reactions)
              continue
            i = 0
            while i < len(reactions) and reactions[i]['time'] <= self.simulationTime:
              i += 1
            self.eventsNow = mergeEvents(self.eventsNow, reactions[:i])
            self.events = mergeEvents(self.events, reactions[i:])
        senderLayer = None
        for layer in self.wsn.keys():
          for node in self.wsn[layer]:
            if node.id == event['message'].senderId:
              senderLayer = layer
              break
          if senderLayer is not None: break
        if senderLayer is None: raise ValueError(f"Sender node with id {event['message'].senderId} not found in the network")
        for layer in self.wsn.keys():
          for node in self.wsn[layer]:
            reactions = [{}]
            if abs(int(layer) - int(senderLayer)) <= 1 and node.id != event['message'].senderId: # avaliando se o nó está no alcance do evento de mensagem (alcance de 1 camada) e se ele não é o nó que enviou a mensagem)
              reactions = mergeEvents(node.eventHandler(event), reactions) # self.events = mergeEvents(self.events, node.eventHandler(event))
            if reactions == [{}]:
              self.events = mergeEvents(self.events, reactions)
              continue
            i = 0
            while i < len(reactions) and reactions[i]['time'] <= self.simulationTime:
              i += 1
            self.eventsNow = mergeEvents(self.eventsNow, reactions[:i])
            self.events = mergeEvents(self.events, reactions[i:])
      else:
        raise NotImplementedError(f'{event["event"]} event processing not implemented yet')
        # with open('simulation_log.txt', 'a') as f: f.write(f'[vs4-{sys._getframe().f_lineno}] - Event type {event["event"]} processing skipped\n')
  
if __name__ == "__main__":
  # criação do objeto Meio com os parâmetros de simulação recebidos por linha de comando
  parser = argparse.ArgumentParser(description='Simulação de WSN com VoVeTA-like protocol')
  parser.add_argument('--harvesting_variation', type=float, default=7, help='variação percentual na energia colhida')
  parser.add_argument('--tick_period', type=float, default=1000, help='período de cada tick em ms')
  parser.add_argument('--cycles', type=int, default=5, help='número de ciclos de simulação')
  parser.add_argument('--layers', type=int, default=1, help='número de camadas na topologia da rede')
  parser.add_argument('--nodes_per_layer', type=int, default=1, help='número de nós por camada na topologia da rede')
  args = parser.parse_args()
  meio = Meio(harvestingVariation=args.harvesting_variation, tickPeriod=args.tick_period, cycles=args.cycles, layers=args.layers, nodesPerLayer=args.nodes_per_layer)

  # execução da simulação
  while meio.tickCount < meio.cycles:
    meio.eventHandler()
    meio.simulationTime += meio.step
  with open('simulation_log.txt', 'a') as f: f.write(f'Simulation finished at simulation time {meio.simulationTime} ms with {meio.msgsReceived} messages received and {meio.msgsLost} messages lost\n')