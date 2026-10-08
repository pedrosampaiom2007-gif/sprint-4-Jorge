---
titulo: Manual de operação do ChargeGrid Intelligence
tipo: manual_produto
acesso: publico
versao: "1.0"
data: 2026-10
autoria: Projeto ChargeGrid Intelligence (Turma 1CCPG) — EV Challenge GoodWe/FIAP
---

# Manual de operação do ChargeGrid Intelligence

## O que é o ChargeGrid Intelligence

O ChargeGrid Intelligence (CGI) é o sistema de gestão de eletropostos desenvolvido no EV
Challenge GoodWe/FIAP. Ele atende postos comerciais e frotas: registra as sessões de
recarga, mostra a disponibilidade dos carregadores, calcula a cobrança de cada sessão e reúne
os indicadores de operação (receita, energia entregue, ticket médio e pico de demanda).

O motorista usa o CGI pelo aplicativo ou pelo totem do posto. A equipe de gestão usa a
ferramenta interna, que mostra também os dados comerciais.

## Pontos de carga

A rede de referência do projeto tem dez pontos de carga, identificados de CP-01 a CP-10.
Os pontos usam três tipos de carregador:

- AC 7,4 kW — corrente alternada, potência de 7,4 kW.
- AC 11 kW — corrente alternada, potência de 11 kW.
- DC 22 kW — corrente contínua, potência de 22 kW.

Cada sessão de recarga fica associada ao ponto de carga em que aconteceu, o que permite
acompanhar a receita e a energia entregue por ponto.

## Disponibilidade dos carregadores

O CGI informa em tempo real quais estações estão livres e quais estão ocupadas. Essa
informação é pública: aparece para qualquer motorista no aplicativo e no totem.

## Perfis de acesso

O CGI separa dois perfis de acesso:

- Motorista (aplicativo e totem): vê a disponibilidade das estações e as informações da
  própria recarga e dos próprios pagamentos.
- Gestão (ferramenta interna): vê também faturamento do dia, sessões ativas,
  sessões iniciadas no dia e o histórico comercial dos pontos de carga.

Dados de outros motoristas, como identificação do veículo e valores de sessões, nunca são
mostrados no perfil de motorista.

## Pagamento das sessões

Cada sessão é cobrada pela energia consumida, em kWh, com a tarifa dinâmica descrita na
Tabela Tarifária do ChargeGrid. O pagamento da sessão pode ser feito por Pix ou cartão de
crédito.

## Cashback

Todo motorista recebe 5% de volta do valor de cada sessão paga carregando pela ChargeGrid.
O valor aparece como saldo acumulado na tela "Meus pagamentos" do aplicativo. Por enquanto o
saldo não pode ser resgatado: é um benefício de uso da plataforma, não um cartão de crédito
com saque.

## Balanceamento dinâmico de carga (DLB)

O DLB (Dynamic Load Balancing) distribui a potência disponível na instalação entre os
carregadores em uso, para que a soma das recargas não ultrapasse o limite da rede do local.

Na base histórica SP2, as sessões com DLB ativo tiveram consumo mais estável: a variância do
consumo foi de 273,1 com DLB ativo, contra 496,1 com DLB inativo. Por isso o CGI recomenda
manter o DLB ativo, que garante a estabilidade da rede.

## Planejamento de novos pontos de carga

Referências usadas no planejamento de expansão:

- O custo de instalação médio por ponto de carga é de R$ 15.000.
- Para atender 50 veículos por dia, recomenda-se ao menos 3 carregadores de 22 kW.

Projetos de instalação elétrica precisam ser feitos e assinados por eletricista ou engenheiro
eletricista habilitado. O CGI não dimensiona circuitos nem quadros de energia.
