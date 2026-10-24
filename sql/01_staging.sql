-- Camada staging: lê os CSVs brutos da ANAC, renomeia para snake_case e tipa as colunas.
-- Nenhuma regra de negócio aqui, só limpeza estrutural.

create or replace table stg_voos as
select
    trim("Sigla ICAO Empresa Aérea")                          as empresa_icao,
    trim("Empresa Aérea")                                     as empresa_nome,
    trim("Número Voo")                                        as numero_voo,
    trim("Código DI")                                         as codigo_di,
    trim("Código Tipo Linha")                                 as tipo_linha,
    trim("Modelo Equipamento")                                as modelo_aeronave,
    try_cast("Número de Assentos" as integer)                 as assentos,
    trim("Sigla ICAO Aeroporto Origem")                       as origem_icao,
    trim("Descrição Aeroporto Origem")                        as origem_descricao,
    try_strptime("Partida Prevista", '%d/%m/%Y %H:%M')        as partida_prevista,
    try_strptime("Partida Real", '%d/%m/%Y %H:%M')            as partida_real,
    trim("Sigla ICAO Aeroporto Destino")                      as destino_icao,
    trim("Descrição Aeroporto Destino")                       as destino_descricao,
    try_strptime("Chegada Prevista", '%d/%m/%Y %H:%M')        as chegada_prevista,
    try_strptime("Chegada Real", '%d/%m/%Y %H:%M')            as chegada_real,
    upper(trim("Situação Voo"))                               as situacao_voo,
    try_strptime("Referência", '%d/%m/%Y %H:%M:%S')::date     as data_referencia,
    nullif(trim("Codeshare"), '')                             as codeshare,
    regexp_extract(filename, 'VRA_(\d{4}_\d{2})', 1)          as arquivo_mes
from read_csv(
    'data/raw/VRA_*.csv',
    delim = ';',
    header = true,
    all_varchar = true,
    filename = true
);
