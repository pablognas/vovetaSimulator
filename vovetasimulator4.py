import sys
import argparse
from dataclasses import dataclass, field
from typing import List
from sensor import Sensor, addEvent, mergeEvents
from math import sin, pi
from random import randint
import json
import os
import random

# energia = c*v*v/2 (J)
# W = J/s

constEnergyHarvest = 1.15  # energia colhida em W no modo constante
radioOn = 325e-3 # energia do radio ligado em W ~\cite{fabbri2018micropower}

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

def simplifiedEH(basePower=constEnergyHarvest, variation=0):
  if variation <= 0: return basePower
  return basePower * (1 + random.uniform(-variation, variation) / 100)


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

  def __init__(self, harvestingVariation:float = 7, tickPeriod:float = 1000, cycles:int = 5, layers:int = 2, nodesPerLayer:int = 2,seed:int = 24,tickJitter: int = 0, simName:str = 'default'):
    self.seed = seed
    random.seed(seed)
    # inicialização das variáveis de simulação e métricas de avaliação
    self.simName = simName
    self.tickJitter = tickJitter
    self.simulationTime = 0
    self.step = tickPeriod/10 # ms - passo da simulação
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
    self.resets = 0
    self.wsn = self.criaRede()
    # self.wsn.insert(0, Sensor(id='base_station', energyLevel = 10000, layer = -1, index = 0, baseStation=True, maxEnergyLevel=1,parentId='root', energyState='Initial'))
    self.wsn['-1'] = [Sensor(id='base_station', energyLevel = 10000, index = 0, baseStation=True, maxEnergyLevel=1,parentId='root', energyState='Initial')]

    # NOVO: criar diretório de saída
    self.outputDir = f'results/{self.simName}'
    os.makedirs(self.outputDir, exist_ok=True)

    with open(f'{self.outputDir}/simulation_log.txt', 'w') as f:
      f.write(f'Simulation: {self.simName}, seed: {self.seed}\n')
      f.write(f'Parameters: variation={self.harvestingVariation}, tick={self.tickPeriod}ms, '
              f'jitter={self.tickJitter}%, cycles={self.cycles}, '
              f'topology={self.layers}x{self.nodesPerLayer}\n')

  # NOVO: método para calcular o próximo tick com jitter
  def _nextTickTime(self):
    if self.tickJitter > 0:
      jitter_factor = 1 + random.uniform(-self.tickJitter, self.tickJitter) / 100
      return self.simulationTime + int(self.tickPeriod * jitter_factor)
    return self.simulationTime + self.tickPeriod

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
          # harvestedEnergy += energyHarvested(self.simulationTime + harvestTime, self.harvestingVariation) / 1000 # energia colhida em J no período de tempo do passo da simulação
          harvestedEnergy += simplifiedEH(constEnergyHarvest, self.harvestingVariation) * self.step / 1000 # energia colhida em J no período de tempo do passo da simulação
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
          self.events = addEvent(self.events, {'event': 'tick', 'time': self._nextTickTime()})
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
  parser.add_argument('--harvesting_variation', type=float, default=0, help='variação percentual na energia colhida')
  parser.add_argument('--tick_period', type=float, default=2500, help='período de cada tick em ms')
  parser.add_argument('--tick_jitter', type=int, default=0, help='variação percentual do período de cada tick')
  parser.add_argument('--cycles', type=int, default=1440, help='número de ciclos de simulação')
  parser.add_argument('--layers', type=int, default=1, help='número de camadas na topologia da rede')
  parser.add_argument('--nodes_per_layer', type=int, default=1, help='número de nós por camada na topologia da rede')
  parser.add_argument('--sim_name', type=str, default='default', help='nome da simulação')
  parser.add_argument('--seed', type=int, default=24, help='semente para geração de números aleatórios')
  args = parser.parse_args()
  # meio = Meio(harvestingVariation=args.harvesting_variation, tickPeriod=args.tick_period, cycles=args.cycles, layers=args.layers, nodesPerLayer=args.nodes_per_layer)

