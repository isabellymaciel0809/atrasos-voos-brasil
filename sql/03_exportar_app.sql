-- Exporta uma versão enxuta da tabela fato para o painel (app/), que roda sem o banco completo.
-- Só voos programados e sem horário inválido; uma linha por voo, colunas mínimas.

copy (
    select
        data_voo,
        hora_partida_prevista::utinyint     as hora,
        grupo_empresa,
        origem_icao,
        destino_icao,
        cancelado,
        atraso_partida_min::smallint        as atraso_partida_min,
        atraso_chegada_min::smallint        as atraso_chegada_min,
        assentos::smallint                  as assentos
    from fct_voos
    where programado
      and not dado_suspeito
      and (cancelado or atraso_chegada_min is not null)
    order by data_voo, origem_icao
) to 'app/data/voos.parquet' (format parquet, compression zstd);

copy (
    select icao, cidade, uf, regiao
    from dim_aeroporto
    where pais = 'BRASIL'
) to 'app/data/aeroportos.parquet' (format parquet, compression zstd);
