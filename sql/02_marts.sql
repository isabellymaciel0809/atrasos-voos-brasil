-- Camada marts: tabela fato de voos domésticos de passageiros, pronta para análise.
--
-- Definições (documentadas no README):
--   * Escopo: tipo_linha = 'N' (doméstica mista = passageiros).
--   * Pontualidade: padrão de mercado OTP15 - chegada até 15 min após o previsto.
--     A ANAC classifica com tolerância de 30 min; as duas métricas ficam disponíveis.
--   * Atraso fora de [-180, 1440] min é tratado como erro de registro (flag dado_suspeito).

create or replace table dim_aeroporto as
with todos as (
    select origem_icao as icao, origem_descricao as descricao from stg_voos
    union all
    select destino_icao, destino_descricao from stg_voos
),
partes as (
    select
        icao,
        any_value(descricao) as descricao,
        string_split(any_value(descricao), ' - ') as p
    from todos
    where icao is not null
    group by icao
)
select
    icao,
    descricao,
    case when p[-1] = 'BRASIL' then p[-2] end as uf,
    case when p[-1] = 'BRASIL' then p[-3] end as cidade,
    p[-1]                                     as pais,
    case
        when p[-1] <> 'BRASIL' then null
        when p[-2] in ('AC','AP','AM','PA','RO','RR','TO') then 'Norte'
        when p[-2] in ('AL','BA','CE','MA','PB','PE','PI','RN','SE') then 'Nordeste'
        when p[-2] in ('DF','GO','MT','MS') then 'Centro-Oeste'
        when p[-2] in ('ES','MG','RJ','SP') then 'Sudeste'
        when p[-2] in ('PR','RS','SC') then 'Sul'
    end as regiao
from partes;


create or replace table fct_voos as
with base as (
    select
        s.*,
        coalesce(s.data_referencia, s.partida_prevista::date)          as data_voo,
        datediff('minute', s.partida_prevista, s.partida_real)          as atraso_partida_bruto,
        datediff('minute', s.chegada_prevista, s.chegada_real)          as atraso_chegada_bruto
    from stg_voos s
    where s.tipo_linha = 'N'
)
select
    b.empresa_icao,
    b.empresa_nome,
    case
        when b.empresa_icao = 'TAM' then 'LATAM'
        when b.empresa_icao in ('AZU', 'ACN') then 'Azul'
        when b.empresa_icao = 'GLO' then 'Gol'
        else 'Outras'
    end                                                     as grupo_empresa,
    b.numero_voo,
    b.codigo_di,
    b.modelo_aeronave,
    b.assentos,

    b.data_voo,
    date_trunc('month', b.data_voo)::date                   as mes,
    isodow(b.data_voo)                                      as dia_semana,      -- 1 = segunda
    hour(b.partida_prevista)                                as hora_partida_prevista,

    b.origem_icao,
    o.cidade                                                as origem_cidade,
    o.uf                                                    as origem_uf,
    o.regiao                                                as origem_regiao,
    b.destino_icao,
    d.cidade                                                as destino_cidade,
    d.uf                                                    as destino_uf,
    d.regiao                                                as destino_regiao,
    b.origem_icao || '-' || b.destino_icao                  as rota,

    b.partida_prevista,
    b.partida_real,
    b.chegada_prevista,
    b.chegada_real,

    b.situacao_voo = 'CANCELADO'                            as cancelado,
    b.partida_prevista is not null                          as programado,
    coalesce(
        b.atraso_chegada_bruto not between -180 and 1440
        or b.atraso_partida_bruto not between -180 and 1440,
        false
    )                                                       as dado_suspeito,

    case when b.atraso_partida_bruto between -180 and 1440
         then b.atraso_partida_bruto end                    as atraso_partida_min,
    case when b.atraso_chegada_bruto between -180 and 1440
         then b.atraso_chegada_bruto end                    as atraso_chegada_min
from base b
left join dim_aeroporto o on o.icao = b.origem_icao
left join dim_aeroporto d on d.icao = b.destino_icao;


-- Visão usada em todas as métricas de pontualidade:
-- voos programados, realizados e com horários válidos.
create or replace view vw_voos_pontualidade as
select
    *,
    atraso_chegada_min > 15  as atrasado_15,
    atraso_chegada_min > 30  as atrasado_30,
    atraso_chegada_min > 60  as atrasado_60
from fct_voos
where programado
  and not cancelado
  and atraso_chegada_min is not null;