# execução da simulação
  meio = Meio(
  harvestingVariation=args.harvesting_variation,
  tickPeriod=args.tick_period,
  cycles=args.cycles,
  layers=args.layers,
  nodesPerLayer=args.nodes_per_layer,
  tickJitter=args.tick_jitter,
  simName=args.sim_name,
  seed=args.seed
)

  # execução da simulação
  while meio.tickCount < meio.cycles:
    meio.eventHandler()
    meio.simulationTime += meio.step

  # === COLETA DE MÉTRICAS ===
  total_data_generated = 0
  total_data_received_bs = 0
  total_setup_sent = 0
  total_data_sent = 0
  total_msgs_received = 0
  total_msgs_ignored = 0
  bs_resets = 0
  bs_reset_timestamps = []
  bs_parent_ready_timestamps = []
  bs_latency_records_ms = []
  bs_latency_records_ticks = []
  node_energy_levels = []
  node_reset_counts = {}
  reset_count_per_layer = {layer: 0 for layer in meio.wsn.keys()}

  bs = meio.wsn['-1'][0]
  bs_resets = bs.resetCount
  bs_reset_timestamps = bs.resetTimestamps
  bs_parent_ready_timestamps = bs.parentReadyTimestamps
  total_data_received_bs = bs.dataMsgsReceived
  total_setup_sent += bs.setupMsgsSent

  for layer in meio.wsn.keys():
    for node in meio.wsn[layer]:
      total_msgs_received += node.msgsReceived
      total_msgs_ignored += node.msgsIgnored
      total_setup_sent += node.setupMsgsSent
      total_data_sent += node.dataMsgsSent
      total_data_generated += node.dataMsgsSent
      if not node.baseStation:
        node_energy_levels.append({'id': node.id, 'energy': node.energyLevel})
        node_reset_counts[node.id] = len(node.resetTimestamps)
        reset_count_per_layer[layer] += len(node.resetTimestamps)
      else:
        for record in node.latency_record:
          bs_latency_records_ms.append(record['latency_ms'])
          bs_latency_records_ticks.append(record['latency_ticks'])

  # PDR
  pdr = total_data_received_bs / total_data_generated if total_data_generated > 0 else 0

  # Control overhead
  overhead = total_setup_sent / total_data_sent if total_data_sent > 0 else float('inf')

  # Reorganization times
  reorg_times = []
  for reset_t in bs_reset_timestamps:
    for pr_t in bs_parent_ready_timestamps:
      if pr_t > reset_t:
        reorg_times.append(pr_t - reset_t)
        break

  results = {
    'simulation_name': meio.simName,
    'seed': meio.seed,
    'parameters': {
      'topology': f'{meio.layers}x{meio.nodesPerLayer}',
      'layers': meio.layers,
      'nodes_per_layer': meio.nodesPerLayer,
      'cycles': meio.cycles,
      'tick_period_ms': meio.tickPeriod,
      'tick_jitter_pct': meio.tickJitter,
      'energy_variation_pct': meio.harvestingVariation,
      'simulation_time_ms': meio.simulationTime,
      'duration_hours': round(meio.simulationTime / 3600000, 2)
    },
    'metrics': {
      'pdr': round(pdr, 4),
      'total_data_generated': total_data_generated,
      'total_data_received_bs': total_data_received_bs,
      'total_msgs_received': total_msgs_received,
      'total_msgs_ignored': total_msgs_ignored,
      'total_setup_sent': total_setup_sent,
      'total_data_sent': total_data_sent,
      'control_overhead': round(overhead, 2),
      'bs_resets': bs_resets,
      'reorg_times_ms': reorg_times,
      'avg_reorg_time_ms': round(sum(reorg_times) / len(reorg_times), 2) if reorg_times else 0,
      'avg_latency_ms': round(sum(bs_latency_records_ms) / len(bs_latency_records_ms), 2) if bs_latency_records_ms else 0,
      'avg_latency_ticks': round(sum(bs_latency_records_ticks) / len(bs_latency_records_ticks), 2) if bs_latency_records_ticks else 0,
      'node_reset_counts': node_reset_counts,
      'node_energy_levels': node_energy_levels,
      'reset_count_per_layer': reset_count_per_layer
    }
  }

  with open(f'{meio.outputDir}/results.json', 'w') as f:
    json.dump(results, f, indent=2)

  # Resumo no terminal
  print(f'=== {meio.simName} ===')
  print(f'Topology: {meio.layers}x{meio.nodesPerLayer} | Cycles: {meio.cycles}')
  print(f'PDR: {pdr:.4f} | BS Resets: {bs_resets} | Overhead: {overhead:.2f}')
  print(f'Msgs received: {total_msgs_received} | Msgs ignored: {total_msgs_ignored}')
  print(f'Results saved to {meio.outputDir}/results.json')