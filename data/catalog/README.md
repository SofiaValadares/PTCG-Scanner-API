# Catalogs

Uma pasta por idioma (`en/`, `pt/`, `ja/`, …), cada uma com `cards.csv` e `sets.csv`.

A API carrega **todos** os idiomas para o match (uma carta em japonês cai em `ja/` mesmo com `CATALOG_LANG=en`). `CATALOG_LANG` só desempata o nome do set.

Origem: repo do TCC, `data/catalog/`. Códigos de set: [PkmnCards](https://pkmncards.com/sets/).
